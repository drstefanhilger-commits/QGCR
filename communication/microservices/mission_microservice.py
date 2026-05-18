#!/usr/bin/env python3
"""
mission_microservice.py
-----------------------

MAVLink Mission MicroService:
- Upload
- Download

Wird von StartupHFSM und MissionHFSM verwendet.
"""

from pymavlink import mavutil


class MissionMicroService:
    def __init__(self, master, target_system, target_component, model=None):
        """
        master:           pymavlink MAVLink connection
        target_system:    Ziel-System-ID (PX4)
        target_component: Ziel-Komponenten-ID
        model:            optional, für GUI-Events (queue_registry)
        """
        self.master = master
        self.target_system = target_system
        self.target_component = target_component
        self.model = model

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

    # ------------------------------------------------------------
    # Mission Download (für StartupHFSM)
    # ------------------------------------------------------------
    def download(self):
        print("[MS] Starte Mission Download…")

        self.master.mav.mission_request_list_send(
            self.target_system,
            self.target_component
        )

        msg = self.master.recv_match(type="MISSION_COUNT", blocking=True, timeout=3)
        if msg is None:
            print("[MS] Timeout: Keine MISSION_COUNT Antwort von PX4.")
            return []

        count = msg.count
        print(f"[MS] PX4 meldet {count} Mission Items")

        mission = []

        for seq in range(count):
            print(f"[MS] → Fordere Item {seq} an")
            self.master.mav.mission_request_int_send(
                self.target_system,
                self.target_component,
                seq
            )

            msg = self.master.recv_match(type="MISSION_ITEM_INT", blocking=True, timeout=3)
            if msg is None:
                print(f"[MS] Timeout: Kein MISSION_ITEM_INT für seq={seq}")
                break

            print(f"[MS] Empfangen: {msg}")
            mission.append(msg)

        print("[MS] Mission Download COMPLETE")

        # GUI über komplette Mission informieren (falls model vorhanden)
        if self.model is not None:
            try:
                self.model.queue_registry.require("gui").push(
                    ("mission_update", mission)
                )
            except Exception:
                pass

        return mission
