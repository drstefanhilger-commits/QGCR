# === PFAD-B FULL FILE: QGCR/communication/dispatcher.py ===

class Dispatcher:
    """
    Minimaler MAVLink-Dispatcher für MicroServices.
    Connection ruft: dispatcher.dispatch(msg)
    """

    def __init__(self, model):
        self.model = model

    def dispatch(self, msg):
        msg_type = msg.get_type()

        # Liste der MicroServices, die Messages erhalten sollen
        targets = [
            getattr(self.model, "mission_ms", None),
            getattr(self.model, "upload_ms", None),
            getattr(self.model, "home_ms", None),
            getattr(self.model, "takeoff", None),
            getattr(self.model, "param_sync", None),
        ]

        for svc in targets:
            if svc and hasattr(svc, "on_message"):
                try:
                    svc.on_message(msg_type, msg)
                except Exception as e:
                    print(f"[Dispatcher] Fehler in {svc.__class__.__name__}.on_message(): {e}")
