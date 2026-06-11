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

from QGCR.communication.microservices.microservice_factory import MicroServiceFactory

# from QGCR.communication.microservices.mission_microservice import MissionMicroService
# from QGCR.communication.microservices.mission_download_microservice import MissionDownloadMicroService
# from QGCR.communication.microservices.upload_microservice import UploadMicroService
# from QGCR.communication.microservices.home_microservice import HomeMicroService
# from QGCR.communication.microservices.parameter_sync_microservice import ParameterSyncMicroService
# from QGCR.communication.microservices.reset_microservice import ResetMicroService
# from QGCR.communication.microservices.takeoff_microservice import TakeoffMicroService

from QGCR.logging.log_router import LogRouter
from QGCR.core.startup_cleanup import StartupCleanup

from QGCR.sim.px4_swarm_starter import PX4InstanceConfig, PX4SwarmStarter


class Application:

    def __init__(self):

        # ------------------------------------------------------------
        # Startup Cleanup (ALLE Ports + Prozesse + SHM)
        # ------------------------------------------------------------
        StartupCleanup.run_full_cleanup()

        # ------------------------------------------------------------
        # Tk-Root erzeugen
        # ------------------------------------------------------------
        self.root = tk.Tk()
        self.root.title("PX4 Ground Control")
        self.root.geometry("1200x850")

        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

        # ------------------------------------------------------------
        # Registry + Model
        # ------------------------------------------------------------
        self.queue_registry = QueueRegistry()
        self.model = Model(queue_registry=self.queue_registry)

        # ------------------------------------------------------------
        # PX4-Fahrzeugkonfiguration(en)
        # ------------------------------------------------------------
        self.model.vehicle_configs = [
            PX4InstanceConfig(
                px4_dir="/home/stefan/PX4_SITL/30Degrees",
                model_name="gz_rc_cessna",
                instance_id=1,
            )
        ]

        # ------------------------------------------------------------
        # Swarm Starter
        # ------------------------------------------------------------
        self.model.swarm_starter = PX4SwarmStarter(
            instances=self.model.vehicle_configs,
            model=self.model
        )

        # ------------------------------------------------------------
        # Logging
        # ------------------------------------------------------------
        self.log_router = LogRouter(self.model, self.queue_registry)
        self.model.log = self.log_router

        # ------------------------------------------------------------
        # Dispatcher + Connection
        # ------------------------------------------------------------
        self.dispatcher = Dispatcher(self.model)
        self.connection = Connection(self.model, self.dispatcher)
        self.model.connection = self.connection

        # ------------------------------------------------------------
        # Controller
        # ------------------------------------------------------------
        self.ms_controller = MicroServiceController(self.model)
        self.main_controller = MainController(self.model, MAIN_STATE_MAP)
        self.gui_controller = GUIController(
            model=self.model,
            state_machine=self.main_controller,
            main_window=None,
            queue_registry=self.queue_registry
        )
        self.gui_controller.root = self.root

        # ------------------------------------------------------------
        # MicroServices factory (erstellt alle MicroServices deterministisch, sobald PX4 verbunden ist)
        # ------------------------------------------------------------
        self.ms_factory = MicroServiceFactory(self.model, self.connection)

        # ------------------------------------------------------------
        # MainWindow einbetten
        # ------------------------------------------------------------
        self.window = MainWindow(
            parent=self.root,
            model=self.model,
            controller=self.gui_controller,
            queue_registry=self.queue_registry
        )
        self.window.grid(row=0, column=0, sticky="nsew")

        self.gui_controller.main_window = self.window
        self.gui_controller.start_gui_tick()
        self.root.after(200, self.gui_controller.gui_tick)

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

    # ------------------------------------------------------------
    # UPDATE LOOP
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
    # CONNECT LOOP
    # ------------------------------------------------------------
    def _connect_loop(self):
        try:
            print("Binding MAVLink UDP on 0.0.0.0:14550 (waiting for PX4 heartbeat)...")
            self.connection.connect()
            print("UDP bind OK. Waiting for PX4 heartbeat...")
        except Exception as e:
            print("Connection error:", e)
            return

        while (
            self.connection.master is None
            or getattr(self.connection.master, "target_system", 0) == 0
            or not getattr(self.model, "px4_connected", False)
        ):
            time.sleep(0.05)

        # ⭐ Jetzt sauber und zentral:
        self.ms_factory.initialize()


        # try:
        #     print("Binding MAVLink UDP on 0.0.0.0:14550 (waiting for PX4 heartbeat)...")
        #     self.connection.connect()
        #     print("UDP bind OK. Waiting for PX4 heartbeat...")
        # except Exception as e:
        #     print("Connection error:", e)
        #     return

        # while (
        #     self.connection.master is None
        #     or getattr(self.connection.master, "target_system", 0) == 0
        #     or not getattr(self.model, "px4_connected", False)
        # ):
        #     time.sleep(0.05)

        # master = self.connection.master
        # ts = master.target_system
        # tc = master.target_component

        # # ------------------------------------------------------------
        # # MicroServices ERST JETZT erzeugen (PX4 ist verbunden)
        # # ------------------------------------------------------------

        # # Mission (klassisch)
        # self.model.mission = MissionMicroService(master, ts, tc)

        # # Upload (FSM, model + connection)
        # self.model.upload = UploadMicroService(self.model, self.connection)

        # # Download (connection, model)
        # self.model.download = MissionDownloadMicroService(self.connection, self.model)

        # # Home (master, ts, tc)
        # self.model.home = HomeMicroService(master, ts, tc)

        # # Takeoff (alter FSM, model + connection)
        # self.model.takeoff = TakeoffMicroService(self.model, self.connection)

        # # Reset (nur model, holt sich alles aus model.connection)
        # self.model.reset = ResetMicroService(self.model)

        # # ParamSync (master, ts, tc)
        # self.model.param_sync = ParameterSyncMicroService(master, ts, tc)

        # print(f"MicroServices initialisiert (sysid={ts}, compid={tc})")

    # ------------------------------------------------------------
    # RUN
    # ------------------------------------------------------------
    def run(self):
        self.window.mainloop()

    # ------------------------------------------------------------
    # STOP (deterministisch)
    # ------------------------------------------------------------
    def stop(self):
        self._stop = True

        try:
            self.model.swarm_starter.cleanup()
        except Exception:
            pass

        try:
            self.connection.close()
        except Exception:
            pass

        time.sleep(0.1)


# ------------------------------------------------------------
# MAIN ENTRY
# ------------------------------------------------------------
if __name__ == "__main__":
    app = Application()
    try:
        app.run()
    finally:
        try:
            app.stop()
        except Exception:
            pass
