# communication/event_router.py

from typing import Protocol
from pymavlink.dialects.v20 import common as mavlink


class FSMProtocol(Protocol):
    def on_message(self, msg) -> None: ...


class DispatcherProtocol(Protocol):
    @property
    def startup_sm(self) -> FSMProtocol: ...
    @property
    def ready_sm(self) -> FSMProtocol: ...
    @property
    def takeoff_sm(self) -> FSMProtocol: ...
    @property
    def mission_sm(self) -> FSMProtocol: ...

    def get_active_fsm(self) -> FSMProtocol: ...


class HeartbeatMonitorProtocol(Protocol):
    def handle_heartbeat(self, msg, source: str) -> None: ...


class EventRouter:
    """
    Verantwortlichkeiten:
    - Unterscheidet PX4-Heartbeat vs. QGC-Heartbeat
    - Leitet PARAM/HOME an StartupFSM
    - Leitet MISSION_* an MissionFSM
    - Leitet COMMAND_ACK an TakeoffFSM
    - Alles andere an die aktive FSM (Dispatcher)
    """

    def __init__(self, dispatcher: DispatcherProtocol, heartbeat_monitor: HeartbeatMonitorProtocol) -> None:
        self._dispatcher = dispatcher
        self._hb_monitor = heartbeat_monitor

    # -------------------------------------------------------------------------
    # Routing Entry Point
    # -------------------------------------------------------------------------
    def route(self, msg) -> None:
        msgid = msg.get_msgId()

        # ---------------------------------------------------------
        # 1. Heartbeat (PX4 + QGC)
        # ---------------------------------------------------------
        if msgid == mavlink.MAVLINK_MSG_ID_HEARTBEAT:
            self._handle_heartbeat(msg)
            return

        # ---------------------------------------------------------
        # 2. PARAM_VALUE → StartupFSM
        # ---------------------------------------------------------
        if msgid == mavlink.MAVLINK_MSG_ID_PARAM_VALUE:
            self._dispatcher.startup_sm.on_message(msg)
            return

        # ---------------------------------------------------------
        # 3. HOME_POSITION → StartupFSM
        # ---------------------------------------------------------
        if msgid == mavlink.MAVLINK_MSG_ID_HOME_POSITION:
            self._dispatcher.startup_sm.on_message(msg)
            return

        # ---------------------------------------------------------
        # 4. MISSION_* → MissionFSM
        # ---------------------------------------------------------
        if msgid in (
            mavlink.MAVLINK_MSG_ID_MISSION_COUNT,
            mavlink.MAVLINK_MSG_ID_MISSION_ITEM_INT,
            mavlink.MAVLINK_MSG_ID_MISSION_REQUEST,
            mavlink.MAVLINK_MSG_ID_MISSION_REQUEST_INT,
            mavlink.MAVLINK_MSG_ID_MISSION_ACK,
        ):
            self._dispatcher.mission_sm.on_message(msg)
            return

        # ---------------------------------------------------------
        # 5. COMMAND_ACK → TakeoffFSM
        # ---------------------------------------------------------
        if msgid == mavlink.MAVLINK_MSG_ID_COMMAND_ACK:
            self._dispatcher.takeoff_sm.on_message(msg)
            return

        # ---------------------------------------------------------
        # 6. Default → aktive FSM
        # ---------------------------------------------------------
        active_fsm = self._dispatcher.get_active_fsm()
        active_fsm.on_message(msg)

    # -------------------------------------------------------------------------
    # Heartbeat Handling
    # -------------------------------------------------------------------------
    def _handle_heartbeat(self, msg) -> None:
        hb_type = getattr(msg, "type", None)

        # PX4 Heartbeat
        if hb_type != mavlink.MAV_TYPE_GCS:
            # -------------------------
            # PX4 MODE MAPPING
            # -------------------------
            custom_mode = msg.custom_mode
            self.model.px4_mode = self.model.map_px4_mode(custom_mode)

            # -------------------------
            # PX4 ARMED FLAG
            # -------------------------
            self.model.px4_armed = (
                msg.base_mode & self.model.MAV_MODE_FLAG_SAFETY_ARMED
            ) != 0

            # -------------------------
            # HEARTBEAT COUNTER
            # -------------------------
            self.model.heartbeat_count += 1

            # -------------------------
            # Alive/Dead/Reboot Handling
            # -------------------------
            self._hb_monitor.handle_heartbeat(msg, source="px4")

        # GCS Heartbeat
        else:
            self._hb_monitor.handle_heartbeat(msg, source="gcs")

