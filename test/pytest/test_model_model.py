#!/usr/bin/env python3
# === PFAD-B FULL FILE: QGCR/pytest/test_model_model.py ===

import math
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

    def get_srcSystem(self):
        return 1

    def get_srcComponent(self):
        return 1


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

    # custom_mode: Hauptmodus Bits 16-23 (4 = AUTO), Untermodus Bits 24-31 (3 = LOITER)
    hb = FakeHeartbeat(
        base_mode=128,                    # armed
        custom_mode=(4 << 16) | (3 << 24) # AUTO.LOITER
    )

    m.on_heartbeat(hb)

    assert m.px4_mode == "AUTO.LOITER"
    assert m.px4_armed is True
    assert m.px4_connected is True
    assert m.px4_heartbeat_count == 1

    events = pop_gui_events(reg)
    assert len(events) == 1
    tag, payload = events[0]
    assert tag == "telemetry"
    assert payload["mode"] == "AUTO.LOITER"
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


# ------------------------------------------------------------
# GUI-Queue bleibt begrenzt (niemand konsumiert sie)
# ------------------------------------------------------------
def test_gui_queue_stays_bounded_under_check_timeout():
    from QGCR.core.queues import GUIEventQueue

    reg = QueueRegistry()
    m = Model(reg)

    for _ in range(GUIEventQueue.MAXLEN * 3):
        m.check_timeout()

    events = pop_gui_events(reg)
    assert len(events) == GUIEventQueue.MAXLEN
    assert all(tag == "telemetry" for tag, _ in events)


# ------------------------------------------------------------
# PX4-Modus aus custom_mode (Werte aus PX4 v1.17 SITL)
# ------------------------------------------------------------
@pytest.mark.parametrize("main, sub, expected", [
    (1, 0, "MANUAL"),
    (3, 0, "POSCTL"),
    (4, 0, "AUTO"),
    (4, 2, "AUTO.TAKEOFF"),
    (4, 3, "AUTO.LOITER"),
    (4, 4, "AUTO.MISSION"),
    (4, 5, "AUTO.RTL"),
    (4, 6, "AUTO.LAND"),
    (4, 42, "AUTO.SUB_42"),
    (99, 0, "MODE_99"),
])
def test_decode_px4_mode(main, sub, expected):
    assert Model.decode_px4_mode((main << 16) | (sub << 24)) == expected


# ------------------------------------------------------------
# Missions-Track (2D-Plot)
# ------------------------------------------------------------
def test_track_only_while_mission_running():
    m = Model(QueueRegistry())
    m.update_vehicle_position(47.0, 8.0, 10.0)
    assert m.mission_track == []

    m.begin_mission()
    m.update_vehicle_position(47.0, 8.0, 10.0)
    m.update_vehicle_position(47.0001, 8.0, 10.0)      # ~11 m nördlich
    assert m.mission_track == [(47.0, 8.0), (47.0001, 8.0)]


def test_track_min_distance_filter():
    m = Model(QueueRegistry())
    m.begin_mission()
    m.update_vehicle_position(47.0, 8.0, 10.0)
    m.update_vehicle_position(47.000001, 8.0, 10.0)    # ~0,1 m → verworfen
    assert len(m.mission_track) == 1


def test_begin_mission_clears_track():
    m = Model(QueueRegistry())
    m.begin_mission()
    m.update_vehicle_position(47.0, 8.0, 10.0)
    m.begin_mission()
    assert m.mission_track == [] and m.mission_running


def test_track_is_capped():
    m = Model(QueueRegistry())
    m.TRACK_MAX_POINTS = 3
    m.begin_mission()
    for i in range(10):
        m.update_vehicle_position(47.0 + i * 0.001, 8.0, 10.0)
    assert len(m.mission_track) == 3


def test_landing_point():
    m = Model(QueueRegistry())
    assert m.landing_point() is None
    m.add_mission_item(0, 22, 47.0, 8.0, 20.0)
    m.add_mission_item(1, 16, 47.1, 8.1, 20.0)
    m.add_mission_item(2, 21, 47.2, 8.2, 0.0)
    assert m.landing_point() == (47.2, 8.2)

    m.clear_mission()
    m.add_mission_item(0, 85, 47.3, 8.3, 0.0)          # NAV_VTOL_LAND
    assert m.landing_point() == (47.3, 8.3)


def test_begin_mission_keeps_start_point():
    m = Model(QueueRegistry())
    m.update_home_position(47.0, 8.0, 400.0)
    m.update_vehicle_position(47.001, 8.001, 0.0)
    m.begin_mission()
    assert m.mission_start_point == (47.001, 8.001)

    m.update_home_position(47.5, 8.5, 400.0)           # PX4 setzt Home nach der Landung neu
    assert m.mission_start_point == (47.001, 8.001)


