# === PFAD-B FULL FILE: QGCR/main.py ===

import threading
import time
import argparse
import gc
import os
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

from QGCR.communication.microservices.mission_microservice import MissionMicroService

from QGCR.logging.log_router import LogRouter
from QGCR.core.startup_cleanup import StartupCleanup

from QGCR.sim.px4_swarm_starter import PX4InstanceConfig
from QGCR.sim.gazebo_markers import GazeboMarkers


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog="python3 -m QGCR.main", description="QGC Replacement")
    parser.add_argument(
        "--model",
        choices=Model.ALLOWED_MODELS,
        default=Model.DEFAULT_MODEL,
        help=f"PX4/Gazebo-Modell (Standard: {Model.DEFAULT_MODEL})",
    )
    return parser.parse_args(argv)


class Application:

    def __init__(self, model_name=Model.DEFAULT_MODEL):
        if model_name not in Model.ALLOWED_MODELS:
            raise ValueError(f"Unbekanntes Modell '{model_name}', erlaubt: {Model.ALLOWED_MODELS}")

        # Zweite Instanz: die Bereinigung würde die laufende QGCR samt PX4 beenden
        others = StartupCleanup.find_other_qgcr()
        if isinstance(others, list) and others:
            pids = ", ".join(str(pid) for pid, _ in others)
            raise RuntimeError(f"QGCR läuft bereits (PID {pids}) – bitte zuerst beenden")

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

        # Fenster schließen (X) → PX4/Gazebo stoppen, dann beenden
        self._shut_down = False
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)

        # ------------------------------------------------------------
        # Registry + Model
        # ------------------------------------------------------------
        self.queue_registry = QueueRegistry()
        self.model = Model(queue_registry=self.queue_registry)

        # ------------------------------------------------------------
        # PX4-Fahrzeugkonfiguration(en) ins Model legen
        # (StartupHFSM liest model.vehicle_configs)
        # ------------------------------------------------------------
        self.model.vehicle_configs = [
            PX4InstanceConfig(
                px4_dir=os.environ.get("PX4_DIR", "~/PX4-Autopilot"),
                model_name=model_name,
                instance_id=1,
            )
        ]

        # ------------------------------------------------------------
        # Logging
        # ------------------------------------------------------------
        self.log_router = LogRouter(self.model, self.queue_registry)
        self.model.log = self.log_router

        # Start-/Landepunkt in Gazebo (eigener Worker-Thread)
        self.gz_markers = GazeboMarkers(
            px4_dir=os.environ.get("PX4_DIR", "~/PX4-Autopilot"),
            log=self.log_router.qgcr,
        )

        # ------------------------------------------------------------
        # Dispatcher + Connection
        # ------------------------------------------------------------
        self.dispatcher = Dispatcher(self.model)
        self.connection = Connection(self.model, self.dispatcher)
        self.model.connection = self.connection

        # ------------------------------------------------------------
        # Controller
        # ------------------------------------------------------------
        # MicroServiceController erzeugt takeoff, upload_ms, home_ms, reset
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
        # MainWindow einbetten
        # ------------------------------------------------------------
        self.window = MainWindow(
            parent=self.root,
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

    def _update_loop(self):
        while not self._stop:
            try:
                self.connection.process_pending()   # einziger Schreiber des Flugzustands
                self.model.check_timeout()
                self.ms_controller.tick()
                self.main_controller.on_update()
                self._update_gz_markers()
            except Exception as e:
                print("UpdateLoop error:", e)
                traceback.print_exc()

            time.sleep(0.05)

    def _update_gz_markers(self):
        # STARTUP = neue Gazebo-Instanz (Programmstart, RESET, Modellwechsel)
        if self.model.hfsm_main == "STARTUP":
            self.gz_markers.invalidate()
            return
        geometry = self.model.intercept_geometry()
        path = wait = None
        if geometry:
            path = geometry["trigger_path"][:2] if len(geometry["trigger_path"]) >= 2 else None
            wait = geometry["wait"]
        self.gz_markers.request(*self.model.mission_markers(), path=path, wait=wait)

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
            if self._stop:
                return
            time.sleep(0.05)

        # model.mission bleibt MissionData – der Service kommt nach model.mission_ms
        self.model.mission_ms = MissionMicroService(
            self.connection.master,
            self.connection.master.target_system,
            self.connection.master.target_component
        )
        self.model.services.mission = self.model.mission_ms

        print(
            f"MissionMicroService initialisiert (sysid={self.connection.master.target_system}, "
            f"compid={self.connection.master.target_component})"
        )

    def run(self):
        self.window.mainloop()

    def stop(self):
        self._stop = True

        try:
            self.connection.close()
        except Exception:
            pass

        time.sleep(0.1)

    def shutdown(self):
        """
        QGCR beenden: Threads + Verbindung stoppen, von QGCR gestartetes
        PX4/Gazebo beenden, Fenster schließen. Mehrfacher Aufruf ist unschädlich.
        """
        if self._shut_down:
            return
        self._shut_down = True

        self.stop()

        # Alle App-Threads beenden lassen, bevor Tk-Objekte freigegeben werden:
        # Tcl bricht ab, wenn Tk-Objekte in einem Nicht-Hauptthread aufgeräumt werden.
        for thread in (getattr(self, "update_thread", None), getattr(self, "_conn_thread", None)):
            if thread is not None and thread.is_alive() and thread is not threading.current_thread():
                thread.join(timeout=2.0)

        markers = getattr(self, "gz_markers", None)
        if markers is not None:
            markers.stop()

        starter = getattr(self.model, "startup_controller", None)
        if starter is not None and hasattr(starter, "stop_all"):
            try:
                starter.stop_all()
            except Exception as e:
                print("PX4 stop error:", e)

        try:
            self.root.destroy()
        except Exception:
            pass

        # Tk-Reste jetzt im Hauptthread einsammeln (nicht später in einem anderen Thread)
        gc.collect()


if __name__ == "__main__":
    args = parse_args()
    try:
        app = Application(model_name=args.model)
    except RuntimeError as e:
        raise SystemExit(f"QGCR: {e}")
    try:
        app.root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        app.shutdown()
