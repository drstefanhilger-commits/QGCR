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

def assert_no_foreign_session():
    """
    SITL-Tests beenden PX4/Gazebo (und die Application räumt Port 14550 frei).
    Läuft bereits eine QGCR-, PX4- oder Gazebo-Sitzung, wird abgebrochen statt beendet.
    """
    own = os.getpid()
    found = []
    for label, args in (("QGCR", ["-af", "--", r"-m QGCR\.main( |$)"]),
                        ("PX4", ["-ax", "px4"]),
                        ("Gazebo", ["-af", "^gz sim"])):
        out = subprocess.run(["pgrep", *args], capture_output=True, text=True).stdout
        for line in out.splitlines():
            pid = line.split(" ", 1)[0]
            if pid.isdigit() and int(pid) != own:
                found.append(f"{label} (PID {pid})")
    if found:
        raise RuntimeError(
            "SITL-Test abgebrochen: laufende Sitzung gefunden – " + ", ".join(found)
            + ". Bitte zuerst beenden; die Tests würden sie sonst beenden."
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
        assert_no_foreign_session()
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


def gz_model_pose(name):
    """(x, y) eines Modells in der Gazebo-Welt oder None."""
    env = dict(os.environ, GZ_IP="127.0.0.1")
    try:
        out = subprocess.run(["gz", "model", "-m", name, "-p"], env=env,
                             capture_output=True, text=True, timeout=15).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    lines = out.splitlines()
    for i, line in enumerate(lines):
        if "Pose [ XYZ" in line and i + 1 < len(lines):
            values = lines[i + 1].strip().strip("[]").split()
            return float(values[0]), float(values[1])
    return None


def persisted_px4_param(name, px4_dir=None):
    """
    Wert eines Parameters in der gespeicherten SITL-Parameterdatei (rootfs/parameters.bson).
    None = nicht gespeichert (PX4-Default gilt). PX4 speichert Änderungen verzögert.
    """
    import struct
    px4_dir = os.path.expanduser(px4_dir or os.environ.get("PX4_DIR", "~/PX4-Autopilot"))
    path = os.path.join(px4_dir, "build", "px4_sitl_default", "rootfs", "parameters.bson")
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return None
    i = 4
    while i < len(data) - 1:
        kind = data[i]
        i += 1
        end = data.index(b"\0", i)
        key = data[i:end].decode()
        i = end + 1
        if kind == 0x01:                              # double
            value = struct.unpack("<d", data[i:i + 8])[0]
            i += 8
        elif kind == 0x10:                            # int32
            value = struct.unpack("<i", data[i:i + 4])[0]
            i += 4
        else:
            raise ValueError(f"unerwarteter BSON-Typ {kind:#x} in {path}")
        if key == name:
            return value
    return None
