# === PFAD-B FULL FILE: QGCR/test/unittest/plan_fixture.py ===

import json
import os
import tempfile

from pymavlink import mavutil


WAYPOINTS = [
    (47.397742, 8.545594, 30.0),
    (47.398500, 8.546500, 40.0),
    (47.399000, 8.545000, 50.0),
]


HOME = (47.397742, 8.545594)
M = mavutil.mavlink


def _simple(i, command, lat, lon, alt, p1=0):
    return {
        "type": "SimpleItem",
        "autoContinue": True,
        "command": command,
        "doJumpId": i + 1,
        "frame": M.MAV_FRAME_GLOBAL_RELATIVE_ALT,
        "params": [p1, 0, 0, None, lat, lon, alt],
    }


def write_plan(directory=None, waypoints=WAYPOINTS):
    """
    Schreibt eine minimale QGC-.plan-Datei (SimpleItems, NAV_WAYPOINT) und liefert den Pfad.
    """
    items = [_simple(i, M.MAV_CMD_NAV_WAYPOINT, lat, lon, alt)
             for i, (lat, lon, alt) in enumerate(waypoints)]
    return _write(items, directory)


def write_flight_plan(model_name, directory=None):
    """
    Flugfähige Mission mit Takeoff und Landung am Startpunkt (PX4: MIS_TKO_LAND_REQ = 2).
    VTOL: NAV_TAKEOFF, 2 Wegpunkte, NAV_LAND.
    Fixed-Wing: NAV_TAKEOFF, 2 Wegpunkte, QGC-Landemuster (fwLandingPattern).
    """
    lat, lon = HOME
    if "vtol" in model_name:
        items = [
            _simple(0, M.MAV_CMD_NAV_TAKEOFF, lat, lon, 20),
            _simple(1, M.MAV_CMD_NAV_WAYPOINT, lat + 0.0005, lon, 20),
            _simple(2, M.MAV_CMD_NAV_WAYPOINT, lat + 0.0005, lon + 0.0007, 20),
            _simple(3, M.MAV_CMD_NAV_LAND, lat, lon, 0),
        ]
    else:
        items = [
            _simple(0, M.MAV_CMD_NAV_TAKEOFF, lat + 0.002, lon, 40, p1=15),
            _simple(1, M.MAV_CMD_NAV_WAYPOINT, lat + 0.005, lon + 0.002, 50),
            _simple(2, M.MAV_CMD_NAV_WAYPOINT, lat + 0.005, lon + 0.006, 50),
            {
                "type": "ComplexItem",
                "complexItemType": "fwLandingPattern",
                "version": 2,
                "landCoordinate": [lat, lon, 0],
                "landingApproachCoordinate": [lat - 0.006, lon, 30],
                "loiterRadius": 75,
                "loiterClockwise": True,
            },
        ]
    return _write(items, directory)


def _write(items, directory):
    plan = {
        "fileType": "Plan",
        "version": 1,
        "groundStation": "QGroundControl",
        "geoFence": {"circles": [], "polygons": [], "version": 2},
        "rallyPoints": {"points": [], "version": 2},
        "mission": {
            "version": 2,
            "firmwareType": 12,
            "vehicleType": 1,
            "cruiseSpeed": 15,
            "hoverSpeed": 5,
            "plannedHomePosition": [47.397742, 8.545594, 488],
            "items": items,
        },
    }

    fd, path = tempfile.mkstemp(suffix=".plan", dir=directory)
    with os.fdopen(fd, "w") as f:
        json.dump(plan, f)
    return path
