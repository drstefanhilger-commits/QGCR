#!/usr/bin/env python3
"""
Harness-Test für HomeMicroService:
- Verbindet sich mit echtem PX4-SITL
- Lädt Home-Position
"""

from harness.harness_px4_alive import require_px4_alive
from QGCR.communication.microservices.home_microservice import HomeMicroService


def main():
    master, tsys, tcomp = require_px4_alive()

    hs = HomeMicroService(master, tsys, tcomp)

    print("[HARNESS] Lade Home-Position…")
    home = hs.load_home()

    print(f"[HARNESS] Home empfangen:")
    print(f"  lat = {home.latitude}")
    print(f"  lon = {home.longitude}")
    print(f"  alt = {home.altitude}")

    print("[HARNESS] HomeMicroService Harness COMPLETE")


if __name__ == "__main__":
    main()
