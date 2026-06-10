# === PFAD-B FULL FILE: QGCR/controller/microservice_controller.py ===

import time

from QGCR.microservices.takeoff_ms import TakeoffMicroService
from QGCR.microservices.upload_ms import UploadMicroService
from QGCR.microservices.home_ms import HomeMicroService
from QGCR.microservices.reset_microservice import ResetMicroService


class MicroServiceController:
    """
    Zentraler Tick-Controller für alle MicroServices.
    """

    def __init__(self, model):
        self.model = model

        # echte MicroServices erzeugen
        self.model.takeoff   = TakeoffMicroService(model, model.connection)
        self.model.upload_ms = UploadMicroService(model, model.connection)
        self.model.home_ms   = HomeMicroService(model, model.connection)
        self.model.reset     = ResetMicroService(model)   # ⭐ NEU

        # in services spiegeln
        self.model.services.takeoff = self.model.takeoff
        self.model.services.upload  = self.model.upload_ms
        self.model.services.home    = self.model.home_ms
        self.model.services.reset   = self.model.reset     # ⭐ NEU

        self.tick_order = [
            "param_sync",   # liegt in model.services
            "upload_ms",
            "home_ms",
            "takeoff",
            "reset",        # ⭐ NEU
        ]

    def tick(self):
        """
        Wird vom MainLoop 20 Hz aufgerufen.
        """
        for name in self.tick_order:
            if name == "param_sync":
                svc = getattr(self.model.services, "param_sync", None)
            else:
                svc = getattr(self.model, name, None)

            if svc and hasattr(svc, "tick"):
                try:
                    svc.tick()
                except Exception as e:
                    self.model.log.qgcr(f"[MicroServiceController] ERROR in {name}.tick(): {e}")
                    print(f"[MicroServiceController] ERROR in {name}.tick(): {e}")
