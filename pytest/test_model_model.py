#!/usr/bin/env python3
# === PFAD-B FULL FILE: QGCR/pytest/test_model_model.py ===

import time
import pytest

from QGCR.model.model import Model, MissionData
from QGCR.core.queue_registry import QueueRegistry


# ------------------------------------------------------------
# Helper: GUI-Events aus Queue holen
# ------------------------------------------------------------
def pop_gui_events(reg):
    return reg.require("gui").pop_all()


# ------------------------------------------------------------
# Fake MAVLink Heartbeat Message
# ------------------------------------------------------------
class FakeHeartbeat:
    def __init__(self, base_mode=0, custom_mode=0):
        self.base_mode = base_mode
        self.custom_mode = custom_mode


# ------------------------------------------------------------
# Fake MAVLink CommandAck Message
# ------------------------------------------------------------
class FakeAck:
    def __init__(self, command, result):
        self.command = command
        self.result = result


# ------------------------------------------------------------
# Konstruktion
# ------------------------------------------------------------
def test_model_construction():
    reg = QueueRegistry()
    m = Model(reg)

    assert isinstance(m.mission, MissionData)
    assert m.px4_connected is False
    assert m.vehicle_alt == 0.0
    assert m.px4_mode == "-"
    assert m.px4_armed is False
    assert m.hfsm_main == "-"
    assert m.hfsm_sub == "-"


# ------------------------------------------------------------
# HEARTBEAT
# ------------------------------------------------------------
def test_on_heartbeat_updates_state_and_gui():
    reg = QueueRegistry()
    m = Model(reg)

    # custom_mode: main_mode = 4 → AUTO
    hb = FakeHeartbeat(
        base_mode=128,          # armed
        custom_mode=(4 << 24)   # AUTO
    )

    m.on_heartbeat(hb)

    assert m.px4_mode == "AUTO"
    assert m.px4_armed is True
    assert m.px4_connected is True
    assert m.px4_heartbeat_count == 1

    events = pop_gui_events(reg)
    assert len(events) == 1
    tag, payload = events[0]
    assert tag == "telemetry"
    assert payload["mode"] == "AUTO"
    assert payload["armed"] is True
    assert payload["px4_connected"] is True


# ------------------------------------------------------------
# TIMEOUT
# ------------------------------------------------------------
def test_timeout_disconnects_after_threshold(monkeypatch):
    reg = QueueRegistry()
    m = Model(reg)

    # Simuliere: letzter Heartbeat ist lange her
    m.px4_last_heartbeat = time.time() - (m.HEARTBEAT_TIMEOUT + 1)

    # monkeypatch time.time() für deterministisches Verhalten
    monkeypatch.setattr(time, "time", lambda: m.px4_last_heartbeat + m.HEARTBEAT_TIMEOUT + 2)

    m.check_timeout()

    assert m.px4_connected is False

    events = pop_gui_events(reg)
    assert len(events) == 1
    tag, payload = events[0]
    assert tag == "telemetry"
    assert payload["px4_connected"] is False


# ------------------------------------------------------------
# POSITION
# ------------------------------------------------------------
def test_update_vehicle_position_pushes_gui_event():
    reg = QueueRegistry()
    m = Model(reg)

    m.update_vehicle_position(47.0, 8.0, 500.0)

    assert m.vehicle_lat == 47.0
    assert m.vehicle_lon == 8.0
    assert m.vehicle_alt == 500.0

    events = pop_gui_events(reg)
    assert len(events) == 1
    tag, payload = events[0]
    assert tag == "telemetry"
    assert payload["alt"] == 500.0


def test_update_home_position_pushes_status():
    reg = QueueRegistry()
    m = Model(reg)

    m.update_home_position(47.0, 8.0, 450.0)

    assert m.home_lat == 47.0
    assert m.home_lon == 8.0
    assert m.home_alt == 450.0

    events = pop_gui_events(reg)
    assert len(events) == 1
    tag, text = events[0]
    assert tag == "status"
    assert "Home set" in text


# ------------------------------------------------------------
# STATUS
# ------------------------------------------------------------
def test_update_status_pushes_gui_event():
    reg = QueueRegistry()
    m = Model(reg)

    m.update_status("Hello World")

    events = pop_gui_events(reg)
    assert len(events) == 1
    tag, text = events[0]
    assert tag == "status"
    assert text == "Hello World"


# ------------------------------------------------------------
# COMMAND ACK
# ------------------------------------------------------------
def test_on_command_ack_pushes_status():
    reg = QueueRegistry()
    m = Model(reg)

    ack = FakeAck(command=22, result=0)
    m.on_command_ack(ack)

    events = pop_gui_events(reg)
    assert len(events) == 1
    tag, text = events[0]
    assert tag == "status"
    assert "ACK" in text


# ------------------------------------------------------------
# MISSION MANAGEMENT
# ------------------------------------------------------------
def test_clear_mission():
    reg = QueueRegistry()
    m = Model(reg)

    m.mission.items = [1, 2, 3]
    m.mission.count = 3
    m.mission.ready = True

    m.clear_mission()

    assert m.mission.items == []
    assert m.mission.count == 0
    assert m.mission.ready is False


def test_add_mission_item():
    reg = QueueRegistry()
    m = Model(reg)

    m.add_mission_item(0, 16, 47.0, 8.0, 500.0)

    assert len(m.mission.items) == 1
    item = m.mission.items[0]

    assert item["seq"] == 0
    assert item["command"] == 16
    assert item["x"] == 47.0
    assert item["y"] == 8.0
    assert item["z"] == 500.0

    assert m.mission.count == 1
