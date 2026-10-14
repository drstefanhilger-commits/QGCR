class BaseStateMachine:
    """
    Gemeinsame Basis für alle Sub-FSMs (Startup, Ready, Mission).

    Öffentliche API:
        update()  -> führt entrance/during/exit aus und liefert next_state zurück

    Interne Methoden:
        on_entrance()
        on_during()  -> liefert optional einen MainState zurück
        on_exit()
    """

    def __init__(self, model, parent):
        self.model = model
        self.parent = parent
        self._entered = False

    # ------------------------------------------------------------
    # Öffentliche Methode: EINZIGER Einstiegspunkt
    # ------------------------------------------------------------
    def update(self):
        """
        Führt automatisch:
            - on_entrance()   (einmalig)
            - on_during()     (jedes Mal)
            - on_exit()       (wenn State verlassen wird)

        Rückgabe:
            - None            → bleib im aktuellen Superstate
            - MainState.X   → Supervisor soll wechseln
        """

        # 1. Eintritt
        if not self._entered:
            self._entered = True
            self.on_entrance()

        # 2. Während
        next_state = self.on_during()

        # 3. Exit (wenn Sub-FSM verlassen wird)
        if next_state is not None:
            self.on_exit()
            self._entered = False

        return next_state

    # ------------------------------------------------------------
    # Sub-FSM überschreibt diese Methoden
    # ------------------------------------------------------------
    def on_entrance(self):
        pass

    def on_during(self):
        return None

    def on_exit(self):
        pass
