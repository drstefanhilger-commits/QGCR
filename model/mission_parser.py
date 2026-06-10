#!/usr/bin/env python3
import json
from pymavlink import mavutil

# ---------------------------------------------------------
#   Hilfsfunktion: Parameter normalisieren
# ---------------------------------------------------------
def sanitize_params(params):
    out = []
    for p in params:
        if p is None:
            out.append(0.0)
        else:
            out.append(float(p))
    return out


# ---------------------------------------------------------
#   DICT → MAVLink MissionItemInt
# ---------------------------------------------------------
def convert_to_mavlink_items(mission_items, target_system=1, target_component=1):
    mav_items = []

    for item in mission_items:
        seq = item["seq"]
        cmd = item["command"]
        frame = item["frame"]
        p = item["params"]

        # params: [p1,p2,p3,p4,lat,lon,alt]
        p1, p2, p3, p4, lat, lon, alt = p

        msg = mavutil.mavlink.MAVLink_mission_item_int_message(
            target_system,
            target_component,
            seq,
            frame,
            cmd,
            0,          # current
            1,          # autocontinue
            p1, p2, p3, p4,
            int(lat * 1e7),
            int(lon * 1e7),
            alt
        )

        mav_items.append(msg)

    return mav_items


# ---------------------------------------------------------
#   QGC PLAN LADEN → interne Mission-Item-Liste
# ---------------------------------------------------------
def load_qgc_plan(filename):
    with open(filename, "r") as f:
        plan = json.load(f)

    items = plan["mission"]["items"]
    mission_items = []
    seq = 0

    for item in items:

        # -------------------------------------------------
        # SIMPLE ITEMS
        # -------------------------------------------------
        if item["type"] == "SimpleItem":
            cmd = item["command"]
            frame = item["frame"]
            params = sanitize_params(item["params"])

            mission_items.append({
                "seq": seq,
                "command": cmd,
                "frame": frame,
                "params": params
            })
            seq += 1
            continue

        # -------------------------------------------------
        # COMPLEX ITEM: FIXED-WING LANDING PATTERN
        # -------------------------------------------------
        if item["type"] == "ComplexItem" and item["complexItemType"] == "fwLandingPattern":
            print("[INFO] Konvertiere ComplexItem: fwLandingPattern → MAVLink-Kommandos")

            land_lat, land_lon, land_alt = item["landCoordinate"]
            app_lat, app_lon, app_alt = item["landingApproachCoordinate"]

            loiter_radius = float(item.get("loiterRadius", 75))
            loiter_clockwise = item.get("loiterClockwise", True)

            # 1) DO_LAND_START
            mission_items.append({
                "seq": seq,
                "command": mavutil.mavlink.MAV_CMD_DO_LAND_START,
                "frame": mavutil.mavlink.MAV_FRAME_MISSION,
                "params": [0, 0, 0, 0, land_lat, land_lon, land_alt]
            })
            seq += 1

            # 2) NAV_LOITER_TO_ALT
            mission_items.append({
                "seq": seq,
                "command": mavutil.mavlink.MAV_CMD_NAV_LOITER_TO_ALT,
                "frame": mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                "params": [
                    loiter_radius,
                    0,
                    0,
                    1 if loiter_clockwise else -1,
                    app_lat,
                    app_lon,
                    app_alt
                ]
            })
            seq += 1

            # 3) NAV_LAND
            mission_items.append({
                "seq": seq,
                "command": mavutil.mavlink.MAV_CMD_NAV_LAND,
                "frame": mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                "params": [0, 0, 0, 0, land_lat, land_lon, land_alt]
            })
            seq += 1

            continue

    print(f"[INFO] Gesamte Mission Items: {len(mission_items)}")
    return convert_to_mavlink_items(mission_items)
