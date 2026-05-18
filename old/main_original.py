# === PFAD-B FULL FILE: main.py ===

import sys
import threading
import time

from QGCR.model.model import Model
from QGCR.communication.dispatcher import Dispatcher
from QGCR.communication.connection import Connection
from QGCR.states.state_builder import build_state_machine
from QGCR.states.main_state_machine import MainStateMachine
from QGCR.view.gui_controller import GUIController

# Falls du ein Tkinter- oder Qt-Window hast:
from QGCR.view.main_window import MainWindow


class Application:
    """
    Hauptanwendung:
    - Initialisiert Model, Dispatcher, Connection
    - Baut HFSMs (Startup, Ready, Takeoff)
    - Baut MainStateMachine (inkl. MissionHFSM)
    - Startet Update-Loops
    """

    def __init__(self):
        # --- Model ---
        self.model = Model()

        # --- Dispatcher ---
        self.dispatcher = Dispatcher(model=self.model)
        
        # --- HFSMs erzeugen ---
        (
            self.startup_hfsm,
            self.ready_hfsm,
            self.mission_hfsm,
            self.airborne_hfsm
        ) = build_state_machine(self.model)
        # AirborneHFSM nachträglich verdrahten
        self.airborne_hfsm.dispatcher = self.dispatcher

        # --- MainStateMachine ---
        self.system_sm = MainStateMachine(
            self.model,
            self.dispatcher,
            self.startup_hfsm,
            self.ready_hfsm,
            self.mission_hfsm,
            self.airborne_hfsm
        )

        # --- GUI-Controller ---
        self.gui_controller = GUIController(
            model=self.model,
            system_sm=self.system_sm,
            dispatcher=self.dispatcher
        )

        # --- Connection ---
        self.connection = Connection(
            model=self.model,
            dispatcher=self.dispatcher,
            wait_for_heartbeat=False   # Für ersten Start ohne PX4
        )

        # --- Update-Thread ---
        self.running = True
        self.update_thread = threading.Thread(
            target=self._update_loop,
            daemon=True
        )
        self.update_thread.start()

        # --- GUI starten (falls vorhanden) ---
        self.window = MainWindow(self.gui_controller)
        self.window.mainloop()


    # ----------------------------------------------------------------------
    # UPDATE LOOP
    # ----------------------------------------------------------------------
    def _update_loop(self):
        """
        GUI-Update-Loop:
        - Connection pollt selbstständig im Hintergrund
        - Dispatcher verarbeitet eingehende Messages
        - FSMs laufen deterministisch
        - GUI liest nur das Model
        """

        counter = 0
        while self.running:

            # Dispatcher verarbeitet Messages, die Connection im Hintergrund liefert
            self.dispatcher.on_update()

            # High-Level FSM
            self.system_sm.on_update()

            # GUI aktualisieren
            self.gui_controller.update_telemetry_from_model()

            # Debug alle 100 Zyklen
            # counter += 1
            # if counter >= 100:
            #     print("[main] update loop alive")
            #     counter = 0

            time.sleep(0.01)  # 100 Hz


    # ----------------------------------------------------------------------
    # SHUTDOWN
    # ----------------------------------------------------------------------
    def shutdown(self):
        self.running = False
        time.sleep(0.05)
        self.connection.mav.close()


# --------------------------------------------------------------------------
# ENTRY POINT
# --------------------------------------------------------------------------
if __name__ == "__main__":
    app = Application()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        app.shutdown()
        sys.exit(0)
