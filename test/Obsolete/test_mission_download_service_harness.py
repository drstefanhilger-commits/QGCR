# === PFAD-B FULL FILE: QGCR/test/test_mission_download_service_harness.py ===

import time
import unittest
from pymavlink import mavutil

from QGCR.model.model import Model
from QGCR.services.mission_download_service import MissionDownloadService


class TestPX4MissionDownload(unittest.TestCase):

    def test_mission_download(self):
        print("\n[TEST] Starte lokalen Mission-Download-Harness (ohne PX4)")

        # 1. Model + Service
        model = Model()
        service = MissionDownloadService(model)

        # 2. Download starten
        service.start_download()
        self.assertTrue(service._active)

        # 3. Simuliere PX4: MISSION_COUNT = 3
        msg_count = mavutil.mavlink.MAVLink_mission_count_message(
            target_system=255,
            target_component=190,
            count=3
        )
        service.on_mission_count(msg_count)

        # 4. Simuliere PX4: MISSION_ITEM_INT seq=0..2
        items = []
        for seq in range(3):
            msg_item = mavutil.mavlink.MAVLink_mission_item_int_message(
                target_system=255,
                target_component=190,
                seq=seq,
                frame=mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                command=mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                current=0,
                autocontinue=1,
                param1=0, param2=0, param3=0, param4=0,
                x=473566789 + seq,
                y=854321234 + seq,
                z=10 + seq * 10
            )
            items.append(msg_item)
            service.on_mission_item_int(msg_item)

        # 5. Abschluss abwarten (nur für interne Flags)
        time.sleep(0.05)

        # 6. Assertions
        self.assertTrue(model.mission_loaded, "Mission wurde nicht als geladen markiert")
        self.assertEqual(len(model.mission_waypoints), 3)

        self.assertEqual(model.mission_waypoints[0].seq, 0)
        self.assertEqual(model.mission_waypoints[1].seq, 1)
        self.assertEqual(model.mission_waypoints[2].seq, 2)

        self.assertEqual(model.mission_waypoints[0].x, 473566789)
        self.assertEqual(model.mission_waypoints[2].z, 30)

        print("[TEST] Lokaler Mission-Download-Harness erfolgreich.")
