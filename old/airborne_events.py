# === PFAD-B FULL FILE: airborne_events.py ===

from enum import Enum, auto


class AirborneEventType(Enum):
    """
    Klassifikation aller Events, die im AirborneHFSM relevant sind.
    """
    MODE_CHANGE = auto()
    MISSION = auto()
    FAILSAFE = auto()
    SYSTEM = auto()
    INTERNAL = auto()


class AirborneEvent:
    """
    Standardisiertes Event-Objekt für AirborneHFSM.
    """
    def __init__(self, event_type: AirborneEventType, name: str, payload=None):
        self.type = event_type
        self.name = name
        self.payload = payload


# ------------------------------------------------------------
# KONKRETE EVENTS
# ------------------------------------------------------------

class AirborneEvents:
    """
    Sammlung aller Airborne-spezifischen Events als Konstanten.
    """

    # --------------------------------------------------------
    # MODE CHANGE EVENTS
    # --------------------------------------------------------
    MODE_MANUAL = AirborneEvent(AirborneEventType.MODE_CHANGE, "MODE_MANUAL")
    MODE_ALTCTL = AirborneEvent(AirborneEventType.MODE_CHANGE, "MODE_ALTCTL")
    MODE_POSCTL = AirborneEvent(AirborneEventType.MODE_CHANGE, "MODE_POSCTL")
    MODE_OFFBOARD = AirborneEvent(AirborneEventType.MODE_CHANGE, "MODE_OFFBOARD")
    MODE_AUTO_MISSION = AirborneEvent(AirborneEventType.MODE_CHANGE, "MODE_AUTO_MISSION")
    MODE_AUTO_LOITER = AirborneEvent(AirborneEventType.MODE_CHANGE, "MODE_AUTO_LOITER")
    MODE_AUTO_RTL = AirborneEvent(AirborneEventType.MODE_CHANGE, "MODE_AUTO_RTL")
    MODE_AUTO_LAND = AirborneEvent(AirborneEventType.MODE_CHANGE, "MODE_AUTO_LAND")

    # --------------------------------------------------------
    # MISSION EVENTS
    # --------------------------------------------------------
    MISSION_STARTED = AirborneEvent(AirborneEventType.MISSION, "MISSION_STARTED")
    MISSION_FINISHED = AirborneEvent(AirborneEventType.MISSION, "MISSION_FINISHED")
    MISSION_ABORTED = AirborneEvent(AirborneEventType.MISSION, "MISSION_ABORTED")
    MISSION_WAYPOINT_REACHED = AirborneEvent(AirborneEventType.MISSION, "MISSION_WAYPOINT_REACHED")

    # --------------------------------------------------------
    # FAILSAFE EVENTS
    # --------------------------------------------------------
    FAILSAFE_GPS_LOST = AirborneEvent(AirborneEventType.FAILSAFE, "FAILSAFE_GPS_LOST")
    FAILSAFE_RC_LOST = AirborneEvent(AirborneEventType.FAILSAFE, "FAILSAFE_RC_LOST")
    FAILSAFE_BATTERY_LOW = AirborneEvent(AirborneEventType.FAILSAFE, "FAILSAFE_BATTERY_LOW")
    FAILSAFE_GEOFENCE = AirborneEvent(AirborneEventType.FAILSAFE, "FAILSAFE_GEOFENCE")

    # --------------------------------------------------------
    # SYSTEM EVENTS
    # --------------------------------------------------------
    TAKEOFF_COMPLETE = AirborneEvent(AirborneEventType.SYSTEM, "TAKEOFF_COMPLETE")
    LANDING_DETECTED = AirborneEvent(AirborneEventType.SYSTEM, "LANDING_DETECTED")
    TOUCHDOWN = AirborneEvent(AirborneEventType.SYSTEM, "TOUCHDOWN")
    ARMED = AirborneEvent(AirborneEventType.SYSTEM, "ARMED")
    DISARMED = AirborneEvent(AirborneEventType.SYSTEM, "DISARMED")

    # --------------------------------------------------------
    # INTERNAL EVENTS
    # --------------------------------------------------------
    INTERNAL_TICK = AirborneEvent(AirborneEventType.INTERNAL, "INTERNAL_TICK")
