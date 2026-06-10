# === PFAD-B FULL FILE: QGCR/communication/microservices/param_microservice.py ===

import time
from pymavlink import mavutil


class ParamMicroService:
    """
    Nicht-blockierender Parameter-Sync für PX4.
    Kompatibel mit deiner FSM-Architektur:
    - start() setzt Initialzustand
    - tick() verarbeitet genau eine MAVLink-Nachricht
    - done=True wenn alle Parameter empfangen wurden
    - error=Exception bei Fehlern
    """

    def __init__(self, master, target_system, target_component):
        self.master = master
        self.tsys = target_system
        self.tcomp = target_component

        # Statusflags
        self.started = False
        self.done = False
        self.error = None

        # Parameter-Speicher
        self.params = {}
        self.expected_count = None

        # Timeout
        self.last_msg_time = None
        self.timeout_sec = 3.0

    # ------------------------------------------------------------
    # Start
    # ------------------------------------------------------------
    def start(self):
        """
        Startet den ParamSync nicht-blockierend.
        """
        self.started = True
        self.done = False
        self.error = None
        self.params = {}
        self.expected_count = None
        self.last_msg_time = time.time()

        # PX4 auffordern, alle Parameter zu senden
        try:
            self.master.mav.param_request_list_send(self.tsys, self.tcomp)
        except Exception as e:
            self.error = e

    # ------------------------------------------------------------
    # Tick
    # ------------------------------------------------------------
    def tick(self):
        """
        Verarbeitet genau EINE MAVLink-Nachricht.
        Wird typischerweise mit ~20 Hz aufgerufen.
        """

        if not self.started or self.done or self.error:
            return

        # Timeout?
        if time.time() - self.last_msg_time > self.timeout_sec:
            self.error = TimeoutError("ParamSync timeout")
            return

        # Eine Nachricht lesen (nicht blockierend!)
        msg = self.master.recv_match(type=["PARAM_VALUE"], blocking=False)

        if msg is None:
            return  # Kein Problem, einfach später wieder versuchen

        # Nachricht erhalten → Timeout zurücksetzen
        self.last_msg_time = time.time()

        # Parameter speichern
        try:
            self.params[msg.param_id] = msg.param_value
        except Exception:
            pass

        # Anzahl der erwarteten Parameter setzen
        if self.expected_count is None:
            self.expected_count = msg.param_count

        # Fertig?
        if msg.param_index + 1 == msg.param_count:
            self.done = True
            return
