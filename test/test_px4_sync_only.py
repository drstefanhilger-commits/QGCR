# === PFAD-B FULL FILE: QGCR/test/test_px4_sync_only.py ===

import unittest
from QGCR.test.utils.px4_startup_synchronizer import PX4StartupSynchronizer
from QGCR.services.mission_download_service import MissionDownloadService
from QGCR.model.model import Model


class TestPX4SyncOnly(unittest.TestCase):

    def test_px4_sync(self):
        print("\n[TEST] PX4-Synchronisationstest startet")

        # PX4 MUSS bereits laufen (make px4_sitl gz_rc_cessna)
        model = Model()
        service = MissionDownloadService(model)

        # Synchronisation über Port 14540
        sync = PX4StartupSynchronizer(timeout=30.0)
        msg = sync.wait_until_ready()

        print(f"[TEST] Erste PX4-Message: {msg.get_type()}")
        print("[TEST] PX4-Synchronisation erfolgreich.")
