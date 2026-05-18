# === PFAD-B FULL FILE: QGCR/view/gui_controller.py ===

class GUIController:
    """
    Vermittelt zwischen GUI, Model und MainWindow.

    GUI → HFSM:
        - Events werden in model.hfsm_events (FIFO deque) geschrieben.
        - HFSM liest ausschließlich aus model.hfsm_events via popleft().

    GUIEventLoop → GUI:
        - Konsumiert Events aus queue_registry.require("gui").

    WICHTIG:
        - GUIController sendet KEINE Status- oder Log-Events.
          Diese kommen ausschließlich aus FSMs.
    """

    # Erlaubte Button-Events (Schutz gegen Tippfehler)
    VALID_BUTTON_EVENTS = {
        "TAKEOFF",
        "LAND",
        "MISSION_START",
        "MISSION_UPLOAD",
        "MISSION_DOWNLOAD",
        "MISSION_VALIDATE",
    }

    def __init__(self, model, state_machine, main_window=None):
        self.model = model
        self.state_machine = state_machine
        self.main_window = main_window

    # ------------------------------------------------------------
    # GUI → HFSM Events (Tab-Wechsel)
    # ------------------------------------------------------------
    def on_tab_home(self):
        """
        HOME-Tab geöffnet → Event in HFSM-Event-Queue.
        """
        try:
            self.model.hfsm_events.append("EV_GOTO_READY")
        except Exception as e:
            print("HFSM event error (HOME_TAB):", e)

    def on_tab_mission(self):
        """
        MISSION-Tab geöffnet → Event in HFSM-Event-Queue.
        """
        try:
            self.model.hfsm_events.append("EV_GOTO_MISSION")
        except Exception as e:
            print("HFSM event error (MISSION_TAB):", e)

    def on_tab_changed(self, tab_name: str):
        """
        GUI-interner Zustand, KEIN FSM-Event.
        """
        self.model.active_tab = tab_name

    # ------------------------------------------------------------
    # GUI → HFSM Events (Buttons)
    # ------------------------------------------------------------
    def handle_button_event(self, event_name: str):
        """
        Buttons senden Events in die HFSM-Event-Queue.
        Schutz gegen Tippfehler durch Whitelist.
        """
        if event_name not in self.VALID_BUTTON_EVENTS:
            print(f"Warnung: Unbekanntes Button-Event '{event_name}' ignoriert.")
            return

        try:
            self.model.hfsm_events.append(event_name)
        except Exception as e:
            print(f"HFSM event error (button {event_name}):", e)

    # ------------------------------------------------------------
    # GUIEventLoop → GUI
    # ------------------------------------------------------------
    def on_gui_event_status(self, text):
        # self.model.add_log(text)
        pass

    def on_gui_event_log(self, text):
        # if self.main_window:
        #     self.main_window.append_log(text)
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
        if self.main_window:
            self.main_window.set_button_state(state)

    # ------------------------------------------------------------
    # Log-Ausgabe von HFSM → GUI
    # ------------------------------------------------------------
    def push_log(self, text: str):
        self.model.add_log(text)

    # ------------------------------------------------------------
    # VIEW → CONTROLLER → MODEL (MissionTab)
    # ------------------------------------------------------------
    def get_mission_view_data(self):
        """
        Liefert View-Daten für MissionTab.
        View greift NICHT direkt auf das Model zu.
        """

        # ---------------- Home ----------------
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

        # ---------------- Mission ----------------
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
# StatusBar-Polling: GUI liest den aktuellen Zustand aus dem Model
# ------------------------------------------------------------
    def start_gui_tick(self):
        """Startet den periodischen GUI-Tick."""
        self.last_hfsm = None
        self.last_sub = None
        self.last_mode = None
        self.last_hb = None

        # ersten Tick starten
        self.root.after(200, self.gui_tick)

    def gui_tick(self):

        # Log-Tab aktualisieren (falls neue Log-Messages vorhanden)
        self.main_window.log_tab.update_logs(self.model.log_messages)

        # HFSM Main
        self.main_window.status_bar.set_hfsm_state(self.model.hfsm_main)

        # HFSM Sub
        self.main_window.status_bar.set_sub_state(self.model.hfsm_sub)

        # PX4 Mode
        self.main_window.status_bar.set_mode(self.model.px4_mode)

        # Armed
        self.main_window.status_bar.set_armed(self.model.px4_armed)

        # Heartbeat
        self.main_window.status_bar.set_hb(self.model.px4_heartbeat_count)

        # Spinner
        self.main_window.status_bar.spin()

        self.root.after(500, self.gui_tick)
