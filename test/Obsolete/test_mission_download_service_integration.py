# === PFAD-B FULL FILE: QGCR/test/test_px4_mission_download_integration.py ===

import time
import unittest

from QGCR.model.model import Model
from QGCR.services.mission_download_service import MissionDownloadService
from QGCR.test.utils.px4_startup_synchronizer import PX4StartupSynchronizer


class TestPX4MissionDownloadIntegration(unittest.TestCase):

    def test_px4_mission_download(self):
        print("\n[TEST] PX4-Mission-Download-Integration startet")

        model = Model()
        service = MissionDownloadService(model)

        try:
            # PX4-Startup-Sync: wartet, bis erste MAVLink-Message kommt
            sync = PX4StartupSynchronizer(timeout=30.0)
            first_msg = sync.wait_until_ready()
            print(f"[TEST] PX4-Link bereit, erste Message: {first_msg.get_type()}")

            print("[TEST] MISSION_REQUEST_LIST gesendet")
            service.start_download()

            timeout = 45.0
            start = time.time()

            msg_stats = {}
            got_count = False
            got_items = 0

            while time.time() - start < timeout and not model.mission_loaded:
                # Regelmäßig GCS-Heartbeat senden
                service.send_heartbeat_if_needed()

                msg = service.mav.recv_msg()
                if not msg:
                    time.sleep(0.02)
                    continue

                mtype = msg.get_type()
                msg_stats[mtype] = msg_stats.get(mtype, 0) + 1

                if mtype == "MISSION_COUNT":
                    got_count = True
                    service.on_mission_count(msg)

                elif mtype == "MISSION_ITEM_INT":
                    got_items += 1
                    service.on_mission_item_int(msg)

            print("\n[TEST] MAVLink-Statistik (Top 15):")
            for mtype, count in sorted(msg_stats.items(), key=lambda x: -x[1])[:15]:
                print(f"  {mtype:25s} {count:5d}")

            self.assertTrue(got_count, "MISSION_COUNT wurde nicht empfangen.")
            self.assertGreater(got_items, 0, "Keine MISSION_ITEM_INT Nachrichten empfangen.")
            self.assertTrue(model.mission_loaded, "Mission wurde nicht vollständig geladen.")
            self.assertGreater(len(model.mission_waypoints), 0, "Mission enthält keine Items.")

            print(f"[OK] PX4-Mission-Download erfolgreich, Items: {len(model.mission_waypoints)}")

        finally:
            service.close()
