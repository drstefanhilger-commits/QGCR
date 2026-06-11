# === PFAD-B FULL FILE: QGCR/view/tab_router.py ===

class TabRouter:
    """
    Verantwortlich für Tab-Wechsel.
    In der aktuellen Architektur löst ein Tab-Wechsel
    keine FSM- oder Controller-Events mehr aus.
    """

    def __init__(self, controller):
        self.controller = controller

    def on_tab_changed(self, tab_name: str):
        """
        Aktuell keine Aktionen notwendig.
        Tab-Wechsel ist reine GUI-Operation.
        """
        pass
