#!/usr/bin/env python3
"""
Utility für Harness-Tests:
Prüft, ob PX4-SITL läuft und liefert eine gültige MAVLink-Verbindung zurück.
"""

# from QGCR.communication.connection import Connection
from QGCR.harness.harness_connection import HarnessConnection as Connection


def require_px4_alive():
    print("[HARNESS] Prüfe PX4-SITL Verfügbarkeit…")

    try:
        conn = Connection()
        master, tsys, tcomp = conn.connect()
    except Exception as e:
        print(f"[HARNESS] PX4-SITL NICHT erreichbar: {e}")
        raise SystemExit(1)

    print(f"[HARNESS] PX4-SITL läuft (sysid={tsys}, compid={tcomp})")
    return master, tsys, tcomp
