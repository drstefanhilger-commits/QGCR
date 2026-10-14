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


def write_plan(directory=None, waypoints=WAYPOINTS):
    """
    Schreibt eine minimale QGC-.plan-Datei (SimpleItems, NAV_WAYPOINT) und liefert den Pfad.
    """
    items = []
    for i, (lat, lon, alt) in enumerate(waypoints):
        items.append({
            "type": "SimpleItem",
            "autoContinue": True,
            "command": mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
            "doJumpId": i + 1,
            "frame": mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
            "params": [0, 0, 0, None, lat, lon, alt],
        })

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
