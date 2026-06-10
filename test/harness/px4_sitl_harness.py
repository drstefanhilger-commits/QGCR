# === PFAD-B FULL FILE: QGCR/harness/px4_sitl_harness.py ===

import os
import time
import subprocess
import psutil
from pymavlink import mavutil


class PX4SITLHarness:
    """
    Minimaler Harness für HFSM-Tests.
    Kein echter Takeoff, kein Mission-Upload.
    Nur: PX4 starten, MAVLink verbinden, Takeoff simulieren.
    """

    def __init__(self, px4_dir=None):
        if px4_dir is None:
            home = os.path.expanduser("~")
            px4_dir = os.path.join(home, "PX4_SITL", "PX4-Autopilot")

        self.px4_dir = px4_dir
        self.process = None
        self.mav = None
        self.model = None

    # ------------------------------------------------------------
    # Zombie-Killer
    # ------------------------------------------------------------
    def kill_zombies(self):
        """
        Killt ALLE relevanten PX4- und Gazebo-Prozesse.
        Extrem robust, um OOM-Kills zu verhindern.
        """

        zombie_names = [
            "px4",
            "px4_sitl",
            "gzserver",
            "gzclient",
            "gz",
            "micrortps_agent",
            "micrortps_client",
            "simulator",
        ]

        # 1) Erst alle Prozesse killen, die so heißen
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                name = proc.info["name"] or ""
                cmd = " ".join(proc.info["cmdline"] or "")

                if any(z in name for z in zombie_names) or any(z in cmd for z in zombie_names):
                    proc.kill()
            except Exception:
                pass

        time.sleep(0.5)

        # 2) Danach sicherheitshalber Ports freiräumen
        # MAVLink: 14540
        # Gazebo: 11345
        ports = [14540, 11345]

        for port in ports:
            for proc in psutil.process_iter(["pid", "connections"]):
                try:
                    conns = proc.connections()
                    for c in conns:
                        if c.laddr.port == port:
                            proc.kill()
                except Exception:
                    pass

        time.sleep(0.5)


    # ------------------------------------------------------------
    # PX4-SITL starten
    # ------------------------------------------------------------
    def start_px4(self):
        self.kill_zombies()

        cmd = ["make", "px4_sitl", "gz_rc_cessna"]

        self.process = subprocess.Popen(
            cmd,
            cwd=self.px4_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        time.sleep(5)

    # ------------------------------------------------------------
    # MAVLink-Verbindung herstellen
    # ------------------------------------------------------------
    def connect_mavlink(self, device="udp:127.0.0.1:14540"):
        self.mav = mavutil.mavlink_connection(device)
        self.mav.wait_heartbeat(timeout=10)

    # ------------------------------------------------------------
    # Model erzeugen
    # ------------------------------------------------------------
    def create_model(self):

        class Services:
            pass

        class TakeoffMS:
            """
            Simulierter Takeoff für HFSM-Tests.
            Kein echter Flug, nur Timeout -> done=True.
            """

            def __init__(self, mav):
                self.mav = mav
                self.done = False
                self.error = None
                self._start_time = None

            def start(self):
                self._start_time = time.time()

                # ARM senden (optional, aber sauber)
                self.mav.mav.command_long_send(
                    self.mav.target_system,
                    self.mav.target_component,
                    mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                    0,
                    1, 0, 0, 0, 0, 0, 0,
                )

            def tick(self):
                # Nach 3 Sekunden simulieren wir "Takeoff complete"
                if self._start_time and (time.time() - self._start_time) > 3:
                    self.done = True

        class Model:
            def __init__(self, mav):
                self.mav = mav
                self.px4_heartbeat_ok = True
                self.services = Services()
                self.services.takeoff = TakeoffMS(mav)

            def update_status(self, msg):
                print("[MODEL]", msg)

        self.model = Model(self.mav)

    # ------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------
    def shutdown(self):
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()


# ------------------------------------------------------------
# Convenience-Funktion (die bei dir gefehlt hat!)
# ------------------------------------------------------------
def start_px4_harness(px4_dir=None):
    h = PX4SITLHarness(px4_dir)
    h.start_px4()
    h.connect_mavlink()
    h.create_model()
    return h
