#!/usr/bin/env python3
"""
QGC-Style Mission Uploader
--------------------------

Ein einzelnes Skript, das:
1. einen GCS-Heartbeat-Thread startet (wie QGC)
2. auf PX4-Heartbeat wartet (sysid=1, compid=1)
3. danach den Mission-Upload startet (QGC-Sequenz)
"""

import time
import threading
from pymavlink import mavutil
from QGCR.test.utils.mission_item_builder import make_waypoint


# ------------------------------------------------------------
# 1) GCS-Heartbeat-Thread (QGC-Style)
# ------------------------------------------------------------

def gcs_heartbeat(master):
    while True:
        master.mav.heartbeat_send(
            mavutil.mavlink.MAV_TYPE_GCS,
            mavutil.mavlink.MAV_AUTOPILOT_INVALID,
            0, 0, 0
        )
        time.sleep(1)


# ------------------------------------------------------------
# 2) Auf PX4-Heartbeat warten
# ------------------------------------------------------------

def wait_for_px4_heartbeat(master):
    print("[QGC] Warte auf PX4-Heartbeat...")
    hb = master.recv_match(type="HEARTBEAT", blocking=True)
    print(f"[QGC] PX4 Heartbeat empfangen: sysid={hb.get_srcSystem()}, compid={hb.get_srcComponent()}")
    return hb.get_srcSystem(), hb.get_srcComponent()


# ------------------------------------------------------------
# 3) Mission Upload (QGC-Sequenz)
# ------------------------------------------------------------

def upload_mission(master, target_sys, target_comp, items):
    print(f"[QGC] Sende MISSION_COUNT = {len(items)}")
    master.mav.mission_count_send(target_sys, target_comp, len(items))

    # PX4 fordert Items nacheinander an
    while True:
        msg = master.recv_match(type=["MISSION_REQUEST", "MISSION_REQUEST_INT", "MISSION_ACK"], blocking=True)

        if msg.get_type() in ["MISSION_REQUEST", "MISSION_REQUEST_INT"]:
            seq = msg.seq
            print(f"[QGC] PX4 fordert Item {seq} an")

            item = items[seq]
            master.mav.mission_item_int_send(
                target_sys,
                target_comp,
                item.seq,
                item.frame,
                item.command,
                item.current,
                item.autocontinue,
                float(item.param1),
                float(item.param2),
                float(item.param3),
                float(item.param4),
                int(item.x),
                int(item.y),
                float(item.z),
            )

        elif msg.get_type() == "MISSION_ACK":
            print(f"[QGC] PX4 Mission ACK: {msg.type}")
            print("[QGC] Mission Upload COMPLETE")
            return


# ------------------------------------------------------------
# 4) Hauptprogramm
# ------------------------------------------------------------

def main():
    print("[QGC] Öffne MAVLink-Verbindung (udp:14550)...")
    master = mavutil.mavlink_connection("udp:127.0.0.1:14550",
                                        source_system=255,
                                        source_component=0)

    # Heartbeat-Thread starten
    threading.Thread(target=gcs_heartbeat, args=(master,), daemon=True).start()

    # Auf PX4-Heartbeat warten
    target_sys, target_comp = wait_for_px4_heartbeat(master)

    # Testmission erzeugen
    mission = [
        make_waypoint(0, 47.397742, 8.545594, 10),
        make_waypoint(1, 47.397900, 8.545800, 15),
        make_waypoint(2, 47.398050, 8.546000, 20),
    ]

    # Mission hochladen
    upload_mission(master, target_sys, target_comp, mission)


if __name__ == "__main__":
    main()
