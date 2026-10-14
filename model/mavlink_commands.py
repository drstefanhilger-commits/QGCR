#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
mavlink_commands.py
Kapselt alle MAVLink COMMAND_LONG / COMMAND_INT Messages,
die für ARM, MODE, TAKEOFF, Mission etc. benötigt werden.

Dieses Modul erzeugt NUR die MAVLink-Nachrichten (Message Objects),
sendet sie aber NICHT. Das Senden übernimmt die Connection-Schicht.

Kompatibel mit:
- pymavlink 2.4.49
- PX4 v1.14.4
"""

from pymavlink import mavutil


# ---------------------------------------------------------------------------
# Hilfsfunktion: COMMAND_LONG Message erzeugen
# ---------------------------------------------------------------------------
def _cmd_long(
    command: int,
    target_system: int = 1,
    target_component: int = 1,
    p1: float = 0, p2: float = 0, p3: float = 0,
    p4: float = 0, p5: float = 0, p6: float = 0, p7: float = 0
):
    """
    Erzeugt eine MAVLink_command_long_message.
    """
    return mavutil.mavlink.MAVLink_command_long_message(
        target_system=target_system,
        target_component=target_component,
        command=command,
        confirmation=0,
        param1=p1,
        param2=p2,
        param3=p3,
        param4=p4,
        param5=p5,
        param6=p6,
        param7=p7
    )

# ---------------------------------------------------------------------------
# 1) ARM / DISARM
# ---------------------------------------------------------------------------
def cmd_arm(target_system: int = 1, target_component: int = 1):
    """
    MAV_CMD_COMPONENT_ARM_DISARM (400)
    param1 = 1 → arm
    """
    return _cmd_long(
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        target_system, target_component,
        p1=1
    )

def cmd_disarm(target_system: int = 1, target_component: int = 1):
    """
    MAV_CMD_COMPONENT_ARM_DISARM (400)
    param1 = 0 → disarm
    """
    return _cmd_long(
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        target_system, target_component,
        p1=0
    )

# ---------------------------------------------------------------------------
# 2) PX4 MODE SET (AUTO.TAKEOFF / AUTO.LOITER / MANUAL)
# ---------------------------------------------------------------------------

# PX4 Custom Modes
PX4_CUSTOM_MAIN_MODE_MANUAL = 1
PX4_CUSTOM_MAIN_MODE_AUTO = 4

PX4_CUSTOM_SUB_MODE_AUTO_TAKEOFF = 2
PX4_CUSTOM_SUB_MODE_AUTO_LOITER = 3


def cmd_set_mode_takeoff(target_system: int = 1, target_component: int = 1):
    """
    MAV_CMD_DO_SET_MODE (176)
    PX4 AUTO.TAKEOFF:
        base_mode = MAV_MODE_FLAG_CUSTOM_MODE_ENABLED
        custom_mode = (main_mode << 16) | (sub_mode << 24)
    """
    base_mode = mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED
    custom_mode = (PX4_CUSTOM_MAIN_MODE_AUTO << 16) | (PX4_CUSTOM_SUB_MODE_AUTO_TAKEOFF << 24)

    return _cmd_long(
        mavutil.mavlink.MAV_CMD_DO_SET_MODE,
        target_system, target_component,
        p1=base_mode,
        p2=custom_mode
    )


def cmd_set_mode_loiter(target_system: int = 1, target_component: int = 1):
    """
    MAV_CMD_DO_SET_MODE (176)
    PX4 AUTO.LOITER:
        base_mode = MAV_MODE_FLAG_CUSTOM_MODE_ENABLED
        custom_mode = (AUTO << 16) | (LOITER << 24)
    """
    base_mode = mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED
    custom_mode = (PX4_CUSTOM_MAIN_MODE_AUTO << 16) | (PX4_CUSTOM_SUB_MODE_AUTO_LOITER << 24)

    return _cmd_long(
        mavutil.mavlink.MAV_CMD_DO_SET_MODE,
        target_system, target_component,
        p1=base_mode,
        p2=custom_mode
    )


def cmd_set_mode_manual(target_system: int = 1, target_component: int = 1):
    """
    MAV_CMD_DO_SET_MODE (176)
    PX4 MANUAL:
        base_mode = MAV_MODE_FLAG_CUSTOM_MODE_ENABLED
        custom_mode = (MANUAL << 16)
        (kein Submode)
    """
    base_mode = mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED
    custom_mode = (PX4_CUSTOM_MAIN_MODE_MANUAL << 16)

    return _cmd_long(
        mavutil.mavlink.MAV_CMD_DO_SET_MODE,
        target_system, target_component,
        p1=base_mode,
        p2=custom_mode
    )

# ---------------------------------------------------------------------------
# 3) TAKEOFF
# ---------------------------------------------------------------------------
def cmd_takeoff(
    altitude: float,
    target_system: int = 1,
    target_component: int = 1
):
    """
    MAV_CMD_NAV_TAKEOFF (22)
    PX4 ignoriert lat/lon, wenn nicht gesetzt → QGC macht es genauso.
    param7 = altitude (m)
    """
    return _cmd_long(
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
        target_system, target_component,
        p7=altitude
    )

# ---------------------------------------------------------------------------
# 4) ACK-Utility (optional)
# ---------------------------------------------------------------------------
def cmd_land(target_system: int = 1, target_component: int = 1):
    """
    MAV_CMD_NAV_LAND (21) an der aktuellen Position:
    param4 (Yaw) und param5-7 (Lat/Lon/Alt) = NaN → PX4 nutzt aktuelle Werte.
    PX4 wechselt in AUTO.LAND (VTOL: vertikal, Fixed-Wing: Landeanflug).
    """
    nan = float("nan")
    return _cmd_long(
        mavutil.mavlink.MAV_CMD_NAV_LAND,
        target_system, target_component,
        p4=nan, p5=nan, p6=nan, p7=nan
    )


def cmd_mission_start(target_system: int = 1, target_component: int = 1, first_item: int = 0):
    """
    MAV_CMD_MISSION_START (300): PX4 armt (falls nötig) und schaltet in AUTO.MISSION.
    param1 = erstes Item (0 = Missionsanfang), param2 = letztes Item (0 = bis zum Ende).
    """
    return _cmd_long(
        mavutil.mavlink.MAV_CMD_MISSION_START,
        target_system, target_component,
        p1=first_item, p2=0
    )


def is_ack_success(msg) -> bool:
    """
    Prüft, ob ein COMMAND_ACK erfolgreich war.
    """
    if msg is None:
        return False
    return msg.result == mavutil.mavlink.MAV_RESULT_ACCEPTED

def cmd_heartbeat_gcs():
    """
    Erzeugt einen HEARTBEAT wie ein GCS.
    Wird von der Connection-Schicht gesendet.
    """
    return mavutil.mavlink.heartbeat_encode(
        mavutil.mavlink.MAV_TYPE_GCS,
        mavutil.mavlink.MAV_AUTOPILOT_GENERIC,
        0,  # base_mode
        0,  # custom_mode
        mavutil.mavlink.MAV_STATE_ACTIVE
    )

def send_heartbeat(master):
    """
    Sendet einen HEARTBEAT wie ein GCS.
    PX4-kompatibel (common dialect).
    """
    master.mav.heartbeat_send(
        mavutil.mavlink.MAV_TYPE_GCS,
        mavutil.mavlink.MAV_AUTOPILOT_GENERIC,
        0,  # base_mode
        0,  # custom_mode
        mavutil.mavlink.MAV_STATE_ACTIVE
    )

def cmd_mission_request_list(
    target_system: int = 1,
    target_component: int = 1
):
    """
    Fordert die Anzahl der Mission-Items vom Autopiloten an.
    Entspricht MISSION_REQUEST_LIST.
    """
    return mavutil.mavlink.MAVLink_mission_request_list_message(
        target_system=target_system,
        target_component=target_component
    )

def cmd_mission_count(
    count: int,
    target_system: int = 1,
    target_component: int = 1
):
    """
    Sendet die Anzahl der Mission-Items an PX4.
    Entspricht MISSION_COUNT.
    """
    return mavutil.mavlink.MAVLink_mission_count_message(
        target_system=target_system,
        target_component=target_component,
        count=count
    )

def cmd_mission_request(
    seq: int,
    target_system: int = 1,
    target_component: int = 1
):
    """
    Fordert ein einzelnes Mission-Item an.
    Entspricht MISSION_REQUEST.
    """
    return mavutil.mavlink.MAVLink_mission_request_message(
        target_system=target_system,
        target_component=target_component,
        seq=seq
    )

def cmd_mission_item_int(
    seq: int,
    frame: int,
    command: int,
    current: int,
    autocontinue: int,
    param1: float,
    param2: float,
    param3: float,
    param4: float,
    x: int,   # lat * 1e7
    y: int,   # lon * 1e7
    z: float, # altitude
    target_system: int = 1,
    target_component: int = 1
):
    """
    Sendet ein Mission-Item im INT-Format.
    Entspricht MISSION_ITEM_INT.
    """
    return mavutil.mavlink.MAVLink_mission_item_int_message(
        target_system=target_system,
        target_component=target_component,
        seq=seq,
        frame=frame,
        command=command,
        current=current,
        autocontinue=autocontinue,
        param1=param1,
        param2=param2,
        param3=param3,
        param4=param4,
        x=x,
        y=y,
        z=z
    )

def cmd_mission_ack(
    result: int,
    target_system: int = 1,
    target_component: int = 1
):
    """
    Bestätigt Mission-Upload oder -Download.
    Entspricht MISSION_ACK.
    """
    return mavutil.mavlink.MAVLink_mission_ack_message(
        target_system=target_system,
        target_component=target_component,
        type=result
    )
