# === PFAD-B FULL FILE: QGCR/view/gui_event_loop.py ===

import threading
import time
import queue


class GUIEventLoop(threading.Thread):
    """
    Pollt die GUI-Event-Queue und tickt die HFSM.
    Sendet nach jedem Tick den aktuellen HFSM-State an MainWindow.
    """

    def __init__(self, root, controller, gui_event_queue: queue.Queue):
        super().__init__(daemon=True)

        self.root = root
        self.controller = controller
        self.gui_event_queue = gui_event_queue

        self._running = True
        self._tick_rate_hz = 20.0
        self._tick_dt = 1.0 / self._tick_rate_hz

    # ------------------------------------------------------------
    # Thread-Loop
    # ------------------------------------------------------------
    def run(self):
        while self._running:
            start = time.time()

            # 1) GUI-Events aus Queue verarbeiten
            self._process_gui_events()

            # 2) HFSM ticken
            # try:
            #     self.controller.state_machine.on_update()
            # except Exception as e:
            #     print("HFSM update error:", e)

            # 3) HFSM-State an GUI senden
            try:
                state = self.controller.state_machine.get_state_dict()
                self.controller.on_gui_event_state(state)
            except Exception as e:
                print("HFSM state dispatch error:", e)

            # 4) Tick-Rate einhalten
            elapsed = time.time() - start
            sleep_time = self._tick_dt - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    # ------------------------------------------------------------
    # GUI-Events aus Queue verarbeiten
    # ------------------------------------------------------------
    def _process_gui_events(self):
        """
        Holt alle Events aus der Queue und leitet sie an den Controller weiter.
        """
        while True:
            try:
                event_type, payload = self.gui_event_queue.get_nowait()
            except queue.Empty:
                break

            if event_type == "status":
                self.controller.on_gui_event_status(payload)

            elif event_type == "log":
                self.controller.on_gui_event_log(payload)

            elif event_type == "telemetry":
                self.controller.on_gui_event_telemetry(payload)

            elif event_type == "mission_item":
                self.controller.on_gui_event_mission_item(payload)

            elif event_type == "buttons":
                self.controller.on_gui_event_buttons(payload)

            elif event_type == "state":
                self.controller.on_gui_event_state(payload)

    # ------------------------------------------------------------
    # Stop
    # ------------------------------------------------------------
    def stop(self):
        self._running = False
