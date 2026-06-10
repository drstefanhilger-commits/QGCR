#!/usr/bin/env python3
"""
mission_microservice.py
-----------------------

Implementiert den MAVLink Mission Upload Microservice
exakt nach QGroundControl-Verhalten.

Verwendet:
- MISSION_COUNT
- MISSION_REQUEST / MISSION_REQUEST_INT
- MISSION_ITEM_INT
- MISSION_ACK
"""

from pymavlink import mavutil


class MissionMicroService:
    def __init__(self, master, target_system, target_component):
        self.master = master
        self.target_system = target_system
        self.target_component = target_component

    # ------------------------------------------------------------
    # Mission Upload
    # ------------------------------------------------------------
    def upload(self, mission_items):
        print(f"[MS] Sende MISSION_COUNT = {len(mission_items)}")
        self.master.mav.mission_count_send(
            self.target_system,
            self.target_component,
            len(mission_items)
        )

        while True:
            print("[MS] Warte auf PX4 MISSION_REQUEST / MISSION_ACK…")
            msg = self.master.recv_match(
                type=["MISSION_REQUEST", "MISSION_REQUEST_INT", "MISSION_ACK"],
                blocking=True
            )
            print(f"[MS] Empfangen: {msg}")

            mtype = msg.get_type()

            # PX4 fordert Item an
            if mtype in ["MISSION_REQUEST", "MISSION_REQUEST_INT"]:
                seq = msg.seq
                print(f"[MS] PX4 fordert Item {seq} an")

                item = mission_items[seq]
                print(f"[MS] → Sende MISSION_ITEM_INT seq={item.seq}")

                self.master.mav.mission_item_int_send(
                    self.target_system,
                    self.target_component,
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

            # PX4 bestätigt Mission
            elif mtype == "MISSION_ACK":
                print(f"[MS] PX4 Mission ACK: {msg.type}")
                print("[MS] Mission Upload COMPLETE")
                return
