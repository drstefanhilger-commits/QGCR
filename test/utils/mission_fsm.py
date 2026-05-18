#!/usr/bin/env python3
"""
Mission Microservice FSM (QGC-Style)
-----------------------------------

Deterministische State Machine für MAVLink Mission Upload.

Verbindung:
- GCS-Port: 14550 (lokal, wie QGC)
- PX4 MAVLink Instance #0: remote port 14550, local 18570
"""

from enum import Enum, auto
import time
from pymavlink import mavutil


class MissionState(Enum):
    IDLE = auto()
    SEND_COUNT = auto()
    WAIT_REQUEST = auto()
    SEND_ITEM = auto()
    WAIT_ACK = auto()
    ERROR = auto()
    COMPLETE = auto()


class MissionFSM:
    def __init__(self, connection_string: str = "udp:127.0.0.1:14550"):
        # Bidirektionale Verbindung (send + recv), nicht udpout
        self.master = mavutil.mavlink_connection(
            connection_string,
            source_system=255,
            source_component=0,
        )

        # PX4-SITL: fast immer sysid=1, compid=1
        self.target_system = 1
        self.target_component = 1

        self.state = MissionState.IDLE
        self.mission_items = []
        self.current_index = 0
        self.last_request_time = 0.0
        self.timeout_sec = 3.0

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------

    def load_mission(self, items):
        """items = Liste von MAVLink_mission_item_int_message"""
        self.mission_items = items

    def start_upload(self):
        if not self.mission_items:
            print("[FSM] Keine Mission geladen.")
            return
        self.current_index = 0
        self.state = MissionState.SEND_COUNT

    def tick(self):
        """Ein FSM-Schritt. Muss regelmäßig aufgerufen werden."""
        match self.state:

            case MissionState.IDLE:
                return

            case MissionState.SEND_COUNT:
                self._send_mission_count()
                self.state = MissionState.WAIT_REQUEST
                self.last_request_time = time.time()

            case MissionState.WAIT_REQUEST:
                if self._timeout():
                    print("[FSM] Timeout in WAIT_REQUEST")
                    self.state = MissionState.ERROR
                    return
                req_seq = self._recv_mission_request()
                if req_seq is not None:
                    self.current_index = req_seq
                    self.state = MissionState.SEND_ITEM

            case MissionState.SEND_ITEM:
                self._send_mission_item(self.current_index)
                # nach jedem Item wieder auf REQUEST warten,
                # ACK kommt nur nach dem letzten Item
                if self.current_index == len(self.mission_items) - 1:
                    self.state = MissionState.WAIT_ACK
                else:
                    self.state = MissionState.WAIT_REQUEST
                self.last_request_time = time.time()

            case MissionState.WAIT_ACK:
                if self._timeout():
                    print("[FSM] Timeout in WAIT_ACK")
                    self.state = MissionState.ERROR
                    return
                ack = self._recv_mission_ack()
                if ack == "ACCEPTED":
                    self.state = MissionState.COMPLETE
                elif ack == "ERROR":
                    self.state = MissionState.ERROR

            case MissionState.ERROR:
                print("[FSM] Mission upload failed.")
                self.state = MissionState.IDLE

            case MissionState.COMPLETE:
                print("[FSM] Mission upload complete.")
                self.state = MissionState.IDLE

    # ------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------

    def _timeout(self) -> bool:
        return (time.time() - self.last_request_time) > self.timeout_sec

    def _send_mission_count(self):
        count = len(self.mission_items)
        print(f"[FSM] Sending MISSION_COUNT = {count}")
        self.master.mav.mission_count_send(
            self.target_system,
            self.target_component,
            count,
        )

    def _send_mission_item(self, index: int):
        item = self.mission_items[index]
        print(f"[FSM] Sending MISSION_ITEM {index}")
        # item ist bereits ein MAVLink_mission_item_int_message
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

    def _recv_mission_request(self):
        msg = self.master.recv_match(
            type=["MISSION_REQUEST", "MISSION_REQUEST_INT"],
            blocking=False,
        )
        if msg:
            print(f"[FSM] PX4 requests item {msg.seq}")
            return msg.seq
        return None

    def _recv_mission_ack(self):
        msg = self.master.recv_match(type="MISSION_ACK", blocking=False)
        if not msg:
            return None

        if msg.type == mavutil.mavlink.MAV_MISSION_ACCEPTED:
            print("[FSM] PX4 ACK: ACCEPTED")
            return "ACCEPTED"

        if msg.type in (
            mavutil.mavlink.MAV_MISSION_ERROR,
            mavutil.mavlink.MAV_MISSION_INVALID,
            mavutil.mavlink.MAV_MISSION_INVALID_PARAM1,
            mavutil.mavlink.MAV_MISSION_INVALID_PARAM2,
            mavutil.mavlink.MAV_MISSION_INVALID_PARAM3,
            mavutil.mavlink.MAV_MISSION_INVALID_PARAM4,
            mavutil.mavlink.MAV_MISSION_INVALID_PARAM5_X,
            mavutil.mavlink.MAV_MISSION_INVALID_PARAM6_Y,
            mavutil.mavlink.MAV_MISSION_INVALID_PARAM7,
            mavutil.mavlink.MAV_MISSION_INVALID_SEQUENCE,
        ):
            print(f"[FSM] PX4 ACK: ERROR ({msg.type})")
            return "ERROR"

        print(f"[FSM] PX4 ACK: {msg.type}")
        return None
