from enum import Enum, auto


class EventType(Enum):
    """
    Typen von Events, die im MainStateMachineController verarbeitet werden.
    GUI-Events und State-Events sind strikt getrennt.
    """

    # GUI → STATE
    GUI_TAKEOFF_BUTTON = auto()
    GUI_LAND_BUTTON = auto()
    GUI_MISSION_UPLOAD = auto()

    # PX4 / System → STATE
    PX4_HEARTBEAT = auto()

    # Parameter-Sync (für StartupParamSyncFSM)
    PX4_PARAMS_RECEIVED = auto()
    PX4_PARAMS_SYNCED = auto()

    # Bestehendes Event bleibt erhalten
    PX4_PARAM_SYNC_DONE = auto()

    # Home-Position
    PX4_HOME_SET = auto()

    # Mission
    PX4_MISSION_ACK = auto()

    # Interne HFSM-Events
    INTERNAL_TRANSITION = auto()


class Event:
    """
    Ein Event ist ein unveränderliches Datenobjekt, das vom EventRouter
    oder vom GUI/MAVLink-Thread erzeugt wird.

    Es enthält:
    - type: EventType
    - payload: optionale Daten (dict oder primitive Werte)
    """

    __slots__ = ("type", "payload")

    def __init__(self, type: EventType, payload=None):
        self.type = type
        self.payload = payload

    def __repr__(self):
        return f"Event(type={self.type}, payload={self.payload})"


# ----------------------------------------------------------------------
# Factory-Funktionen für GUI-Events
# ----------------------------------------------------------------------

def gui_takeoff_button():
    return Event(EventType.GUI_TAKEOFF_BUTTON)


def gui_land_button():
    return Event(EventType.GUI_LAND_BUTTON)


def gui_mission_upload(mission_data):
    return Event(EventType.GUI_MISSION_UPLOAD, payload=mission_data)


# ----------------------------------------------------------------------
# Factory-Funktionen für PX4/State-Events
# ----------------------------------------------------------------------

def px4_heartbeat():
    return Event(EventType.PX4_HEARTBEAT)


def px4_params_received():
    return Event(EventType.PX4_PARAMS_RECEIVED)


def px4_params_synced():
    return Event(EventType.PX4_PARAMS_SYNCED)


def px4_param_sync_done():
    return Event(EventType.PX4_PARAM_SYNC_DONE)


def px4_home_set(home_position):
    return Event(EventType.PX4_HOME_SET, payload=home_position)


def px4_mission_ack(result):
    return Event(EventType.PX4_MISSION_ACK, payload=result)
