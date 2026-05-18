# === PFAD-B FULL FILE: QGCR/controller/microservice_controller.py ===

import time

class MicroServiceController:
    """
    Zentraler Tick-Controller für alle MicroServices.
    - deterministische Reihenfolge
    - non-blocking
    - keine FSM-Logik
    - keine GUI-Logik
    - keine MAVLink-Logik
    """

    def __init__(self, model):
        self.model = model

        # Tick-Reihenfolge: benutze die Aliase aus model.*
        self.tick_order = [
            "param_sync",   # bleibt in services
            "mission_ms",
            "upload_ms",
            "home_ms",
            "takeoff",
        ]

    # ------------------------------------------------------------
    # Tick
    # ------------------------------------------------------------
    def tick(self):
        """
        Wird vom MainLoop 20 Hz aufgerufen.
        """
        for name in self.tick_order:

            # param_sync liegt in model.services
            if name == "param_sync":
                svc = getattr(self.model.services, "param_sync", None)
            else:
                svc = getattr(self.model, name, None)

            if svc and hasattr(svc, "tick"):
                try:
                    svc.tick()
                except Exception as e:
                    print(f"[MicroServiceController] Fehler in {name}.tick():", e)
