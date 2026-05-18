# === PFAD-B FULL FILE: QGCR/view/button_policy.py ===

from QGCR.states.main_state import MainState


class ButtonPolicy:
    """
    Deklarative Zuordnung von MainState → Button-Zuständen.
    Keine Logik, keine GUI-Abhängigkeit.
    """

    BUTTON_STATES = {
        MainState.STARTUP: {
            "takeoff": False,
            "land": False,
            "arm": False,
            "disarm": False,
            "upload": False,
            "download": False,
        },
        MainState.READY: {
            "takeoff": True,
            "land": False,
            "arm": True,
            "disarm": True,
            "upload": True,
            "download": True,
        },
        MainState.AIRBORNE: {
            "takeoff": False,
            "land": True,
            "arm": False,
            "disarm": False,
            "upload": False,
            "download": False,
        },
    }

    def for_state(self, state):
        return self.BUTTON_STATES.get(state, self.BUTTON_STATES[MainState.STARTUP])
