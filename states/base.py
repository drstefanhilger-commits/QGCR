# === PFAD-B FULL FILE: QGCR/states/base_fsm.py ===

__all__ = ["Base"]

from abc import ABC, abstractmethod


class Base(ABC):
    """
    Basis- mit sauberem Lifecycle:
    - _on_enter() wird genau einmal beim Eintritt ausgeführt
    - _on_during() sammelt Infos, tickt Microservices, KEINE Statewechsel
    - _on_exit() entscheidet deterministisch den nächsten Zustand
    - on_update() wird in den abgeleiteten Klassen erzeugt 
    """

    def __init__(self, model, state_enum):
        self.model = model
        self.state_enum = state_enum
        self._entered = False

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if "on_update" in cls.__dict__:
            raise TypeError(
                f"{cls.__name__} darf on_update() nicht überschreiben. "
                "Bitte nur _on_enter, _on_during, _on_exit implementieren."
            )

    def on_update(self):
        """
        Ablauf eines Ticks:
        1. _on_enter() beim ersten Eintritt
        2. _on_during() sammelt Infos, setzt interne Felder
        3. _on_exit() entscheidet Übergang und liefert next_state
        4. Statewechsel → _entered=False
        5. Rückgabewert wird an HFSM weitergegeben
        """

        # 1) ENTER
        if not self._entered:
            self._entered = True
            self._on_enter()

        # 2) DURING
        self._on_during()

        # 3) EXIT
        try:
            next_state = self._on_exit()
        except Exception:
            next_state = self.state_enum

        # 4) Statewechsel?
        if next_state != self.state_enum:
            old = self.state_enum
            self.state_enum = next_state
            self._entered = False

            # GUI + Model informieren
            try:
                # # Substate für GUI/HFSM sichtbar machen
                # self.model.hfsm_sub = self.state_enum.name

                # Statewechsel loggen
                self.model.log.qgcr(f"Statewechsel: {old.name} → {next_state.name}")

                # Optional: Statewechsel für andere Systeme
                self.model.queue_registry.require("state").push(self.state_enum)

            except Exception:
                pass

        # 5) Rückgabewert an HFSM weitergeben
        return next_state

    @abstractmethod
    def _on_enter(self):
        pass

    @abstractmethod
    def _on_during(self):
        """Kein return! Nur interne Felder / _next_state setzen."""
        pass

    @abstractmethod
    def _on_exit(self):
        """Muss self._next_state zurückgeben."""
        pass
