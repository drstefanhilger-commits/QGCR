#!/usr/bin/env python3

from QGCR.harness.harness_px4_alive import require_px4_alive
from QGCR.communication.microservices.mission_microservice import MissionMicroService
from QGCR.test.utils.mission_item_builder import make_waypoint
import time


def main():
    master, tsys, tcomp = require_px4_alive()

    ms = MissionMicroService(master, tsys, tcomp)

    mission = [
        make_waypoint(0, 47.397742, 8.545594, 10),
        make_waypoint(1, 47.397900, 8.545800, 15),
        make_waypoint(2, 47.398050, 8.546000, 20),
    ]

    print("[HARNESS] Upload Mission…")
    ms.upload(mission)

    time.sleep(1)

    print("[HARNESS] Download Mission…")
    downloaded = ms.download()

    print(f"[HARNESS] Mission Downloaded: {len(downloaded)} Items")
    print("[HARNESS] MissionMicroService Harness COMPLETE")


if __name__ == "__main__":
    main()
