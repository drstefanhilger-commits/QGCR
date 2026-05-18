# === PFAD-B FULL FILE: QGCR/main.py ===

import threading
import time
import traceback
import tkinter as tk

from QGCR.model.model import Model
from QGCR.communication.connection import Connection
from QGCR.communication.dispatcher import Dispatcher

from QGCR.view.main_window import MainWindow
from QGCR.controller.main_controller import MainController
from QGCR.controller.gui_controller import GUIController
from QGCR.controller.microservice_controller import MicroServiceController

from QGCR.core.queue_registry import QueueRegistry
from QGCR.states.main_state_map import MAIN_STATE_MAP

# MissionMicroService (funktionierende Version)
from QGCR.communication.microservices.mission_microservice import MissionMicroService

from QGCR.microservices.upload_ms import UploadMicroService
from QGCR.microservices.home_ms import HomeMicroService
from QGCR.microservices.takeoff_ms import TakeoffMicroService


class Application:

    def __init__(self):

        # ------------------------------------------------------------
        # Tk-Root erzeugen
        # ------------------------------------------------------------
        self.root = tk.Tk()
        self.root.title("PX4 Ground Control")
        self.root.geometry("1200x850")

        # ------------------------------------------------------------
        # Tk-Root darf wachsen
        # ------------------------------------------------------------
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

        # ------------------------------------------------------------
        # Registry + Model
        # ------------------------------------------------------------
        self.queue_registry = QueueRegistry()
        self.model = Model(queue_registry=self.queue_registry)

        # ------------------------------------------------------------
        # Dispatcher + Connection
        # ------------------------------------------------------------
        self.dispatcher = Dispatcher(self.model)
        self.connection = Connection(self.model, self.dispatcher)
        self.model.connection = self.connection

        # ------------------------------------------------------------
        # MicroServices
        # ------------------------------------------------------------
        self.model.mission = None
        self.model.upload = UploadMicroService(self.model, self.connection)
        self.model.home = HomeMicroService(self.model, self.connection)
        self.model.takeoff = TakeoffMicroService(self.model, self.connection)

        # ------------------------------------------------------------
        # Controller
        # ------------------------------------------------------------
        self.ms_controller = MicroServiceController(self.model)
        self.main_controller = MainController(self.model, MAIN_STATE_MAP)

        self.gui_controller = GUIController(
            model=self.model,
            state_machine=self.main_controller,
            main_window=None
        )
        self.gui_controller.root = self.root

        # ------------------------------------------------------------
        # MainWindow einbetten (Frame!)
        # ------------------------------------------------------------
        self.window = MainWindow(
            parent=self.root,
            controller=self.gui_controller,
            queue_registry=self.queue_registry
        )
        self.window.grid(row=0, column=0, sticky="nsew")

        # ------------------------------------------------------------
        # GUI-Controller bekommt Referenz auf das Fenster
        # ------------------------------------------------------------
        self.gui_controller.main_window = self.window
        self.gui_controller.start_gui_tick()

        # ------------------------------------------------------------
        # Threads
        # ------------------------------------------------------------
        self._stop = False

        self.update_thread = threading.Thread(
            target=self._update_loop,
            daemon=True
        )
        self.update_thread.start()

        self._conn_thread = threading.Thread(
            target=self._connect_loop,
            daemon=True
        )
        self._conn_thread.start()

        # GUI-Tick starten (Spinner)
        self.root.after(200, self.gui_controller.gui_tick)

    # ------------------------------------------------------------
    # Update Loop (FSM + MicroServices)
    # ------------------------------------------------------------
    def _update_loop(self):
        while not self._stop:
            try:
                self.model.check_timeout()
                self.ms_controller.tick()
                self.main_controller.on_update()
            except Exception as e:
                print("UpdateLoop error:", e)
                traceback.print_exc()

            time.sleep(0.05)

    # ------------------------------------------------------------
    # MAVLink Connect Loop
    # ------------------------------------------------------------
    def _connect_loop(self):
        try:
            print("Binding MAVLink UDP on 0.0.0.0:14550 (waiting for PX4 heartbeat)...")
            self.connection.connect()
            print("UDP bind OK. Waiting for PX4 heartbeat...")
        except Exception as e:
            print("Connection error:", e)
            return

        # Warten bis PX4 wirklich da ist:
        # - master existiert
        # - target_system != 0
        # - Model meldet px4_connected
        while (
            self.connection.master is None
            or getattr(self.connection.master, "target_system", 0) == 0
            or not getattr(self.model, "px4_connected", False)
        ):
            time.sleep(0.05)

        # MissionMicroService JETZT initialisieren (Heartbeat ist da, IDs sind gesetzt)
        self.model.mission = MissionMicroService(
            self.connection.master,
            self.connection.master.target_system,
            self.connection.master.target_component
        )

        print(
            f"MissionMicroService initialisiert (sysid={self.connection.master.target_system}, "
            f"compid={self.connection.master.target_component})"
        )

    # ------------------------------------------------------------
    # GUI Mainloop
    # ------------------------------------------------------------
    def run(self):
        self.window.mainloop()

    # ------------------------------------------------------------
    # Stop
    # ------------------------------------------------------------
    def stop(self):
        self._stop = True
        try:
            self.connection.close()
        except Exception:
            pass
        time.sleep(0.1)

if __name__ == "__main__":
    app = Application()
    app.root.mainloop()


# if __name__ == "__main__":
#     app = Application()
#     try:
#         app.run()
#     except KeyboardInterrupt:
#         app.stop()
