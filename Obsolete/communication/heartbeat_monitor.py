# heartbeat_monitor.py

import time
from pymavlink.dialects.v20 import common as mavlink


class HeartbeatMonitor:
    """
    Überwacht PX4- und GCS-Heartbeats.
    Erkennt:
    - PX4_LOST / PX4_RECOVERED
    - PX4_REBOOTED (base_mode geändert)
    - GCS_LOST / GCS_RECOVERED
    """

    def __init__(self, timeout_s: float = 2.0):
        self.timeout_s = timeout_s

        # PX4
        self.last_px4_hb = None
        self._last_px4_ts = None
        self._px4_alive = False
        self._px4_last_base_mode = None
        self._px4_reboot_pending = False
        self._px4_recovered_pending = False

        # GCS
        self.last_gcs_hb = None
        self._last_gcs_ts = None
        self._gcs_alive = False



    # -------------------------------------------------------------------------
    # Heartbeat Empfang
    # -------------------------------------------------------------------------
    def handle_heartbeat(self, msg, source: str):
        now = time.time()

        if source == "px4":
            was_dead = not self._px4_alive

            self.last_px4_hb = msg
            self._last_px4_ts = now
            self._px4_alive = True

            base_mode = getattr(msg, "base_mode", None)

            # Reboot-Erkennung
            if (
                self._px4_last_base_mode is not None
                and base_mode != self._px4_last_base_mode
            ):
                self._px4_reboot_pending = True

            self._px4_last_base_mode = base_mode

            # RECOVERED
            if was_dead:
                self._px4_recovered_pending = True

        elif source == "gcs":
            self.last_gcs_hb = msg
            self._last_gcs_ts = now
            self._gcs_alive = True

    # -------------------------------------------------------------------------
    # Periodisches Update → Events erzeugen
    # -------------------------------------------------------------------------
    def update(self):
        now = time.time()
        events = []

        # ---------------------------------------------------------
        # PX4 Timeout
        # ---------------------------------------------------------
        if self._px4_alive and self._last_px4_ts is not None:
            if now - self._last_px4_ts > self.timeout_s:
                self._px4_alive = False
                events.append("PX4_LOST")

        # PX4 recovered
        if self._px4_alive and self.last_px4_hb is not None:
            if getattr(self, "_px4_was_dead", False):
                events.append("PX4_RECOVERED")
            self._px4_was_dead = False
        else:
            self._px4_was_dead = True

        # PX4 reboot
        if self._px4_reboot_pending:
            events.append("PX4_REBOOTED")
            self._px4_reboot_pending = False

        # PX4 recovered
        if self._px4_recovered_pending:
            events.append("PX4_RECOVERED")
            self._px4_recovered_pending = False

        # ---------------------------------------------------------
        # GCS Timeout
        # ---------------------------------------------------------
        if self._gcs_alive and self._last_gcs_ts is not None:
            if now - self._last_gcs_ts > self.timeout_s:
                self._gcs_alive = False
                events.append("GCS_LOST")

        # GCS recovered
        if self._gcs_alive and self.last_gcs_hb is not None:
            if getattr(self, "_gcs_was_dead", False):
                events.append("GCS_RECOVERED")
            self._gcs_was_dead = False
        else:
            self._gcs_was_dead = True

        return events