def test_begin_mission_start_point_falls_back_to_home():
    m = Model(QueueRegistry())
    m.update_home_position(47.0, 8.0, 400.0)
    m.begin_mission()
    assert m.mission_start_point == (47.0, 8.0)


def test_mission_markers():
    m = Model(QueueRegistry())
    assert m.mission_markers() == (None, None)

    m.update_home_position(47.0, 8.0, 400.0)
    m.add_mission_item(0, 21, 47.2, 8.2, 0.0)
    assert m.mission_markers() == ((47.0, 8.0), None)      # Mission noch nicht "ready"

    m.mission.ready = True
    m.update_vehicle_position(47.1, 8.1, 0.0)
    m.begin_mission()
    assert m.mission_markers() == ((47.1, 8.1), (47.2, 8.2))


# ------------------------------------------------------------
# Höhenverlauf (Höhen-Plot)
# ------------------------------------------------------------
def test_alt_track_only_during_mission(monkeypatch):
    import QGCR.model.model as model_mod
    now = [1000.0]
    monkeypatch.setattr(model_mod.time, "time", lambda: now[0])

    m = Model(QueueRegistry())
    m.update_vehicle_position(47.0, 8.0, 5.0)
    assert m.mission_alt_track == []

    m.begin_mission()
    m.update_vehicle_position(47.0, 8.0, 0.0)
    now[0] += 0.2
    m.update_vehicle_position(47.0, 8.0, 1.0)          # < 0,5 s → verworfen
    now[0] += 0.5
    m.update_vehicle_position(47.0, 8.0, 3.0)
    assert [(pytest.approx(t), a) for t, a in m.mission_alt_track] == [(0.0, 0.0), (0.7, 3.0)]


def test_clear_track_clears_both():
    m = Model(QueueRegistry())
    m.begin_mission()
    m.update_vehicle_position(47.0, 8.0, 1.0)
    assert m.mission_track and m.mission_alt_track
    m.clear_track()
    assert m.mission_track == [] and m.mission_alt_track == []
    assert m.mission_running                         # Mission läuft weiter


# ------------------------------------------------------------
# Akku + FSL-Geometrie
# ------------------------------------------------------------
def test_update_battery():
    m = Model(QueueRegistry())
    assert m.battery_remaining is None
    m.update_battery(73)
    assert m.battery_remaining == 73
    m.update_battery(-1)                               # MAVLink: unbekannt
    assert m.battery_remaining is None


def test_intercept_geometry():
    from QGCR.model.intercept import InterceptConfig, Trigger, plan_intercept
    m = Model(QueueRegistry())
    assert m.intercept_geometry() is None

    m.intercept_origin = (47.0, 8.0)
    m.intercept_plan = plan_intercept(Trigger("T", 0, -150, 100, 20, 5, 0, 0), 0, InterceptConfig())
    g = m.intercept_geometry()
    assert g["circle"] == ((47.0, 8.0), 200.0)
    assert len(g["trigger_path"]) == 2 and len(g["trigger_path"][0]) == 3
    lat, lon, alt = g["wait"]
    assert alt == 20.0
    assert abs((lat - 47.0) * 111_320.0 - 100.0) < 0.5    # 100 m nördlich


def test_intercept_trigger_moves_with_time(monkeypatch):
    import QGCR.model.model as model_mod
    from QGCR.model.intercept import InterceptConfig, Trigger, plan_intercept
    now = [1000.0]
    monkeypatch.setattr(model_mod.time, "time", lambda: now[0])

    m = Model(QueueRegistry())
    m.intercept_origin = (47.0, 8.0)
    m.intercept_trigger = Trigger("T5", 1000.0, -150, 100, 20, 5, 0, 0)
    m.intercept_plan = plan_intercept(m.intercept_trigger, 1000.0, InterceptConfig())

    def east_m():
        lat, lon, _ = m.intercept_geometry()["trigger_now"]
        return (lon - 8.0) * 111_320.0 * math.cos(math.radians(47.0))

    assert abs(east_m() - (-150)) < 0.1
    now[0] = 1010.0                                     # 10 s später: 50 m weiter östlich
    assert abs(east_m() - (-100)) < 0.1

    g = m.intercept_geometry()
    assert g["trigger_id"] == "T5" and g["trigger_heading"] == 90.0

    now[0] = 1000.0 + 10_000                            # weit hinter dem Bahnende
    assert m.intercept_geometry()["trigger_now"] is None
