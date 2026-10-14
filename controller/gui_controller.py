# === PFAD-B FULL FILE: QGCR/controller/gui_controller.py ===

import os

from QGCR.model.mission_parser import load_qgc_plan


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

        idle = (
            self.model.hfsm_main == "MISSION"
            and self.model.hfsm_sub == "IDLE"
            and getattr(self.model, "mission_ms", None) is not None
        )

        tab = self.main_window.mission_tab
        tab.set_enabled(upload=idle, download=idle, stop=False)
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

        if self.root:
            self.root.after(500, self.gui_tick)
