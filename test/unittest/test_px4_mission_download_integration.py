# === PFAD-B FULL FILE: QGCR/test/test_px4_mission_download_integration.py ===

import unittest

from QGCR.model.model import Model
from QGCR.services.gcs_emulator import MiniQGC
from QGCR.test.utils.px4_startup_synchronizer import PX4StartupSynchronizer


class TestPX4MissionDownloadIntegration(unittest.TestCase):
    """
    E2E-Integrationstest:
    - PX4-SITL muss laufen (make px4_sitl gz_rc_cessna)
    - MiniQGC emuliert ein Ground Control Station-Verhalten auf Port 14550
    - Test FAILT, wenn:
      - kein MISSION_COUNT kommt
      - keine MISSION_ITEM_INT kommen
      - Mission nicht als geladen markiert wird
    """

    def test_px4_mission_download(self):
        print("\n[TEST] PX4-Mission-Download-Integration startet")

        model = Model()
        gcs = MiniQGC()

        try:
            # 1) PX4-Startup-Sync (nur zur Sicherheit, dass PX4 sendet)
            sync = PX4StartupSynchronizer(timeout=30.0)
            first_msg = sync.wait_until_ready()
            print(f"[TEST] PX4-Link bereit, erste Message: {first_msg.get_type()}")

            # 2) Missions-Download starten
            print("[TEST] Starte MiniQGC-Missions-Download")
            gcs.start_mission_download()

            # 3) Event-Loop bis Abschluss oder Timeout
            got_count, got_items, msg_stats = gcs.run_until_complete(model, timeout=45.0)

            # 4) Statistik ausgeben
            print("\n[TEST] MAVLink-Statistik (Top 15):")
            for mtype, count in sorted(msg_stats.items(), key=lambda x: -x[1])[:15]:
                print(f"  {mtype:25s} {count:5d}")

            # 5) Assertions
            self.assertTrue(got_count, "MISSION_COUNT wurde nicht empfangen.")
            self.assertGreater(got_items, 0, "Keine MISSION_ITEM_INT Nachrichten empfangen.")
            self.assertTrue(model.mission_loaded, "Mission wurde nicht vollständig geladen.")
            self.assertGreater(len(model.mission_waypoints), 0, "Mission enthält keine Items.")

            print(f"[OK] PX4-Mission-Download erfolgreich, Items: {len(model.mission_waypoints)}")

        finally:
            gcs.close()
