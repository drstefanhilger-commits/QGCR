#!/usr/bin/env python3
# === PFAD-B FULL FILE: QGCR/communication/qgc_dispatcher.py ===
"""
qgc_dispatcher.py
-----------------

Zentrale, vollständig entkoppelte Routing-Schicht für MAVLink-Nachrichten.

- QGCConnection ruft: dispatcher.route_message(msg_type, msg)
- Dispatcher ruft registrierte Handler auf
- Keine Kopplung an GUI, Model oder FSM
- Handler können dynamisch registriert/entfernt werden
- Thread-sicher
"""

from collections import defaultdict
from threading import RLock


class QGCDispatcher:
    """
    Entkoppelter MAVLink-Dispatcher:

    - Registriert Handler pro Message-Typ
    - Routet eingehende MAVLink-Nachrichten an alle passenden Handler
    - Thread-sicher (Connection RX-Thread ruft route_message() auf)
    """

    def __init__(self):
        # msg_type -> [handler, handler, ...]
        self._handlers = defaultdict(list)
        self._lock = RLock()

    # ------------------------------------------------------------
    # Handler-Registrierung
    # ------------------------------------------------------------
    def register(self, msg_type: str, handler):
        """
        Registriert einen Handler für einen MAVLink-Message-Typ.

        :param msg_type: z.B. "HEARTBEAT", "MISSION_ITEM_INT"
        :param handler: Funktion handler(msg)
        """
        with self._lock:
            if handler not in self._handlers[msg_type]:
                self._handlers[msg_type].append(handler)

    def unregister(self, msg_type: str, handler):
        """
        Entfernt einen Handler für einen Message-Typ.
        """
        with self._lock:
            if handler in self._handlers[msg_type]:
                self._handlers[msg_type].remove(handler)

    # ------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------
    def route_message(self, msg_type: str, msg):
        """
        Wird von der QGCConnection aufgerufen.

        Ruft alle registrierten Handler für msg_type auf.
        """
        with self._lock:
            handlers = list(self._handlers.get(msg_type, []))

        for handler in handlers:
            try:
                handler(msg)
            except Exception:
                # Fehler in einem Handler dürfen das Routing nicht stoppen
                pass

    # ------------------------------------------------------------
    # Utility: Handler für mehrere Typen registrieren
    # ------------------------------------------------------------
    def register_multi(self, msg_types, handler):
        """
        Registriert denselben Handler für mehrere Message-Typen.
        """
        for t in msg_types:
            self.register(t, handler)

    def unregister_multi(self, msg_types, handler):
        """
        Entfernt denselben Handler aus mehreren Message-Typen.
        """
        for t in msg_types:
            self.unregister(t, handler)
