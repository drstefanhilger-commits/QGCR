# === PFAD-B FULL FILE: test_communication_harness.py ===

import time
import types

from QGCR.communication.dispatcher import Dispatcher
from QGCR.model.model import Model
from QGCR.test.unittest.dummy_model import DummyModel


# ------------------------------------------------------------
# Fake MAVLink Message Generator
# ------------------------------------------------------------
def make_msg(**fields):
    """
    Erzeugt ein einfaches Objekt mit Attributen wie ein MAVLink-Message.
    Beispiel:
        msg = make_msg(type="HEARTBEAT", custom_mode=4, base_mode=128)
    """
    return types.SimpleNamespace(**fields)


# ------------------------------------------------------------
# Fake FSM für COMMAND_ACK-Tests
# ------------------------------------------------------------
class FakeFSM:
    def __init__(self):
        self.received = []

    def on_message(self, msg_type, msg):
        self.received.append((msg_type, msg))


# ------------------------------------------------------------
# Harness-Test für Dispatcher + Model
# ------------------------------------------------------------
def test_dispatcher_and_model():
    model = Model()
    dispatcher = Dispatcher(model)

    # Fake FSM subscriben
    fsm = FakeFSM()
    dispatcher.subscribe(fsm, "COMMAND_ACK")

    # --------------------------------------------------------
    # HEARTBEAT
    # --------------------------------------------------------
    hb = make_msg(
        type="HEARTBEAT",
        custom_mode=4,
        base_mode=128  # armed bit
    )
    dispatcher.route_message("HEARTBEAT", hb)

    assert model.px4_connected is True
    assert model.px4_heartbeat_count == 1
    assert model.px4_mode == 4
    assert model.px4_armed is True

    # --------------------------------------------------------
    # HOME_POSITION
    # --------------------------------------------------------
    home = make_msg(
        type="HOME_POSITION",
        latitude=473000000,   # 47.3°
        longitude=85000000,   # 8.5°
        altitude=55000        # 55m
    )
    dispatcher.route_message("HOME_POSITION", home)

    assert model.home_lat == 47.3
    assert model.home_lon == 8.5
    assert model.home_alt == 55.0

    # --------------------------------------------------------
    # GLOBAL_POSITION_INT
    # --------------------------------------------------------
    pos = make_msg(
        type="GLOBAL_POSITION_INT",
        lat=473000000,
        lon=85000000,
        alt=55000
    )
    dispatcher.route_message("GLOBAL_POSITION_INT", pos)

    assert model.vehicle_lat == 47.3
    assert model.vehicle_lon == 8.5
    assert model.vehicle_alt == 55.0

    # --------------------------------------------------------
    # STATUSTEXT
    # --------------------------------------------------------
    st = make_msg(
        type="STATUSTEXT",
        severity=4,
        text="PX4 OK"
    )
    dispatcher.route_message("STATUSTEXT", st)

    assert model.log_messages[-1] == (4, "PX4 OK")

    # --------------------------------------------------------
    # COMMAND_ACK → FSM
    # --------------------------------------------------------
    ack = make_msg(
        type="COMMAND_ACK",
        command=22,
        result=0
    )
    dispatcher.route_message("COMMAND_ACK", ack)

    assert len(fsm.received) == 1
    assert fsm.received[0][0] == "COMMAND_ACK"

    # --------------------------------------------------------
    # Unhandled Message
    # --------------------------------------------------------
    dummy = make_msg(type="ATTITUDE", roll=0.1, pitch=0.2, yaw=0.3)
    dispatcher.route_message("ATTITUDE", dummy)

    assert dispatcher.unhandled_stats["ATTITUDE"] == 1


# ------------------------------------------------------------
# Harness-Test für DummyModel
# ------------------------------------------------------------
def test_dummy_model():
    dummy = DummyModel()

    # HEARTBEAT
    hb = make_msg(type="HEARTBEAT")
    dummy.on_heartbeat(hb)
    assert dummy.px4_connected is True
    assert dummy.px4_heartbeat_count == 1

    # HOME_POSITION
    dummy.update_home_position(47.3, 8.5, 55.0)
    assert dummy.home_lat == 47.3
    assert dummy.home_lon == 8.5
    assert dummy.home_alt == 55.0

    # GLOBAL_POSITION_INT
    dummy.update_vehicle_position(47.3, 8.5, 55.0)
    assert dummy.vehicle_lat == 47.3
    assert dummy.vehicle_lon == 8.5
    assert dummy.vehicle_alt == 55.0

    # COMMAND_ACK
    ack = make_msg(type="COMMAND_ACK", command=22, result=0)
    dummy.on_command_ack(ack)
