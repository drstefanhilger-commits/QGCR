# === PFAD-B FULL FILE: main_hfsm_app.py ===

import time
import threading

from QGCR.model.model import Model
from QGCR.states.main.main_hfsm import MainHFSM
from QGCR.states.main_state import MainState
from QGCR.hfsm.hfsm_event_router import HFSMEventRouter, HFSMEvent, EventType


class HFSMApplication:
    """
    Minimal lauffähige Anwendung für das neue HFSM-System.
    - Keine Abhängigkeit zur alten MainStateMachine
    - Keine GUI, kein Dispatcher, keine Connection
    - Reiner HFSM-Test-Launcher
    """

    def __init__(self, update_rate_hz=20.0):
        self.model = Model()
        self.hfsm = MainHFSM(self.model)

        self.update_rate_hz = update_rate_hz
        self.dt = 1.0 / update_rate_hz

        self.running = True
        self.thread = threading.Thread(target=self._update_loop, daemon=True)
        self.thread.start()

        self.event_router = HFSMEventRouter(self.model, self.hfsm)
        self.event_router.route(HFSMEvent(EventType.GUI, "BTN_START"))



    # ------------------------------------------------------------
    # UPDATE LOOP
    # ------------------------------------------------------------
    def _update_loop(self):
        """
        Führt das neue HFSM-System deterministisch aus.
        """
        print("[HFSM] Update loop started")

        while self.running:
            next_state = self.hfsm.on_update()

            # Debug-Ausgabe
            # print(f"[HFSM] State: {next_state}")

            time.sleep(self.dt)

        print("[HFSM] Update loop stopped")

    # ------------------------------------------------------------
    # EVENT HANDLING
    # ------------------------------------------------------------
    def send_event(self, event):
        """
        Delegiert Events an das HFSM.
        """
        self.hfsm.handle_event(event)

    # ------------------------------------------------------------
    # SHUTDOWN
    # ------------------------------------------------------------
    def shutdown(self):
        self.running = False
        time.sleep(0.05)


# ------------------------------------------------------------
# ENTRY POINT
# ------------------------------------------------------------
if __name__ == "__main__":
    app = HFSMApplication(update_rate_hz=20.0)

    print("HFSMApplication running. Press Ctrl+C to exit.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping HFSMApplication...")
        app.shutdown()
