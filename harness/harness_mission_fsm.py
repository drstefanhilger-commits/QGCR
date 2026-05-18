#!/usr/bin/env python3
"""
Harness Test für MissionFSM
---------------------------

Dieser Harness:
- verbindet zu PX4 über Port #0 (udpout:127.0.0.1:18570)
- erzeugt 3 gültige MissionItems
- lädt sie in die MissionFSM
- führt den vollständigen Mission-Upload durch
- prüft, ob PX4 korrekt reagiert

Voraussetzungen:
- PX4 läuft (make px4_sitl gz_rc_cessna)
- Dummy-GCS-Heartbeat läuft
- PX4 ist NICHT im OFFBOARD-Modus
"""

import time
from QGCR.test.utils.mission_fsm import MissionFSM
from QGCR.test.utils.mission_item_builder import make_waypoint


def build_test_mission():
    """Erzeugt eine gültige 3-Waypoint-Mission."""
    items = []
    items.append(make_waypoint(0, 47.397742, 8.545594, 10))
    items.append(make_waypoint(1, 47.397900, 8.545800, 15))
    items.append(make_waypoint(2, 47.398050, 8.546000, 20))
    return items


def main():
    print("[HARNESS] Verbinde zu PX4 auf Port 18570...")
    fsm = MissionFSM()

    print("[HARNESS] Erzeuge Testmission...")
    mission = build_test_mission()
    fsm.load_mission(mission)

    print("[HARNESS] Starte Upload...")
    fsm.start_upload()

    # FSM laufen lassen
    while True:
        fsm.tick()

        if fsm.state.name in ["COMPLETE", "ERROR", "IDLE"]:
            print(f"[HARNESS] FSM beendet mit Zustand: {fsm.state.name}")
            break

        time.sleep(0.05)


if __name__ == "__main__":
    main()
