# === PFAD-B FULL FILE: QGCR/core/startup_cleanup.py ===

import os
import signal
import subprocess
import socket
import time
import glob


class StartupCleanup:
    """
    Bereinigt ALLE hängenden Prozesse, Ports und Gazebo-SHM-Reste,
    bevor PX4 und Gazebo gestartet werden.
    """

    PX4_PROCESSES = [
        "px4",
        "px4_sitl",
        "px4_sitl_default",
        "PX4_SIM_MODEL",
    ]

    SIM_PROCESSES = [
        "gz",
        "gzserver",
        "gzclient",
        "gz-sim",
        "ign",
    ]

    MAV_PROCESSES = [
        "micrortps_agent",
        "micrortps_client",
        "mavsdk",
        "mavsdk_server",
    ]

    PYTHON_PROCESSES = [
        "px4_service.py",
        "px4_swarm_starter.py",
    ]

    PORTS_TO_CLEAR = [
        14540, 14550, 14560, 14570,
        11345,
    ]

    @staticmethod
    def _kill_processes_by_name(names):
        for name in names:
            try:
                subprocess.run(["pkill", "-9", "-f", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

    @staticmethod
    def _free_port(port):
        """
        Schließt Ports, indem Prozesse, die sie halten, gekillt werden.
        """
        try:
            result = subprocess.run(
                ["lsof", "-t", f"-i:{port}"],
                capture_output=True,
                text=True
            )
            pids = result.stdout.strip().split("\n")
            for pid in pids:
                if pid.isdigit():
                    os.kill(int(pid), signal.SIGKILL)
        except Exception:
            pass

    @staticmethod
    def _clear_gazebo_shm():
        """
        Entfernt alte Gazebo Shared-Memory Dateien.
        """
        for path in glob.glob("/dev/shm/gz-*"):
            try:
                os.remove(path)
            except Exception:
                pass

    @staticmethod
    def run_full_cleanup():
        """
        Führt die komplette Bereinigung durch.
        """

        # PX4
        StartupCleanup._kill_processes_by_name(StartupCleanup.PX4_PROCESSES)

        # Simulatoren
        StartupCleanup._kill_processes_by_name(StartupCleanup.SIM_PROCESSES)

        # MAVLink / RTPS
        StartupCleanup._kill_processes_by_name(StartupCleanup.MAV_PROCESSES)

        # Python-Reste
        StartupCleanup._kill_processes_by_name(StartupCleanup.PYTHON_PROCESSES)

        # Ports freigeben
        for port in StartupCleanup.PORTS_TO_CLEAR:
            StartupCleanup._free_port(port)

        # Gazebo SHM
        StartupCleanup._clear_gazebo_shm()

        time.sleep(0.3)
