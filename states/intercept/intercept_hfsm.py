# === PFAD-B FULL FILE: QGCR/states/intercept/intercept_hfsm.py ===

import threading
import time

from QGCR.model.intercept import InterceptConfig, build_mission, plan_intercept
from QGCR.model.mavlink_commands import cmd_mission_start, cmd_rtl
from QGCR.states.base_hfsm import BaseHFSM
from QGCR.states.main_state import MainState


class InterceptHFSM(BaseHFSM):
    """
    INTERCEPT (Tab „FSL“, kontrollierte FSL-Drohne):

    IDLE   ─INTERCEPT_TRIGGER→ Wartepunkt planen; erreichbar → UPLOAD (Worker-Thread)
    UPLOAD ─OK→ MISSION_START → START ─armed + AUTO.MISSION→ FLIGHT
    FLIGHT ─Timeout / Akku < Minimum / INTERCEPT_ABORT→ RTL (zurück zum Start, landen)
    FLIGHT/RTL ─gelandet + disarmed→ IDLE
    Immer nur ein Trigger: neue Trigger außerhalb von IDLE werden verworfen.
    Tab verlassen → READY (während eines Flugs erst nach der Landung).
    RESET im Flug: erst RTL + Landung, dann RESET.
    """

    FSL_MODEL = "gz_fsl_rocket_vtol"
    START_TIMEOUT = 10.0

    def __init__(self, model):
        super().__init__(model, MainState.INTERCEPT)
        self._next_state = MainState.INTERCEPT

        self._job = None
        self._job_cancel = None
        self._job_result = None
        self._job_ms = None
        self._start_deadline = None
        self._flight_start = None
        self._seen_armed = False
        self._rtl_sent = False
        self._reset_after_landing = False

    # ------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------
    def _on_enter(self):
        self.model.log.qgcr("[InterceptHFSM] entering INTERCEPT")
        self.model.hfsm_main = "INTERCEPT"
        self.model.hfsm_sub = "IDLE"
        self.model.push_state_update()

    def _on_during(self):
        sub = self.model.hfsm_sub

        # 1) Laufende Schritte auswerten
        if sub == "UPLOAD" and self._job is not None and not self._job.is_alive():
            self._finish_upload()
        elif sub == "START":
            self._check_start()
        elif sub in ("FLIGHT", "RTL"):
            if self._check_flight():
                return

        # 2) Events
        if self.model.hfsm_events:
            event = self.model.hfsm_events.popleft()

            match event:
                case "INTERCEPT_TRIGGER":
                    self._on_trigger()

                case "INTERCEPT_ABORT":
                    self._abort("Abbruch durch Bediener")

                case "RESET":
                    if self.model.px4_armed:
                        self._reset_after_landing = True
                        self._abort("RESET: erst zurück und landen")
                    else:
                        self._next_state = MainState.RESET
                        return

        # 3) Verbindung
        if not self.model.connection_ready():
            self.model.log.qgcr("[InterceptHFSM] Connection lost → RESET")
            self._next_state = MainState.RESET
            return

        # 4) Tab verlassen → READY (nur am Boden / ohne laufenden Schritt)
        if self.model.active_tab != "FSL" and self.model.hfsm_sub == "IDLE":
            self.model.log.qgcr("[InterceptHFSM] Tab verlassen → READY")
            self._next_state = MainState.READY
            return

        self._next_state = MainState.INTERCEPT

    def _on_exit(self):
        return self._next_state

    # ------------------------------------------------------------
    # Trigger → Plan → Upload
    # ------------------------------------------------------------
    def _config(self):
        return self.model.intercept_config or InterceptConfig()

    def _selected_model(self):
        configs = getattr(self.model, "vehicle_configs", None) or []
        return configs[0].model_name if configs else None

    def _on_trigger(self):
        if self.model.hfsm_sub != "IDLE":
            self.model.log.qgcr("[InterceptHFSM] Trigger verworfen: FSL ist bereits im Einsatz")
            return

        trigger = self.model.intercept_trigger
        if trigger is None:
            return

        if self._selected_model() not in (None, self.FSL_MODEL):
            self._set_status(f"Trigger abgelehnt: Modell {self.FSL_MODEL} erforderlich")
            return

        ms = getattr(self.model, "mission_ms", None)
        if ms is None or not hasattr(ms, "upload"):
            self._set_status("Trigger abgelehnt: keine Verbindung zu PX4")
            return

        origin = self._origin()
        if origin is None:
            self._set_status("Trigger abgelehnt: Startposition der FSL unbekannt")
            return

        cfg = self._config()
        plan = plan_intercept(trigger, time.time(), cfg)
        self.model.intercept_plan = plan
        self.model.intercept_origin = origin

        if not plan.reachable:
            self._set_status(f"Trigger {trigger.drone_id}: {plan.reason}")
            return

        items = build_mission(plan, origin, cfg)
        self._store_mission(items)
        self._set_status(
            f"Trigger {trigger.drone_id}: Wartepunkt {plan.along:.0f} m vor dem Trigger, "
            f"FSL nach {plan.t_fsl:.0f} s, wartet {plan.hold:.0f} s – Upload …"
        )

        self._job_ms = ms
        self._job_result = None
        self._job_cancel = threading.Event()
        self._job = threading.Thread(target=self._run_upload, args=(ms, items, self._job_cancel), daemon=True)
        self._job.start()
        self._set_sub("UPLOAD")

    def _origin(self):
        m = self.model
        if m.vehicle_lat is not None and m.vehicle_lon is not None:
            return (m.vehicle_lat, m.vehicle_lon)
        if m.home_lat is not None and m.home_lon is not None:
            return (m.home_lat, m.home_lon)
        return None

    def _run_upload(self, ms, items, cancel):
        try:
            self._job_result = ms.upload(items, cancel=cancel)
        except Exception as e:
            self._job_result = e

    def _finish_upload(self):
        ok = self._job_result is True
        error = self._job_result if isinstance(self._job_result, Exception) else getattr(self._job_ms, "last_error", None)
        self._job = None

        if not ok:
            self._set_sub("IDLE")
            self._set_status(f"Upload fehlgeschlagen: {error or 'unbekannt'}")
            return

        connection = getattr(self.model, "connection", None)
        master = getattr(connection, "master", None)
        if master is None or not getattr(master, "target_system", 0):
            self._set_sub("IDLE")
            self._set_status("Start abgebrochen: keine Verbindung zu PX4")
            return

        connection.send(cmd_mission_start(master.target_system, master.target_component))
        self._start_deadline = time.time() + self.START_TIMEOUT
        self._set_sub("START")
        self._set_status("Mission hochgeladen – Start gesendet …")

    def _store_mission(self, items):
        """Mission für Plot und Gazebo-Landemarke ins Model (Grad)."""
        self.model.clear_mission()
        for it in items:
            self.model.add_mission_item(it.seq, it.command, it.x / 1e7, it.y / 1e7, it.z)
        self.model.mission.ready = True

    # ------------------------------------------------------------
    # Start + Überwachung
    # ------------------------------------------------------------
    def _check_start(self):
        if self.model.px4_armed and self.model.px4_mode == "AUTO.MISSION":
            self._start_deadline = None
            self._flight_start = time.time()
            self._seen_armed = True
            self._rtl_sent = False
            self.model.begin_mission()
            self._set_sub("FLIGHT")
            self._set_status("FSL fliegt zum Wartepunkt")
        elif time.time() > self._start_deadline:
            self._start_deadline = None
            self._set_sub("IDLE")
            self._set_status("Missionsstart abgelehnt (PX4 nicht armed / kein AUTO.MISSION)")

    def _check_flight(self):
        """True, wenn der Zustand gewechselt wird."""
        m = self.model

        if m.px4_armed:
            self._seen_armed = True
        elif self._seen_armed:
            m.mission_running = False
            self._set_sub("IDLE")
            self._set_status("FSL gelandet")
            if self._reset_after_landing:
                self._reset_after_landing = False
                self._next_state = MainState.RESET
                return True
            return False

        if self.model.hfsm_sub == "FLIGHT" and not self._rtl_sent:
            cfg = self._config()
            elapsed = time.time() - self._flight_start
            if elapsed > cfg.timeout:
                self._abort(f"Timeout nach {elapsed:.0f} s")
            elif m.battery_remaining is not None and m.battery_remaining < cfg.battery_min:
                self._abort(f"Akku {m.battery_remaining:.0f} % < {cfg.battery_min:.0f} %")
        return False

    def _abort(self, reason):
        sub = self.model.hfsm_sub

        if sub == "UPLOAD" and self._job_cancel is not None:
            self._job_cancel.set()
            self._set_status(f"{reason} – Upload abgebrochen")
            return

        if sub == "START" and not self.model.px4_armed:
            self._start_deadline = None
            self._set_sub("IDLE")
            self._set_status(f"{reason} – Start abgebrochen")
            return

        if sub in ("START", "FLIGHT") or (sub == "IDLE" and self.model.px4_armed):
            self._start_deadline = None
            self._send_rtl(reason)
            return

        if sub == "RTL":
            self.model.log.qgcr(f"[InterceptHFSM] {reason}: RTL läuft bereits")

    def _send_rtl(self, reason):
        connection = getattr(self.model, "connection", None)
        master = getattr(connection, "master", None)
        if master is None or not getattr(master, "target_system", 0):
            self._set_status(f"{reason} – RTL nicht möglich (keine Verbindung)")
            return
        connection.send(cmd_rtl(master.target_system, master.target_component))
        self._rtl_sent = True
        if self._flight_start is None:
            self._flight_start = time.time()
        self._set_sub("RTL")
        self._set_status(f"{reason} → zurück zum Start und landen (RTL)")

    # ------------------------------------------------------------
    # Anzeige
    # ------------------------------------------------------------
    def _set_sub(self, sub):
        self.model.hfsm_sub = sub
        self.model.push_state_update()

    def _set_status(self, text):
        self.model.intercept_status = text
        self.model.log.qgcr(f"[InterceptHFSM] {text}")
