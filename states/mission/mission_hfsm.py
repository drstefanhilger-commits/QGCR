# === PFAD-B FULL FILE: QGCR/states/mission/mission_hfsm.py ===

import threading

from QGCR.communication.microservices.mission_microservice import MissionMicroService
from QGCR.states.main_state import MainState
from QGCR.states.base_hfsm import BaseHFSM


class MissionHFSM(BaseHFSM):
    """
    MISSION:
    - MISSION_UPLOAD   → model.mission_upload_items über model.mission_ms hochladen
    - MISSION_DOWNLOAD → Mission von PX4 laden und in model.mission schreiben
    - MISSION_STOP     → laufenden Transfer abbrechen (Mission im Model bleibt unverändert)
    - Home-Tab aktiv (model.active_tab == "Home") → READY (während eines Transfers erst danach)
    - RESET / Verbindung verloren → RESET

    upload()/download() blockieren und laufen deshalb in einem Worker-Thread;
    die HFSM fragt das Ergebnis bei jedem Tick ab (hfsm_sub: IDLE / UPLOAD / DOWNLOAD).
    """

    def __init__(self, model):
        super().__init__(model, MainState.MISSION)
        self._next_state = MainState.MISSION

        self._job = None
        self._job_cancel = None
        self._job_ms = None
        self._job_kind = None
        self._job_items = None
        self._job_result = None

    def _on_enter(self):
        self.model.log.qgcr("[MissionHFSM] entering MISSION")
        self.model.hfsm_main = "MISSION"
        self.model.hfsm_sub = "IDLE"
        self.model.push_state_update()

    def _on_during(self):
        # 1) Laufenden Transfer auswerten
        if self._job is not None and not self._job.is_alive():
            self._finish_job()

        # 2) Events
        if self.model.hfsm_events:
            event = self.model.hfsm_events.popleft()

            match event:
                case "RESET":
                    self.model.log.qgcr("[MissionHFSM] RESET received")
                    self._next_state = MainState.RESET
                    return

                case "MISSION_UPLOAD":
                    self._start_upload()

                case "MISSION_DOWNLOAD":
                    self._start_download()

                case "MISSION_STOP":
                    self._cancel_job()

        # 3) Verbindung
        if not self.model.connection_ready():
            self.model.log.qgcr("[MissionHFSM] Connection lost → RESET")
            self._next_state = MainState.RESET
            return

        # 4) Home-Tab aktiv → READY (laufender Transfer wird erst beendet)
        if self.model.active_tab == "Home" and not self._busy():
            self.model.log.qgcr("[MissionHFSM] Home-Tab → READY")
            self._next_state = MainState.READY
            return

        self._next_state = MainState.MISSION

    def _on_exit(self):
        return self._next_state

    # ------------------------------------------------------------
    # Transfer starten
    # ------------------------------------------------------------
    def _busy(self):
        return self._job is not None

    def _service(self):
        ms = getattr(self.model, "mission_ms", None)
        if ms is None or not hasattr(ms, "upload"):
            return None
        return ms

    def _start_upload(self):
        items = getattr(self.model, "mission_upload_items", None)
        if not items:
            self._set_status("Upload: keine Mission geladen")
            return
        self._start_job("UPLOAD", list(items))

    def _start_download(self):
        self._start_job("DOWNLOAD", None)

    def _start_job(self, kind, items):
        name = "Upload" if kind == "UPLOAD" else "Download"

        if self._busy():
            self.model.log.qgcr(f"[MissionHFSM] {name} ignoriert: Transfer läuft bereits")
            return

        ms = self._service()
        if ms is None:
            self._set_status(f"{name}: keine Verbindung zu PX4")
            return

        self._job_ms = ms
        self._job_kind = kind
        self._job_items = items
        self._job_result = None
        self._job_cancel = threading.Event()
        self._job = threading.Thread(
            target=self._run_job, args=(ms, kind, items, self._job_cancel), daemon=True
        )
        self._job.start()

        self._set_sub(kind)
        self._set_status(f"{name} läuft …")

    def _run_job(self, ms, kind, items, cancel):
        """Läuft im Worker-Thread – nur das Ergebnis ablegen."""
        try:
            if kind == "UPLOAD":
                self._job_result = ms.upload(items, cancel=cancel)
            else:
                self._job_result = ms.download(cancel=cancel)
        except Exception as e:
            self._job_result = e

    def _cancel_job(self):
        if not self._busy():
            self.model.log.qgcr("[MissionHFSM] Stop ignoriert: kein Transfer aktiv")
            return

        if not self._job_cancel.is_set():
            self._job_cancel.set()
            name = "Upload" if self._job_kind == "UPLOAD" else "Download"
            self._set_status(f"{name} wird abgebrochen …")

    # ------------------------------------------------------------
    # Transfer auswerten (Update-Thread)
    # ------------------------------------------------------------
    def _finish_job(self):
        ms, kind, items, result = self._job_ms, self._job_kind, self._job_items, self._job_result
        self._job = None
        self._job_cancel = None
        self._job_ms = None
        self._job_kind = None
        self._job_items = None
        self._set_sub("IDLE")

        name = "Upload" if kind == "UPLOAD" else "Download"
        error = result if isinstance(result, Exception) else getattr(ms, "last_error", None)

        if error == MissionMicroService.CANCELLED:
            # Mission im Model bleibt unverändert
            self._set_status(f"{name} abgebrochen")
            return

        if kind == "UPLOAD":
            if result is True:
                self._store_mission(items)
                self._set_status(f"Upload OK ({len(items)} Items)")
            else:
                self._set_status(f"Upload FEHLGESCHLAGEN: {error or 'unbekannt'}")
            return

        if error:
            # Unvollständige Mission nicht ins Model übernehmen
            self._set_status(f"Download FEHLGESCHLAGEN: {error}")
            return

        self._store_mission(result)
        self._set_status(f"Download OK ({len(result)} Items)")

    def _store_mission(self, msgs):
        """MAVLink-MISSION_ITEM_INT → model.mission (Grad / Meter)."""
        self.model.clear_mission()
        for m in msgs:
            self.model.add_mission_item(m.seq, m.command, m.x / 1e7, m.y / 1e7, m.z)
        self.model.mission.ready = len(msgs) > 0
        self.model.mission_loaded = len(msgs) > 0

    # ------------------------------------------------------------
    # Anzeige
    # ------------------------------------------------------------
    def _set_sub(self, sub):
        self.model.hfsm_sub = sub
        self.model.push_state_update()

    def _set_status(self, text):
        self.model.mission_status = text
        self.model.log.qgcr(f"[MissionHFSM] {text}")
