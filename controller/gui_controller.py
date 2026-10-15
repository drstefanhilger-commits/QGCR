# === PFAD-B FULL FILE: QGCR/controller/gui_controller.py ===

import os
import time

from QGCR.model.intercept import InterceptConfig, Trigger
from QGCR.model.mission_parser import load_qgc_plan
from QGCR.sim.px4_swarm_starter import PX4InstanceConfig


class GUIController:
    """
    Vermittelt zwischen GUI, Model und MainWindow.

    GUI → HFSM:
        - Events werden in model.hfsm_events (FIFO deque) geschrieben.
        - HFSM liest ausschließlich aus model.hfsm_events via popleft().

    GUIEventLoop → GUI:
        - Konsumiert Events aus queue_registry.require("gui").

    Logging:
        - Drei getrennte Log-Queues in queue_registry:
          px4_log_queue, sim_log_queue, qgcr_log_queue
        - Werden im gui_tick in das LogTab geschrieben.
    """

    # Erlaubte Button-Events (Schutz gegen Tippfehler)
    VALID_BUTTON_EVENTS = {
        "ARM",
        "DISARM",
        "TAKEOFF",
        "LAND",
        "MISSION_START",
        "MISSION_UPLOAD",
        "MISSION_DOWNLOAD",
        "MISSION_VALIDATE",
        "MISSION_STOP",
        "RESET",            # <--- NEU
        "STOP",             # <--- optional, falls du STOP global willst
        "INTERCEPT_TRIGGER",
        "INTERCEPT_ABORT",
    }

    def __init__(self, model, state_machine, main_window, queue_registry):
        self.model = model
        self.state_machine = state_machine
        self.main_window = main_window
        self.queue_registry = queue_registry
        self.root = None

    # ------------------------------------------------------------
    # GUI → Model (Tab-Wechsel)
    # READY/MISSION werten model.active_tab zustandsbasiert aus.
    # ------------------------------------------------------------
    def on_tab_changed(self, tab_name: str):
        self.model.active_tab = tab_name

    # ------------------------------------------------------------
    # GUI → HFSM Events (Buttons)
    # ------------------------------------------------------------
    def handle_button_event(self, event_name: str):
        """
        Buttons senden Events in die HFSM-Event-Queue.
        Schutz gegen Tippfehler durch Whitelist.
        """
        print("GUIController: Button Event =", event_name)

        if event_name not in self.VALID_BUTTON_EVENTS:
            print(f"Warnung: Unbekanntes Button-Event '{event_name}' ignoriert.")
            return

        try:
            self.model.hfsm_events.append(event_name)
            print("HFSM Queue nach append:", list(self.model.hfsm_events))
        except Exception as e:
            print(f"HFSM event error (button {event_name}):", e)

    # ------------------------------------------------------------
    # GUIEventLoop → GUI
    # ------------------------------------------------------------
    def on_gui_event_status(self, text):
        pass

    def on_gui_event_log(self, text):
        pass

    def on_gui_event_telemetry(self, telemetry_dict):
        if self.main_window:
            self.main_window.update_telemetry(telemetry_dict)

    def on_gui_event_mission_item(self, item):
        if self.main_window:
            self.main_window.update_mission_items(item)

    def on_gui_event_buttons(self, mapping):
        if self.main_window:
            self.main_window.set_button_state(mapping)

    def on_gui_event_state(self, state):
        if self.main_window:
            self.main_window.update_state(state)

    # ------------------------------------------------------------
    # HFSM → GUI
    # ------------------------------------------------------------
    def update_buttons(self, state):
        """
        state = dict aus ButtonPolicy, z.B.:
        {
            "takeoff": True,
            "land": False,
            "reset": True,
            ...
        }
        """

        # ------------------------------------------------------------
        # 1) RESET darf nur EINMAL ausgelöst werden
        # ------------------------------------------------------------
        if self.model.hfsm_main == "RESET":
            # RESET-Button hart deaktivieren
            if "reset" in state:
                state["reset"] = False

        # ------------------------------------------------------------
        # 2) TAKEOFF nur erlauben, wenn PX4 ready-to-arm ist
        # ------------------------------------------------------------
        if "takeoff" in state:
            state["takeoff"] = state["takeoff"] and self.model.ready_to_arm

        # ------------------------------------------------------------
        # 3) Buttons an MainWindow weitergeben
        # ------------------------------------------------------------
        if self.main_window:
            self.main_window.set_button_state(state)
            
    # ------------------------------------------------------------
    # Log-Ausgabe von HFSM → GUI
    # ------------------------------------------------------------
    def push_log(self, text: str):
        # QGCR-interne Logs gehen in den QGCR-Log-Channel
        self.model.log.qgcr(text)

    # ------------------------------------------------------------
    # Modellauswahl (HomeTab)
    # ------------------------------------------------------------
    # Im Flug / während eines laufenden RESET kein Modellwechsel
    MODEL_CHANGE_BLOCKED = ("AIRBORNE", "RESET", "INTERCEPT")

    def get_model_choices(self):
        return list(self.model.allowed_models)

    def get_selected_model(self):
        configs = getattr(self.model, "vehicle_configs", None) or []
        return configs[0].model_name if configs else None

    def can_change_model(self):
        return self.model.hfsm_main not in self.MODEL_CHANGE_BLOCKED

    def request_model_change(self, model_name):
        """
        Neues Modell in vehicle_configs eintragen und RESET auslösen:
        RESET stoppt PX4, STARTUP startet es mit dem neuen Modell.
        """
        if model_name not in self.model.allowed_models:
            self.model.log.qgcr(f"[GUIController] Unbekanntes Modell '{model_name}' ignoriert")
            return False

        if model_name == self.get_selected_model():
            return False

        if not self.can_change_model():
            self.model.log.qgcr(
                f"[GUIController] Modellwechsel in {self.model.hfsm_main} nicht erlaubt"
            )
            return False

        old = self.model.vehicle_configs[0]
        self.model.vehicle_configs = [
            PX4InstanceConfig(old.px4_dir, model_name, old.instance_id, old.verbose)
        ]
        self.model.log.qgcr(f"[GUIController] Modellwechsel → {model_name} (RESET)")
        self.handle_button_event("RESET")
        return True

    # ------------------------------------------------------------
    # FSL-Tab (kontrollierte FSL-Drohne)
    # ------------------------------------------------------------
    FSL_MODEL = "gz_fsl_rocket_vtol"

    def send_trigger(self, values):
        """Werte aus dem FSL-Tab → Trigger + Parameter ins Model, Event an InterceptHFSM."""
        if self.model.hfsm_main != "INTERCEPT":
            self.model.intercept_status = "Trigger nur im FSL-Tab (INTERCEPT) möglich"
            return False
        try:
            trigger = Trigger(
                drone_id=values.get("drone_id") or "T?",
                timestamp=time.time(),
                east=float(values["east"]), north=float(values["north"]), up=float(values["up"]),
                v_east=float(values["v_east"]), v_north=float(values["v_north"]),
                v_up=float(values.get("v_up") or 0.0),
            )
            config = InterceptConfig(
                speed=float(values["speed"]), timeout=float(values["timeout"]),
                battery_min=float(values["battery_min"]),
            )
        except (KeyError, ValueError) as e:
            self.model.intercept_status = f"Eingabe ungültig: {e}"
            return False

        if config.speed <= 0 or config.timeout <= 0:
            self.model.intercept_status = "Eingabe ungültig: Geschwindigkeit und Timeout müssen > 0 sein"
            return False

        self.model.intercept_config = config
        self.model.intercept_trigger = trigger
        self.handle_button_event("INTERCEPT_TRIGGER")
        return True

    def abort_intercept(self):
        self.handle_button_event("INTERCEPT_ABORT")

    def switch_to_fsl_model(self):
        """Aus dem FSL-Tab (am Boden): Modell auf FSL umstellen (RESET + Neustart)."""
        if self.get_selected_model() == self.FSL_MODEL:
            return False
        if not (self.model.hfsm_main == "INTERCEPT" and self.model.hfsm_sub == "IDLE"):
            return False
        old = self.model.vehicle_configs[0]
        self.model.vehicle_configs = [
            PX4InstanceConfig(old.px4_dir, self.FSL_MODEL, old.instance_id, old.verbose)
        ]
        self.model.log.qgcr(f"[GUIController] FSL-Tab: Modellwechsel → {self.FSL_MODEL} (RESET)")
        self.handle_button_event("RESET")
        return True

    def update_fsl_tab(self):
        tab = getattr(self.main_window, "fsl_tab", None) if self.main_window else None
        m = self.model
        in_intercept = m.hfsm_main == "INTERCEPT"
        sub = m.hfsm_sub if in_intercept else "-"
        fsl = self.get_selected_model() in (None, self.FSL_MODEL)

        # HomeTab-Buttons und Modellwahl sind im FSL-Einsatz inaktiv
        home = getattr(self.main_window, "home_tab", None) if self.main_window else None
        if home is not None and hasattr(home, "set_buttons_enabled"):
            home.set_buttons_enabled(not in_intercept)

        if tab is None:
            return

        tab.set_enabled(trigger=in_intercept and sub == "IDLE" and fsl,
                        abort=in_intercept and sub in ("UPLOAD", "START", "FLIGHT"),
                        model_hint=in_intercept and sub == "IDLE" and not fsl)

        plan = m.intercept_plan
        if plan is None:
            plan_text = "Plan: -"
        elif plan.reachable:
            e, n, u = plan.wait
            plan_text = (f"Wartepunkt: Ost {e:.0f} m, Nord {n:.0f} m, Höhe {u:.0f} m\n"
                         f"FSL dort nach {plan.t_fsl:.0f} s, Trigger nach {plan.t_trigger:.0f} s, "
                         f"Warten {plan.hold:.0f} s, Kurs {plan.heading_deg:.0f}°")
        else:
            plan_text = f"Plan: {plan.reason}"

        battery = f"{m.battery_remaining:.0f} %" if m.battery_remaining is not None else "-"
        flight = f"Akku: {battery}   Höhe: {m.vehicle_alt:.1f} m   Modus: {m.px4_mode}"
        model_hint = "" if fsl else f"\nModell {self.FSL_MODEL} erforderlich"
        tab.show_status(f"{m.hfsm_main}/{sub}", f"{m.intercept_status}{model_hint}", plan_text, flight)

        data = self.get_plot_data()
        tab.plot.draw(data)
        tab.alt_plot.draw(self.get_alt_plot_data())

    def update_model_selector(self):
        """Auswahlliste im HomeTab aktualisieren (aus gui_tick)."""
        home = getattr(self.main_window, "home_tab", None) if self.main_window else None
        if home is None or not hasattr(home, "set_model"):
            return
        home.set_model(self.get_selected_model(), enabled=self.can_change_model())

    # ------------------------------------------------------------
    # 2D-Plot (HomeTab)
    # ------------------------------------------------------------
    def get_plot_data(self):
        """Track, Wegpunkte, Start/Landung, Position für den 2D-Plot (Grad)."""
        m = self.model
        start, landing = m.mission_markers()
        vehicle = (m.vehicle_lat, m.vehicle_lon) if m.vehicle_lat is not None and m.vehicle_lon is not None else None
        waypoints = [(wp["x"], wp["y"]) for wp in list(m.mission.items)
                     if wp["command"] in (16, 21, 22, 31, 85) and (wp["x"] or wp["y"])]

        geometry = m.intercept_geometry()
        extras = {}
        if geometry:
            extras = {
                "circle": geometry["circle"],
                "trigger_path": [p[:2] for p in geometry["trigger_path"]],
                "wait": geometry["wait"][:2] if geometry["wait"] else None,
            }

        return {
            **extras,
            "track": list(m.mission_track),        # Kopie (Update-Thread hängt an)
            "waypoints": waypoints if m.mission.ready else [],
            "start": start,
            "landing": landing,
            "vehicle": vehicle,
        }

    def get_alt_plot_data(self):
        """Höhenverlauf der Mission: {"samples": [(t, alt), ...]}."""
        return {"samples": list(self.model.mission_alt_track)}

    def clear_track(self):
        """Button „Track löschen“: Track und Höhenverlauf im Plot leeren."""
        self.model.clear_track()
        self.model.log.qgcr("[GUIController] Track gelöscht")

    def update_plot(self):
        home = getattr(self.main_window, "home_tab", None) if self.main_window else None
        if home is None:
            return
        plot = getattr(home, "canvas", None)
        if plot is not None and hasattr(plot, "draw"):
            plot.draw(self.get_plot_data())
        alt_plot = getattr(home, "alt_plot", None)
        if alt_plot is not None and hasattr(alt_plot, "draw"):
            alt_plot.draw(self.get_alt_plot_data())

    # ------------------------------------------------------------
    # GUI-Queue → Anzeige (aus gui_tick, Tk-Thread)
    # ------------------------------------------------------------
    def process_gui_queue(self):
        """
        ("status", text) → StatusBar (letzte Meldung) + QGCR-Log
        ("log", text)    → QGCR-Log
        Telemetrie/State-Updates werden verworfen (gui_tick liest das Model direkt).
        """
        window = self.main_window
        status_bar = getattr(window, "status_bar", None) if window else None
        log_tab = getattr(window, "log_tab", None) if window else None

        for item in self.queue_registry.require("gui").pop_all():
            try:
                tag, payload = item
            except (TypeError, ValueError):
                continue

            match tag:
                case "status":
                    if status_bar:
                        status_bar.set_message(str(payload))
                    if log_tab:
                        log_tab.append_qgcr(f"[STATUS] {payload}")
                case "log":
                    if log_tab:
                        log_tab.append_qgcr(str(payload))
                case _:
                    pass

    # ------------------------------------------------------------
    # Mission-Upload: .plan wählen → laden → Event an MissionHFSM
    # ------------------------------------------------------------
    def request_mission_upload(self, path=None):
        if self.model.hfsm_main != "MISSION":
            return

        if path is None:
            from tkinter import filedialog
            path = filedialog.askopenfilename(
                title="QGC-Mission laden",
                initialdir=os.path.expanduser("~"),
                filetypes=[("QGC Plan", "*.plan"), ("Alle Dateien", "*")],
            )
            if not path:
                return

        try:
            items = load_qgc_plan(path)
        except Exception as e:
            self.model.mission_status = f"Plan-Datei fehlerhaft: {e}"
            self.model.log.qgcr(f"[GUIController] Plan-Datei fehlerhaft ({path}): {e}")
            return

        self.model.mission_upload_items = items
        self.model.mission_upload_file = path
        self.model.log.qgcr(f"[GUIController] Plan geladen: {path} ({len(items)} Items)")
        self.handle_button_event("MISSION_UPLOAD")

    def update_mission_tab(self):
        """MissionTab aktualisieren (aus gui_tick)."""
        if not (self.main_window and getattr(self.main_window, "mission_tab", None)):
            return

        in_mission = self.model.hfsm_main == "MISSION"
        idle = (
            in_mission
            and self.model.hfsm_sub == "IDLE"
            and getattr(self.model, "mission_ms", None) is not None
        )
        transfer = in_mission and self.model.hfsm_sub in ("UPLOAD", "DOWNLOAD")

        tab = self.main_window.mission_tab
        start = idle and self.model.mission.ready
        tab.set_enabled(upload=idle, download=idle, stop=transfer, start=start)
        tab.show_mission(self.get_mission_view_data())

    # ------------------------------------------------------------
    # VIEW → CONTROLLER → MODEL (MissionTab)
    # ------------------------------------------------------------
    def get_mission_view_data(self):
        if (
            self.model.home_lat is not None
            and self.model.home_lon is not None
            and self.model.home_alt is not None
        ):
            home_text = (
                f"Home: {self.model.home_lat:.5f}, "
                f"{self.model.home_lon:.5f}, "
                f"{self.model.home_alt:.1f} m"
            )
        else:
            home_text = "Home: -"

        mission = self.model.mission

        if mission.ready and mission.count > 0:
            mission_text = f"Mission: {mission.count} Waypoints"
        else:
            mission_text = "Mission: -"

        waypoints = []
        if mission.ready and mission.items:
            for wp in mission.items:
                waypoints.append(
                    f"{wp['seq']:02d}: CMD {wp['command']} "
                    f"({wp['x']:.5f}, {wp['y']:.5f}, {wp['z']:.1f})"
                )

        return {
            "home_text": home_text,
            "mission_text": mission_text,
            "waypoints": waypoints,
            "status_text": f"Status: {getattr(self.model, 'mission_status', '-')}",
        }

    # ------------------------------------------------------------
    # StatusBar-Polling + Log-Polling
    # ------------------------------------------------------------
    def start_gui_tick(self):
        self.last_hfsm = None
        self.last_sub = None
        self.last_mode = None
        self.last_hb = None

        if self.root:
            self.root.after(200, self.gui_tick)

    def gui_tick(self):
        # ------------------------------------------------------------
        # Neue Log-Verarbeitung (3 getrennte Fenster)
        # ------------------------------------------------------------
        # PX4-Logs
        while not self.queue_registry.px4_log_queue.empty():
            msg = self.queue_registry.px4_log_queue.get()
            if self.main_window and self.main_window.log_tab:
                self.main_window.log_tab.append_px4(msg)

        # Simulator-Logs
        while not self.queue_registry.sim_log_queue.empty():
            msg = self.queue_registry.sim_log_queue.get()
            if self.main_window and self.main_window.log_tab:
                self.main_window.log_tab.append_sim(msg)

        # QGCR-Logs
        while not self.queue_registry.qgcr_log_queue.empty():
            msg = self.queue_registry.qgcr_log_queue.get()
            if self.main_window and self.main_window.log_tab:
                self.main_window.log_tab.append_qgcr(msg)

        # ------------------------------------------------------------
        # GUI-Queue (Status-/Log-Meldungen) leeren
        # ------------------------------------------------------------
        self.process_gui_queue()

        # ------------------------------------------------------------
        # Statusbar aktualisieren
        # ------------------------------------------------------------
        if self.main_window and self.main_window.status_bar:
            self.main_window.status_bar.set_hfsm_state(self.model.hfsm_main)
            self.main_window.status_bar.set_sub_state(self.model.hfsm_sub)
            self.main_window.status_bar.set_mode(self.model.px4_mode)
            self.main_window.status_bar.set_armed(self.model.px4_armed)
            self.main_window.status_bar.set_hb(self.model.px4_heartbeat_count)
            self.main_window.status_bar.spin()

        # MissionTab (Buttons, Mission, Status)
        self.update_mission_tab()

        # HomeTab (Modellauswahl, 2D-Plot), FSL-Tab
        self.update_model_selector()
        self.update_plot()
        self.update_fsl_tab()

        if self.root:
            self.root.after(500, self.gui_tick)
