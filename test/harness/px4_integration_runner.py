#!/usr/bin/env python3
# === PFAD-B FULL FILE: QGCR/harness/px4_integration_runner.py ===

import os
import time
import subprocess
import psutil
from pymavlink import mavutil


PX4_PORT = 14540
GAZEBO_PORT = 11345


# ------------------------------------------------------------
# Zombie-Killer (robust)
# ------------------------------------------------------------
def kill_all_px4_gz():
    names = [
        "px4", "px4_sitl",
        "gzserver", "gzclient", "gz",
        "micrortps_agent", "micrortps_client",
        "simulator"
    ]

    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            name = proc.info["name"] or ""
            cmd = " ".join(proc.info["cmdline"] or "")
            if any(n in name for n in names) or any(n in cmd for n in names):
                proc.kill()
        except Exception:
            pass

    time.sleep(0.5)


# ------------------------------------------------------------
# PX4-SITL starten
# ------------------------------------------------------------
def start_px4(px4_dir):
    return subprocess.Popen(
        ["make", "px4_sitl", "gz_rc_cessna"],
        cwd=px4_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )


# ------------------------------------------------------------
# MAVLink verbinden
# ------------------------------------------------------------
def connect_mavlink():
    mav = mavutil.mavlink_connection(f"udp:127.0.0.1:{PX4_PORT}")
    mav.wait_heartbeat(timeout=20)
    return mav


# ------------------------------------------------------------
# Mission-Upload (TAKEOFF)
# ------------------------------------------------------------
def upload_takeoff_mission(mav):
    lat = int(47.397742 * 1e7)
    lon = int(8.545594 * 1e7)
    alt = 50

    mav.mav.mission_count_send(mav.target_system, mav.target_component, 1)

    while True:
        msg = mav.recv_match(type=["MISSION_REQUEST_INT", "MISSION_REQUEST"], blocking=True, timeout=10)
        if msg.seq == 0:
            break

    mav.mav.mission_item_int_send(
        mav.target_system,
        mav.target_component,
        0,
        mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
        1, 1,
        0, 0, 0, 0,
        lat, lon, float(alt)
    )


# ------------------------------------------------------------
# AUTO.MISSION setzen
# ------------------------------------------------------------
def set_auto_mission(mav):
    base_mode = mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED
    main_mode = 4  # AUTO
    sub_mode = 4   # AUTO.MISSION

    mav.mav.command_long_send(
        mav.target_system,
        mav.target_component,
        mavutil.mavlink.MAV_CMD_DO_SET_MODE,
        0,
        float(base_mode),
        float(main_mode),
        float(sub_mode),
        0, 0, 0, 0
    )


# ------------------------------------------------------------
# Mission starten (QGC macht das IMMER)
# ------------------------------------------------------------
def start_mission(mav):
    mav.mav.command_long_send(
        mav.target_system,
        mav.target_component,
        mavutil.mavlink.MAV_CMD_MISSION_START,
        0,
        0, 0, 0, 0, 0, 0, 0
    )


# ------------------------------------------------------------
# Takeoff überwachen
# ------------------------------------------------------------
def wait_for_takeoff(mav, timeout=30):
    t0 = time.time()
    while time.time() - t0 < timeout:
        msg = mav.recv_match(type="GLOBAL_POSITION_INT", blocking=False)
        if msg and msg.relative_alt > 1500:
            return True
        time.sleep(0.1)
    return False


# ------------------------------------------------------------
# Hauptfunktion
# ------------------------------------------------------------
def run_integration_test(px4_dir):
    kill_all_px4_gz()

    print("Starte PX4-SITL…")
    px4_proc = start_px4(px4_dir)

    print("Warte auf MAVLink…")
    mav = connect