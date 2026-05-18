# === PFAD-B FULL FILE: QGCR/model/model.py ===

import time


class Model:
    """
    Zentrales Datenmodell:
    - Speichert Telemetrie
    - Speichert HFSM-State
    - Verbindungsstatus (px4_connected)
    - Heartbeat-Handling mit Timeout + Debounce
    """

    HEARTBEAT_TIMEOUT = 8.0          # vorher 3.0
    HEARTBEAT_DEBOUNCE_COUNT = 2     # LOST erst nach 2 Timeouts

    def __init__(self, queue_registry):
        self.queue_registry = queue_registry

        # Verbindung / Heartbeat
        self.px4_connected = False
        self.px4_last_heartbeat = 0.0
        self.px4_heartbeat_count = 0
        self._lost_counter = 0

        # Telemetrie
        self.vehicle_lat = None
        self.vehicle_lon = None
        self.vehicle_alt = 0.0

        self.home_lat = None
        self.home_lon = None
        self.home_alt = None

        # HFSM-State
        self.hfsm_main = "-"
        self.hfsm_sub = "-"

    # ------------------------------------------------------------
    # Heartbeat
    # ------------------------------------------------------------
    def on_heartbeat(self, msg):
        """
        Wird von Connection aufgerufen, wenn ein PX4-Heartbeat empfangen wurde.
        """
        now = time.time()
        dt = now - self.px4_last_heartbeat

        # Debug-Ausgabe (kann später entfernt werden)
        print(f"HB dt={dt:.3f}s")

        self.px4_last_heartbeat = now
        self.px4_heartbeat_count += 1

        # Debounce: Verbindung ist stabil, sobald ein Heartbeat kommt
        self._lost_counter = 0
        self.px4_connected = True

    # ------------------------------------------------------------
    # Timeout + Debounce
    # ------------------------------------------------------------
    def check_timeout(self):
        """
        Wird vom HFSM-Thread zyklisch aufgerufen.
        Prüft, ob Heartbeats ausbleiben.
        """
        now = time.time()
        dt = now - self.px4_last_heartbeat

        if dt > self.HEARTBEAT_TIMEOUT:
            self._lost_counter += 1

            # LOST erst nach mehreren Timeouts
            if self._lost_counter >= self.HEARTBEAT_DEBOUNCE_COUNT:
                self.px4_connected = False
        else:
            # Heartbeat kam rechtzeitig → Verbindung stabil
            self._lost_counter = 0
            self.px4_connected = True

    # ------------------------------------------------------------
    # HFSM-State
    # ------------------------------------------------------------
    def update_hfsm_state(self, main, sub):
        self.hfsm_main = main
        self.hfsm_sub = sub

        try:
            self.queue_registry.gui.push(("state", {"main": main, "sub": sub}))
        except Exception:
            pass

    # ------------------------------------------------------------
    # Telemetrie
    # ------------------------------------------------------------
    def update_vehicle_position(self, lat, lon, alt):
        self.vehicle_lat = lat
        self.vehicle_lon = lon
        self.vehicle_alt = alt

        try:
            self.queue_registry.gui.push(("telemetry", {
                "mode": "-",
                "armed": False,
                "alt": alt,
                "px4_hb": self.px4_heartbeat_count,
                "px4_connected": self.px4_connected
            }))
        except Exception:
            pass

    def update_home_position(self, lat, lon, alt):
        self.home_lat = lat
        self.home_lon = lon
        self.home_alt = alt

        try:
            self.queue_registry.gui.push(("status", f"Home set: {lat:.5f}, {lon:.5f}, {alt:.1f} m"))
        except Exception:
            pass

    # ------------------------------------------------------------
    # Status / Text
    # ------------------------------------------------------------
    def update_status(self, text):
        try:
            self.queue_registry.gui.push(("status", text))
        except Exception:
            pass

    # ------------------------------------------------------------
    # Command ACK
    # ------------------------------------------------------------
    def on_command_ack(self, msg):
        try:
            self.queue_registry.gui.push(("status", f"ACK: {msg.command} → {msg.result}"))
        except Exception:
            pass
