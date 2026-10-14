# === PFAD-B FULL FILE: QGCR/view/gui_interface.py ===

class IGUI:
    """
    Abstrakte GUI-Schnittstelle.
    Der GUIController spricht nur noch mit diesem Interface.
    """

    def set_button_state(self, mapping: dict):
        raise NotImplementedError

    def update_status(self, text: str):
        raise NotImplementedError

    def update_log(self, text: str):
        raise NotImplementedError

    def update_mission_items(self, item):
        raise NotImplementedError

    def update_telemetry(self, telemetry_dict):
        raise NotImplementedError
