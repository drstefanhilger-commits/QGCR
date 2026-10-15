# === PFAD-B FULL FILE: QGCR/states/intercept/intercept_hfsm.py ===

import math
import threading
import time

from QGCR.model.intercept import (
    InterceptConfig, build_mission, enu_to_latlon, latlon_to_enu, plan_intercept, pursuit,
    reposition_command, return_time,
)
from QGCR.model.mavlink_commands import cmd_mission_start, cmd_rtl
from QGCR.states.base_hfsm import BaseHFSM
from QGCR.states.main_state import MainState


class InterceptHFSM(BaseHFSM):
    """
    INTERCEPT (Tab „FSL“, kontrollierte FSL-Drohne):

    IDLE     ─INTERCEPT_TRIGGER→ Wartepunkt (Lot-Fußpunkt) planen; erreichbar → UPLOAD
    UPLOAD   ─OK→ MISSION_START → START ─armed + AUTO.MISSION→ APPROACH
    APPROACH ─Wartepunkt erreicht→ PURSUE: laufend entgegen / nachfliegen, Treffpunkt per
             DO_REPOSITION nachführen
    PURSUE   ─Treffen (≤ meet_radius) / Nachflug unmöglich / Zeit reicht nicht→ RTL
    APPROACH/PURSUE ─Timeout / Akku < Minimum / INTERCEPT_ABORT→ RTL
    RTL      ─gelandet + disarmed→ IDLE
    Immer nur ein Trigger: neue Trigger außerhalb von IDLE werden verworfen.
    Tab verlassen → READY (während eines Flugs erst nach der Landung).
    RESET im Flug: erst RTL + Landung, dann RESET.
    """

    FSL_MODEL = "gz_fsl_rocket_vtol"
    START_TIMEOUT = 10.0
    ARRIVAL_RADIUS = 2.5        # Wartepunkt erreicht [m] (horizontal)
    REPOSITION_MOVE = 3.0       # Treffpunkt neu senden ab dieser Verschiebung [m]
    REPOSITION_PERIOD = 2.0     # ... spätestens alle 2 s
    FLYING = ("APPROACH", "PURSUE", "RTL")

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
        self._last_reposition = None    # (Zeit, (e, n, u))

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
        elif sub in self.FLYING:
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
        self.model.intercept_pursuit = None
        self.model.intercept_min_distance = None
        self._set_status(
            f"Trigger {trigger.drone_id}: Wartepunkt nach {plan.t_fsl:.0f} s, dann vermutlich "
            f"{plan.mode} (Treffen nach weiteren {plan.t_meet:.0f} s) – Upload …"
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
            self._set_sub("APPROACH")
            self._set_status("FSL fliegt auf kürzestem Weg zur Trigger-Bahn (Wartepunkt)")
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
            self._set_status(f"FSL gelandet{self._min_distance_text()}")
            if self._reset_after_landing:
                self._reset_after_landing = False
                self._next_state = MainState.RESET
                return True
            return False

        self._track_min_distance()

        sub = m.hfsm_sub
        if sub in ("APPROACH", "PURSUE") and not self._rtl_sent:
            cfg = self._config()
            elapsed = time.time() - self._flight_start
            if elapsed > cfg.timeout:
                self._abort(f"Timeout nach {elapsed:.0f} s")
            elif m.battery_remaining is not None and m.battery_remaining < cfg.battery_min:
                self._abort(f"Akku {m.battery_remaining:.0f} % < {cfg.battery_min:.0f} %")
            elif sub == "APPROACH":
                self._check_arrival()
            else:
                self._pursue(elapsed)
        return False

    # ------------------------------------------------------------
    # Wartepunkt → entgegen / nachfliegen
    # ------------------------------------------------------------
    def _fsl_enu(self):
        m = self.model
        if m.vehicle_lat is None or m.intercept_origin is None:
            return None
        e, n = latlon_to_enu(m.intercept_origin, m.vehicle_lat, m.vehicle_lon)
        return e, n, m.vehicle_alt or 0.0

    def _check_arrival(self):
        pos, plan = self._fsl_enu(), self.model.intercept_plan
        if pos is None or plan is None:
            return
        if math.hypot(pos[0] - plan.wait[0], pos[1] - plan.wait[1]) <= self.ARRIVAL_RADIUS:
            self._set_sub("PURSUE")
            self._last_reposition = None
            self.model.log.qgcr("[InterceptHFSM] Wartepunkt erreicht → Entscheidung")
            self._pursue(time.time() - self._flight_start)

    def _pursue(self, elapsed):
        m, cfg = self.model, self._config()
        pos = self._fsl_enu()
        if pos is None:
            return
        now = time.time()

        # Positionen gleich → zurück und landen
        distance = m.intercept_distance()
        if distance is not None and distance[0] <= cfg.meet_radius:
            self._abort(f"Treffpunkt erreicht ({distance[0]:.1f} m)")
            return

        p = pursuit(m.intercept_trigger, pos, now, cfg)
        m.intercept_pursuit = p

        if p.t_meet is None:
            self._abort("Trigger schneller als FSL – Nachfliegen unmöglich")
            return

        remaining = cfg.timeout - elapsed
        need = p.t_meet + return_time(p.meet, cfg)
        if need > remaining:
            self._abort(f"Zeit reicht nicht: Treffen {p.t_meet:.0f} s + Rückflug "
                        f"{need - p.t_meet:.0f} s > Rest {remaining:.0f} s")
            return

        self._set_status(f"FSL fliegt {p.mode}: Treffen in {p.t_meet:.0f} s "
                         f"(Abstand entlang der Bahn {p.gap:.0f} m)")
        self._send_reposition(p.meet, now)

    def _send_reposition(self, meet, now):
        last = self._last_reposition
        if last is not None:
            moved = math.hypot(meet[0] - last[1][0], meet[1] - last[1][1])
            if moved < self.REPOSITION_MOVE and now - last[0] < self.REPOSITION_PERIOD:
                return

        connection = getattr(self.model, "connection", None)
        master = getattr(connection, "master", None)
        if master is None or not getattr(master, "target_system", 0):
            return
        lat, lon = enu_to_latlon(self.model.intercept_origin, meet[0], meet[1])
        alt_amsl = (self.model.home_alt or 0.0) + meet[2]
        connection.send(reposition_command(master.target_system, master.target_component,
                                           lat, lon, alt_amsl, self._config().speed))
        self._last_reposition = (now, meet)

    # ------------------------------------------------------------
    # Minimaler Abstand Trigger–FSL (gemessen)
    # ------------------------------------------------------------
    def _track_min_distance(self):
        distance = self.model.intercept_distance()
        if distance is None or self._flight_start is None:
            return
        current = self.model.intercept_min_distance
        if current is None or distance[0] < current[0]:
            self.model.intercept_min_distance = (distance[0], time.time() - self._flight_start)

    def _min_distance_text(self):
        md = self.model.intercept_min_distance
        return f" – minimaler Abstand {md[0]:.1f} m nach {md[1]:.0f} s" if md else ""

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

        if sub in ("START", "APPROACH", "PURSUE") or (sub == "IDLE" and self.model.px4_armed):
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
