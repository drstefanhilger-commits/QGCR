#!/usr/bin/env python3
"""
QGC-Style Mission Uploader (mit maximalem Debug)
------------------------------------------------

Dieses Skript:
1. Öffnet eine QGC-kompatible MAVLink-Verbindung (udp:14550)
2. Startet einen GCS-Heartbeat-Thread
3. Wartet auf PX4-Heartbeat (sysid=1)
4. Führt Mission-Upload exakt nach QGC-Sequenz durch
5. Druckt ALLES, was passiert
"""

import time
import threading
from pymavlink import mavutil
from QGCR.test.utils.mission_item_builder import make_waypoint


# ------------------------------------------------------------
# 1) GCS-Heartbeat-Thread
# ------------------------------------------------------------

def gcs_heartbeat(master):
    print("[DBG] Heartbeat-Thread gestartet")
    while True:
        print("[DBG] → Sende GCS HEARTBEAT")
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
    print("[DBG] Warte auf PX4-Heartbeat…")
    while True:
        msg = master.recv_match(type="HEARTBEAT", blocking=True)
        print(f"[DBG] Empfangen: {msg}")

        sysid = msg.get_srcSystem()
        compid = msg.get_srcComponent()

        if sysid == 1:
            print(f"[DBG] PX4 erkannt: sysid={sysid}, compid={compid}")
            return sysid, compid
        else:
            print(f"[DBG] Ignoriere Heartbeat von sysid={sysid}")


# ------------------------------------------------------------
# 3) Mission Upload (QGC-Sequenz)
# ------------------------------------------------------------

def upload_mission(master, target_sys, target_comp, items):
    print(f"[DBG] Sende MISSION_COUNT = {len(items)}")
    master.mav.mission_count_send(target_sys, target_comp, len(items))

    while True:
        print("[DBG] Warte auf PX4 MISSION_REQUEST / MISSION_ACK…")
        msg = master.recv_match(
            type=["MISSION_REQUEST", "MISSION_REQUEST_INT", "MISSION_ACK"],
            blocking=True
        )
        print(f"[DBG] Empfangen: {msg}")

        mtype = msg.get_type()

        if mtype in ["MISSION_REQUEST", "MISSION_REQUEST_INT"]:
            seq = msg.seq
            print(f"[DBG] PX4 fordert Item {seq} an")

            item = items[seq]
            print(f"[DBG] → Sende MISSION_ITEM_INT seq={item.seq}")

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

        elif mtype == "MISSION_ACK":
            print(f"[DBG] PX4 Mission ACK: {msg.type}")
            print("[DBG] Mission Upload COMPLETE")
            return


# ------------------------------------------------------------
# 4) Hauptprogramm
# ------------------------------------------------------------

def main():
    print("[DBG] Öffne MAVLink-Verbindung udp:14550…")
    master = mavutil.mavlink_connection(
        "udp:0.0.0.0:14550",
        source_system=255,
        source_component=0
    )

    # Heartbeat-Thread starten
    threading.Thread(target=gcs_heartbeat, args=(master,), daemon=True).start()

    # Auf PX4-Heartbeat warten
    target_sys, target_comp = wait_for_px4_heartbeat(master)

    # Testmission erzeugen
    print("[DBG] Erzeuge Testmission…")
    mission = [
        make_waypoint(0, 47.397742, 8.545594, 10),
        make_waypoint(1, 47.397900, 8.545800, 15),
        make_waypoint(2, 47.398050, 8.546000, 20),
    ]

    # Mission hochladen
    upload_mission(master, target_sys, target_comp, mission)


if __name__ == "__main__":
    main()
