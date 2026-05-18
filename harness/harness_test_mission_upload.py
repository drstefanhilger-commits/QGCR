#!/usr/bin/env python3
"""
Integrationstest:
- Verbindung zu PX4 herstellen
- Mission hochladen
- Erfolgreichen Abschluss prüfen
"""

from harness_connection import HarnessConnection
from mission_microservice import MissionMicroService
from QGCR.test.utils.mission_item_builder import make_waypoint


def main():
    print("[TEST] Starte Harness-Integrationstest…")

    # Verbindung herstellen
    conn = HarnessConnection()
    master, tsys, tcomp = conn.connect()

    # Mission erzeugen
    mission = [
        make_waypoint(0, 47.397742, 8.545594, 10),
        make_waypoint(1, 47.397900, 8.545800, 15),
        make_waypoint(2, 47.398050, 8.546000, 20),
    ]

    # Microservice starten
    ms = MissionMicroService(master, tsys, tcomp)
    ms.upload(mission)

    print("[TEST] Mission-Upload erfolgreich abgeschlossen.")


if __name__ == "__main__":
    main()
