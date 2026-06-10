#!/usr/bin/env python3
from pymavlink import mavutil

def make_waypoint(seq, lat, lon, alt):
    return mavutil.mavlink.MAVLink_mission_item_int_message(
        target_system=1,
        target_component=1,
        seq=seq,
        frame=mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
        command=mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
        current=1 if seq == 0 else 0,
        autocontinue=1,
        param1=0.0,
        param2=0.0,
        param3=0.0,
        param4=0.0,
        x=int(lat * 1e7),
        y=int(lon * 1e7),
        z=float(alt)
    )
