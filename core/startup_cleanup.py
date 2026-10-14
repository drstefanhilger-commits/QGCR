# === PFAD-B FULL FILE: QGCR/core/startup_cleanup.py ===

import os
import signal
import subprocess
import socket
import time
import glob
import re


class StartupCleanup:
    """
    Bereinigt ALLE hängenden Prozesse, Ports und Gazebo-SHM-Reste,
    bevor PX4 und Gazebo gestartet werden.
    """

    # Programmnamen (argv[0], mit oder ohne Pfad) – exakter Vergleich
    PX4_PROCESSES = [
        "px4",
    ]

    SIM_PROCESSES = [
        "gz",           # Gazebo Harmonic: "gz sim ..."
        "gzserver",
        "gzclient",
        "ign",
    ]

    MAV_PROCESSES = [
        "micrortps_agent",
        "micrortps_client",
        "mavsdk_server",
    ]

    # Python-Skripte (python3 <pfad/>skript.py ...)
    PYTHON_PROCESSES = [
        "px4_service.py",
        "px4_swarm_starter.py",
    ]

    # Zusätzliche, am Zeilenanfang verankerte Kommandozeilen (POSIX-ERE für pkill -f)
    CMDLINE_PATTERNS = [
        r"^make px4_sitl( |$)",
    ]

    PORTS_TO_CLEAR = [
        14540, 14550, 14560, 14570,
        11345,
    ]

    @staticmethod
    def _program_pattern(name):
        """
        Trifft nur Prozesse, deren argv[0] exakt name ist (optional mit Pfad),
        z.B. "px4" oder "/home/.../bin/px4" – aber NICHT "python3 test_px4_x.py".
        """
        return rf"^([^ ]*/)?{re.escape(name)}( |$)"

    @staticmethod
    def _python_script_pattern(script):
        return rf"^([^ ]*/)?python3?(\.[0-9]+)? ([^ ]*/)?{re.escape(script)}( |$)"

    @staticmethod
    def kill_patterns():
        """
        Alle pkill -f Muster der Bereinigung.
        """
        names = (
            StartupCleanup.PX4_PROCESSES
            + StartupCleanup.SIM_PROCESSES
            + StartupCleanup.MAV_PROCESSES
        )
        patterns = [StartupCleanup._program_pattern(n) for n in names]
        patterns += [StartupCleanup._python_script_pattern(s) for s in StartupCleanup.PYTHON_PROCESSES]
        patterns += StartupCleanup.CMDLINE_PATTERNS
        return patterns

    @staticmethod
    def _kill_processes_by_pattern(patterns):
        for pattern in patterns:
            try:
                subprocess.run(["pkill", "-9", "-f", pattern], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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

        # PX4, Simulatoren, MAVLink/RTPS, Python-Reste
        StartupCleanup._kill_processes_by_pattern(StartupCleanup.kill_patterns())

        # Ports freigeben
        for port in StartupCleanup.PORTS_TO_CLEAR:
            StartupCleanup._free_port(port)

        # Gazebo SHM
        StartupCleanup._clear_gazebo_shm()

        time.sleep(0.3)
