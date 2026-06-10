# === PFAD-B FULL FILE: QGCR/controller/gui_controller.py ===

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
    # GUI → HFSM Events (Tab-Wechsel)
    # ------------------------------------------------------------
    def on_tab_home(self):
        try:
            self.model.hfsm_events.append("EV_GOTO_READY")
        except Exception as e:
            print("HFSM event error (HOME_TAB):", e)

    def on_tab_mission(self):
        try:
            self.model.hfsm_events.append("EV_GOTO_MISSION")
        except Exception as e:
            print("HFSM event error (MISSION_TAB):", e)

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
        # Statusbar aktualisieren
        # ------------------------------------------------------------
        if self.main_window and self.main_window.status_bar:
            self.main_window.status_bar.set_hfsm_state(self.model.hfsm_main)
            self.main_window.status_bar.set_sub_state(self.model.hfsm_sub)
            self.main_window.status_bar.set_mode(self.model.px4_mode)
            self.main_window.status_bar.set_armed(self.model.px4_armed)
            self.main_window.status_bar.set_hb(self.model.px4_heartbeat_count)
            self.main_window.status_bar.spin()

        if self.root:
            self.root.after(500, self.gui_tick)
