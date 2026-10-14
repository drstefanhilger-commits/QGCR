# === PFAD-B BLOCK: base_state.py ===

class State:
    def __init__(self, fsm):
        self.fsm = fsm
        self.model = fsm.model
        self.gui = fsm.gui

    def on_enter(self):
        pass

    def on_exit(self):
        pass

    def on_update(self):
        pass
