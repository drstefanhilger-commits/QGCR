#!/usr/bin/env python3
from pymavlink import mavutil


class HomeMicroService:
    def __init__(self, master, target_system, target_component):
        self.master = master
        self.tsys = target_system
        self.tcomp = target_component

    def load_home(self):
        print("[HOME-MS] Fordere Home-Position an…")

        self.master.mav.command_long_send(
            self.tsys,
            self.tcomp,
            mavutil.mavlink.MAV_CMD_GET_HOME_POSITION,
            0,      # confirmation
            0, 0, 0, 0, 0, 0, 0   # param1–param7
        )

        msg = self.master.recv_match(type="HOME_POSITION", blocking=True, timeout=3)
        if msg is None:
            raise TimeoutError("PX4 hat keine HOME_POSITION gesendet.")

        print(f"[HOME-MS] Home-Position empfangen: lat={msg.latitude}, lon={msg.longitude}, alt={msg.altitude}")
        return msg
