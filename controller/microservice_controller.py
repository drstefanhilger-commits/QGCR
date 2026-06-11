# === PFAD-B FULL FILE: QGCR/controller/microservice_controller.py ===

class MicroServiceController:
    """
    Tick-Controller für alle MicroServices.
    Erzeugt KEINE MicroServices mehr.
    Alle MicroServices werden in main.py nach PX4-Connect erzeugt.
    """

    def __init__(self, model):
        self.model = model

        # Reihenfolge der MicroServices im Tick
        self.tick_order = [
            "home",
            "upload",
            "download",
            "takeoff",
            "reset",
            "param_sync",
            "mission",   # optional, falls mission tickbar ist
        ]

    def tick(self):
        """
        Ruft tick() auf allen existierenden MicroServices auf.
        """
        for name in self.tick_order:
            svc = getattr(self.model, name, None)
            if svc and hasattr(svc, "tick"):
                try:
                    svc.tick()
                except Exception as e:
                    print(f"[MicroServiceController] Fehler in {name}.tick(): {e}")
