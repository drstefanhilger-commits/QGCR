# === PFAD-B FULL FILE: QGCR/test/unittest/sitl_helper.py ===

import os
import signal
import subprocess
import time
import unittest

from pymavlink import mavutil


# PX4-SITL-Tests starten PX4 + Gazebo Harmonic und dauern entsprechend.
# Aktivieren mit: QGCR_SITL=1 python3 -m unittest ...
requires_sitl = unittest.skipUnless(
    os.environ.get("QGCR_SITL") == "1",
    "PX4-SITL-Test – aktivieren mit QGCR_SITL=1",
)

# Port #0 (QGroundControl-Link): PX4 18570 → QGCR 14550
GCS_URL = "udp:0.0.0.0:14550"


class PX4Sitl:
    """
    Startet PX4-SITL (make px4_sitl gz_rc_cessna) und räumt PX4 + Gazebo Harmonic wieder ab.
    """

    def __init__(self, target="gz_rc_cessna", headless=True):
        self.px4_dir = os.path.expanduser(os.environ.get("PX4_DIR", "~/PX4-Autopilot"))
        self.target = target
        self.headless = headless
        self.process = None

    def start(self):
        self._kill_leftovers()

        env = os.environ.copy()
        if self.headless:
            env["HEADLESS"] = "1"

        self.process = subprocess.Popen(
            ["make", "px4_sitl", self.target],
            cwd=self.px4_dir,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid,
        )

    def stop(self):
        if self.process is not None:
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass
            self.process = None

        self._kill_leftovers()

    @staticmethod
    def _kill_leftovers():
        # px4 exakt per Name, Gazebo Harmonic per Kommandozeile "gz sim ..."
        subprocess.run(["pkill", "-9", "-x", "px4"], stderr=subprocess.DEVNULL)
        subprocess.run(["pkill", "-9", "-f", "^gz sim"], stderr=subprocess.DEVNULL)
        time.sleep(0.5)


def gcs_link():
    """Raw-pymavlink-Link wie QGC/QGCR auf Port #0."""
    return mavutil.mavlink_connection(GCS_URL, source_system=255, source_component=190)


def wait_for(mav, msg_type, timeout):
    """Wartet auf eine Nachricht vom Typ msg_type (oder None nach Timeout)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        msg = mav.recv_match(type=msg_type, blocking=True, timeout=0.5)
        if msg is not None:
            return msg
    return None


def send_gcs_heartbeat(mav):
    mav.mav.heartbeat_send(
        mavutil.mavlink.MAV_TYPE_GCS,
        mavutil.mavlink.MAV_AUTOPILOT_INVALID,
        0,
        0,
        mavutil.mavlink.MAV_STATE_ACTIVE,
    )
