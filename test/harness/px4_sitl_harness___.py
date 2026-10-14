# === PFAD-B FULL FILE: QGCR/harness/px4_sitl_harness.py ===

import subprocess
import time
from pymavlink import mavutil
import os


class PX4SITLHarness:
    """
    Startet PX4-SITL, stellt MAVLink-Verbindung her und liefert ein
    minimal kompatibles Model-Objekt für HFSM-Integrationstests.
    """

    def __init__(self, px4_dir=None):
        # Standardpfad für Stefan:
        # ~/PX4-Autopilot
        if px4_dir is None:
            px4_dir = os.path.expanduser(os.environ.get("PX4_DIR", "~/PX4-Autopilot"))

        self.px4_dir = px4_dir
        self.process = None
        self.mav = None
        self.model = None

    # ------------------------------------------------------------
    # PX4-SITL starten
    # ------------------------------------------------------------
    def start_px4(self):
        cmd = ["make", "px4_sitl", "gz_rc_cessna"]

        self.process = subprocess.Popen(
            cmd,
            cwd=self.px4_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # PX4 braucht ~3–5 Sekunden zum Hochfahren
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
        """
        Das Model muss folgende Attribute haben:
        - update_status(str)
        - px4_heartbeat_ok
        - services.takeoff.start()
        - services.takeoff.tick()
        - services.takeoff.done
        - services.takeoff.error
        """

        class Services:
            pass

        # Fuer Multicopter (PX4: OFFBOARD + TAKEOFF)
        # class TakeoffMS:
        #     def __init__(self, mav):
        #         self.mav = mav
        #         self.done = False
        #         self.error = None

        #     def start(self):
        #         # PX4: Mode OFFBOARD + TAKEOFF
        #         self.mav.mav.command_long_send(
        #             self.mav.target_system,
        #             self.mav.target_component,
        #             mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
        #             0,
        #             0, 0, 0, 0,
        #             0, 0, 10  # Zielhöhe 10 m
        #         )

        #     def tick(self):
        #         msg = self.mav.recv_match(type="LOCAL_POSITION_NED", blocking=False)
        #         if msg and msg.z < -1.0:  # Höhe > 1 m
        #             self.done = True

        # Fuer Fixed-Wing (PX4: TAKEOFF)      
        class TakeoffMS:
            def __init__(self, mav):
                self.mav = mav
                self.done = False
                self.error = None

            def start(self):
                # 1) ARM
                self.mav.mav.command_long_send(
                    self.mav.target_system,
                    self.mav.target_component,
                    mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                    0,
                    1, 0, 0, 0, 0, 0, 0
                )

                # 2) Mission mit einem TAKEOFF-Waypoint erzeugen
                # PX4 erwartet: lat, lon in 1e7, alt in m
                lat = 47.397742 * 1e7
                lon = 8.545594 * 1e7
                alt = 50

                # Mission count
                self.mav.mav.mission_count_send(
                    self.mav.target_system,
                    self.mav.target_component,
                    1
                )

                # TAKEOFF waypoint
                self.mav.mav.mission_item_int_send(
                    self.mav.target_system,
                    self.mav.target_component,
                    0,  # seq
                    0,  # frame: MAV_FRAME_GLOBAL_RELATIVE_ALT
                    mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
                    1,  # current
                    1,  # autocontinue
                    0, 0, 0, 0,
                    int(lat),
                    int(lon),
                    alt
                )

                # 3) AUTO.MISSION setzen
                self.mav.mav.command_long_send(
                    self.mav.target_system,
                    self.mav.target_component,
                    mavutil.mavlink.MAV_CMD_DO_SET_MODE,
                    0,
                    mavutil.mavlink.MAV_MODE_AUTO_ARMED,  # mode
                    0, 0, 0, 0, 0, 0
                )

            def tick(self):
                msg = self.mav.recv_match(type="GLOBAL_POSITION_INT", blocking=False)
                if msg and msg.relative_alt > 1500:  # >1.5 m
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


# Convenience-Funktion für Tests
def start_px4_harness(px4_dir=None):
    h = PX4SITLHarness(px4_dir)
    h.start_px4()
    h.connect_mavlink()
    h.create_model()
    return h
