#!/usr/bin/env python3
"""
mission_microservice.py
-----------------------

MAVLink Mission MicroService:
- Upload
- Download

Liest NICHT selbst von der MAVLink-Verbindung (das macht ausschließlich der
RX-Thread der Connection). Mission-Nachrichten kommen über den Dispatcher
(on_message) in eine thread-sichere Queue, upload()/download() warten darauf.

upload()/download() blockieren bis zum Ende bzw. Timeout und dürfen daher
NICHT aus dem RX-Thread (Dispatcher-Callback) aufgerufen werden.
Abbruch: optionales threading.Event `cancel` je Transfer – wird es gesetzt,
endet der Transfer, PX4 erhält MISSION_ACK (OPERATION_CANCELLED) und
last_error == MissionMicroService.CANCELLED.
"""

import queue
import time

from pymavlink import mavutil


class MissionMicroService:

    CANCELLED = "Abgebrochen"
    POLL_INTERVAL = 0.1     # Abbruch-Prüfung beim Warten [s]

    MISSION_MSG_TYPES = {
        "MISSION_COUNT",
        "MISSION_ITEM_INT",
        "MISSION_REQUEST",
        "MISSION_REQUEST_INT",
        "MISSION_ACK",
    }

    def __init__(self, master, target_system, target_component, model=None, timeout=3.0):
        """
        master:           pymavlink MAVLink connection (nur zum Senden)
        target_system:    Ziel-System-ID (PX4)
        target_component: Ziel-Komponenten-ID
        model:            optional, für GUI-Events (queue_registry)
        timeout:          max. Wartezeit pro erwarteter Nachricht [s]
        """
        self.master = master
        self.target_system = target_system
        self.target_component = target_component
        self.model = model
        self.timeout = timeout

        self._rx = queue.Queue()

        # Fehler des letzten upload()/download() (None = OK)
        self.last_error = None

    # ------------------------------------------------------------
    # Dispatcher Hook (läuft im RX-Thread der Connection)
    # ------------------------------------------------------------
    def on_message(self, msg_type, msg):
        if msg_type in self.MISSION_MSG_TYPES:
            self._rx.put(msg)

    # ------------------------------------------------------------
    # Empfangs-Helfer
    # ------------------------------------------------------------
    def _clear_rx(self):
        """Veraltete Nachrichten aus früheren Transfers verwerfen."""
        while True:
            try:
                self._rx.get_nowait()
            except queue.Empty:
                return

    def _wait_for(self, types, timeout=None, cancel=None):
        """
        Wartet auf die nächste Nachricht eines der Typen.
        Andere Mission-Nachrichten werden verworfen. None bei Timeout oder Abbruch.
        """
        deadline = time.monotonic() + (self.timeout if timeout is None else timeout)

        while True:
            if cancel is not None and cancel.is_set():
                return None

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None

            try:
                msg = self._rx.get(timeout=min(remaining, self.POLL_INTERVAL))
            except queue.Empty:
                continue

            if msg.get_type() in types:
                return msg

    def _cancelled(self, cancel):
        """Abbruch gesetzt? Dann PX4 informieren und last_error setzen."""
        if cancel is None or not cancel.is_set():
            return False

        print("[MS] Transfer abgebrochen → MISSION_ACK (OPERATION_CANCELLED)")
        self.master.mav.mission_ack_send(
            self.target_system,
            self.target_component,
            mavutil.mavlink.MAV_MISSION_OPERATION_CANCELLED
        )
        self.last_error = self.CANCELLED
        return True

    # ------------------------------------------------------------
    # Mission Upload
    # ------------------------------------------------------------
    def upload(self, mission_items, cancel=None):
        """
        Lädt die Mission hoch. True, wenn PX4 sie akzeptiert hat.
        """
        self._clear_rx()
        self.last_error = None

        print(f"[MS] Sende MISSION_COUNT = {len(mission_items)}")
        self.master.mav.mission_count_send(
            self.target_system,
            self.target_component,
            len(mission_items)
        )

        while True:
            print("[MS] Warte auf PX4 MISSION_REQUEST / MISSION_ACK…")
            msg = self._wait_for({"MISSION_REQUEST", "MISSION_REQUEST_INT", "MISSION_ACK"}, cancel=cancel)

            if self._cancelled(cancel):
                return False

            if msg is None:
                print("[MS] Timeout: Keine MISSION_REQUEST / MISSION_ACK Antwort von PX4.")
                self.last_error = "Timeout (MISSION_REQUEST / MISSION_ACK)"
                return False

            print(f"[MS] Empfangen: {msg}")

            mtype = msg.get_type()

            # PX4 fordert Item an
            if mtype in ["MISSION_REQUEST", "MISSION_REQUEST_INT"]:
                seq = msg.seq
                print(f"[MS] PX4 fordert Item {seq} an")

                if not 0 <= seq < len(mission_items):
                    print(f"[MS] Ungültige Item-Anforderung seq={seq}")
                    self.last_error = f"Ungültige Item-Anforderung seq={seq}"
                    return False

                item = mission_items[seq]
                print(f"[MS] → Sende MISSION_ITEM_INT seq={item.seq}")

                self.master.mav.mission_item_int_send(
                    self.target_system,
                    self.target_component,
                    item.seq,
                    item.frame,
                    item.command,
                    item.current,
                    item.autocontinue,
                    float(item.param1),
                    float(item.param2),
                    float(item.param3),
                    float(item.param4),
                    int(item.x),
                    int(item.y),
                    float(item.z),
                )

            # PX4 bestätigt Mission
            elif mtype == "MISSION_ACK":
                print(f"[MS] PX4 Mission ACK: {msg.type}")
                print("[MS] Mission Upload COMPLETE")
                if msg.type != mavutil.mavlink.MAV_MISSION_ACCEPTED:
                    self.last_error = f"PX4 lehnt Mission ab (MAV_MISSION_RESULT {msg.type})"
                    return False
                return True

    # ------------------------------------------------------------
    # Mission Download (für StartupHFSM)
    # ------------------------------------------------------------
    def download(self, cancel=None):
        print("[MS] Starte Mission Download…")

        self._clear_rx()
        self.last_error = None

        self.master.mav.mission_request_list_send(
            self.target_system,
            self.target_component
        )

        msg = self._wait_for({"MISSION_COUNT"}, cancel=cancel)
        if self._cancelled(cancel):
            return []
        if msg is None:
            print("[MS] Timeout: Keine MISSION_COUNT Antwort von PX4.")
            self.last_error = "Timeout (MISSION_COUNT)"
            return []

        count = msg.count
        print(f"[MS] PX4 meldet {count} Mission Items")

        mission = []

        for seq in range(count):
            print(f"[MS] → Fordere Item {seq} an")
            self.master.mav.mission_request_int_send(
                self.target_system,
                self.target_component,
                seq
            )

            msg = self._wait_for_item(seq, cancel)
            if self._cancelled(cancel):
                break
            if msg is None:
                print(f"[MS] Timeout: Kein MISSION_ITEM_INT für seq={seq}")
                self.last_error = f"Timeout (MISSION_ITEM_INT seq={seq})"
                break

            print(f"[MS] Empfangen: {msg}")
            mission.append(msg)

        # Download gegenüber PX4 abschließen (wie QGC)
        if count > 0 and len(mission) == count:
            self.master.mav.mission_ack_send(
                self.target_system,
                self.target_component,
                mavutil.mavlink.MAV_MISSION_ACCEPTED
            )

        print("[MS] Mission Download COMPLETE")

        # GUI über komplette Mission informieren (falls model vorhanden)
        if self.model is not None:
            try:
                self.model.queue_registry.require("gui").push(
                    ("mission_update", mission)
                )
            except Exception:
                pass

        return mission

    def _wait_for_item(self, seq, cancel=None):
        """MISSION_ITEM_INT mit passender seq; Duplikate/alte Items überspringen."""
        deadline = time.monotonic() + self.timeout

        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None

            msg = self._wait_for({"MISSION_ITEM_INT"}, timeout=remaining, cancel=cancel)
            if msg is None or msg.seq == seq:
                return msg
