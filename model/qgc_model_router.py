#!/usr/bin/env python3
# === PFAD-B FULL FILE: QGCR/model/qgc_model_router.py ===
"""
qgc_model_router.py
-------------------

Der QGCModelRouter verbindet das Model mit dem QGCDispatcher:

- Registriert Handler für relevante MAVLink-Message-Typen
- Übersetzt MAVLink-Nachrichten in Model-Methoden
- Keine Kopplung an Connection, GUI oder FSM
"""

class QGCModelRouter:
    """
    Vermittelt zwischen MAVLink (über QGCDispatcher) und dem Model.

    Der Router kennt:
    - das Model
    - den Dispatcher

    Der Router kennt NICHT:
    - Connection
    - GUI
    - FSM
    """

    def __init__(self, model, dispatcher):
        self.model = model
        self.dispatcher = dispatcher

    # ------------------------------------------------------------
    # Registrierung aller relevanten MAVLink-Handler
    # ------------------------------------------------------------
    def register_all(self):
        """
        Registriert alle Handler beim Dispatcher.
        """
        self.dispatcher.register("HEARTBEAT", self._on_heartbeat)
        self.dispatcher.register("SYS_STATUS", self._on_sys_status)
        self.dispatcher.register("GPS_RAW_INT", self._on_gps_raw)
        self.dispatcher.register("GLOBAL_POSITION_INT", self._on_global_position)
        self.dispatcher.register("MISSION_CURRENT", self._on_mission_current)
        self.dispatcher.register("MISSION_ITEM_REACHED", self._on_mission_reached)

        # Mission-Upload/Download wird von MissionFSM behandelt
        # → nicht hier registrieren

    # ------------------------------------------------------------
    # HEARTBEAT
    # ------------------------------------------------------------
    def _on_heartbeat(self, msg):
        """
        Aktualisiert PX4-Status im Model.
        """
        self.model.update_heartbeat(
            base_mode=msg.base_mode,
            custom_mode=msg.custom_mode,
            system_status=msg.system_status,
            sysid=msg.get_srcSystem(),
            compid=msg.get_srcComponent(),
        )

    # ------------------------------------------------------------
    # SYS_STATUS (Batterie, Load, Sensoren)
    # ------------------------------------------------------------
    def _on_sys_status(self, msg):
        self.model.update_sys_status(
            battery_remaining=msg.battery_remaining,
            voltage_battery=msg.voltage_battery,
            current_battery=msg.current_battery,
            load=msg.load,
        )

    # ------------------------------------------------------------
    # GPS_RAW_INT
    # ------------------------------------------------------------
    def _on_gps_raw(self, msg):
        self.model.update_gps(
            fix_type=msg.fix_type,
            lat=msg.lat,
            lon=msg.lon,
            alt=msg.alt,
            eph=msg.eph,
            epv=msg.epv,
            satellites_visible=msg.satellites_visible,
        )

    # ------------------------------------------------------------
    # GLOBAL_POSITION_INT
    # ------------------------------------------------------------
    def _on_global_position(self, msg):
        self.model.update_global_position(
            lat=msg.lat,
            lon=msg.lon,
            alt=msg.alt,
            relative_alt=msg.relative_alt,
            vx=msg.vx,
            vy=msg.vy,
            vz=msg.vz,
            hdg=msg.hdg,
        )

    # ------------------------------------------------------------
    # MISSION_CURRENT
    # ------------------------------------------------------------
    def _on_mission_current(self, msg):
        self.model.update_mission_current(msg.seq)

    # ------------------------------------------------------------
    # MISSION_ITEM_REACHED
    # ------------------------------------------------------------
    def _on_mission_reached(self, msg):
        self.model.update_mission_reached(msg.seq)
