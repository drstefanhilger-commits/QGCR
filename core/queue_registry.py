#!/usr/bin/env python3
# === PFAD-B FULL FILE: QGCR/core/queue_registry.py ===
"""
queue_registry.py
-----------------

Zentrale Verwaltung aller Queues im System.

Ziele:
- Single Source of Truth für Event- und Datenflüsse
- Dynamische Registrierung neuer Queues (FSMs, Services, Worker)
- Statische System-Queues (telemetry, fsm, mission, gui)
- Typ-sichere Queue-Erzeugung
- Thread-sicher, deterministisch, testbar
"""

from QGCR.core.queues import (
    TelemetryQueue,
    FSMEventQueue,
    MissionQueue,
    GUIEventQueue,
    BaseQueue,
)


class QueueRegistry:
    """
    Registry für alle Queues im System.

    - Statische Queues:
        telemetry  → RingBufferQueue (hochfrequent)
        fsm        → FSMEventQueue (deterministisch)
        mission    → MissionQueue
        gui        → GUIEventQueue

    - Dynamische Queues:
        Beliebige Worker/FSM/Service-Queues via register(name, type)
    """

    SYSTEM_QUEUES = {
        "telemetry": TelemetryQueue,
        "fsm": FSMEventQueue,
        "mission": MissionQueue,
        "gui": GUIEventQueue,
    }

    def __init__(self):
        # Statische Queues erzeugen
        self._queues = {
            name: qtype()
            for name, qtype in self.SYSTEM_QUEUES.items()
        }

    # ------------------------------------------------------------
    # Registrierung
    # ------------------------------------------------------------
    def register(self, name: str, queue_type=BaseQueue):
        """
        Registriert eine neue Queue.

        :param name: Name der Queue
        :param queue_type: Klasse, die von BaseQueue erbt
        """
        if name in self._queues:
            raise ValueError(f"Queue '{name}' existiert bereits.")

        if not issubclass(queue_type, BaseQueue):
            raise TypeError(
                f"Queue-Typ '{queue_type}' muss von BaseQueue erben."
            )

        self._queues[name] = queue_type()
        return self._queues[name]

    # ------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------
    def get(self, name: str):
        """
        Gibt eine Queue zurück oder None.
        """
        return self._queues.get(name)

    def require(self, name: str):
        """
        Gibt eine Queue zurück oder wirft Fehler.
        """
        if name not in self._queues:
            raise KeyError(f"Queue '{name}' existiert nicht.")
        return self._queues[name]

    # ------------------------------------------------------------
    # Verwaltung
    # ------------------------------------------------------------
    def exists(self, name: str) -> bool:
        return name in self._queues

    def list(self):
        """
        Liefert alle Queue-Namen.
        """
        return list(self._queues.keys())

    def clear_dynamic(self):
        """
        Entfernt alle dynamischen Queues.
        System-Queues bleiben erhalten.
        """
        self._queues = {
            name: q
            for name, q in self._queues.items()
            if name in self.SYSTEM_QUEUES
        }

    def clear_all(self):
        """
        Entfernt ALLE Queues (nur für Tests).
        """
        self._queues.clear()
