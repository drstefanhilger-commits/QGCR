#!/usr/bin/env python3
# === PFAD-B FULL FILE: QGCR/test/test_core_queue_registry.py ===

import pytest

from QGCR.core.queue_registry import QueueRegistry
from QGCR.core.queues import (
    BaseQueue,
    TelemetryQueue,
    FSMEventQueue,
    MissionQueue,
    GUIEventQueue,
)


# ------------------------------------------------------------
# Helper für switch/case (dict-dispatch)
# ------------------------------------------------------------
def queue_type_name(q):
    dispatch = {
        TelemetryQueue: "telemetry",
        FSMEventQueue: "fsm",
        MissionQueue: "mission",
        GUIEventQueue: "gui",
        BaseQueue: "base",
    }
    for cls, name in dispatch.items():
        if isinstance(q, cls):
            return name
    return "unknown"


# ------------------------------------------------------------
# Tests
# ------------------------------------------------------------

def test_system_queues_exist():
    reg = QueueRegistry()

    assert reg.exists("telemetry")
    assert reg.exists("fsm")
    assert reg.exists("mission")
    assert reg.exists("gui")

    assert isinstance(reg.get("telemetry"), TelemetryQueue)
    assert isinstance(reg.get("fsm"), FSMEventQueue)
    assert isinstance(reg.get("mission"), MissionQueue)
    assert isinstance(reg.get("gui"), GUIEventQueue)


def test_register_dynamic_queue():
    reg = QueueRegistry()

    q = reg.register("worker1", BaseQueue)

    assert reg.exists("worker1")
    assert isinstance(q, BaseQueue)
    assert reg.get("worker1") is q


def test_register_duplicate_fails():
    reg = QueueRegistry()

    reg.register("workerX", BaseQueue)

    with pytest.raises(ValueError):
        reg.register("workerX", BaseQueue)


def test_register_wrong_type_fails():
    reg = QueueRegistry()

    class NotAQueue:
        pass

    with pytest.raises(TypeError):
        reg.register("bad", NotAQueue)


def test_require_success():
    reg = QueueRegistry()
    q = reg.require("telemetry")
    assert isinstance(q, TelemetryQueue)


def test_require_fails():
    reg = QueueRegistry()
    with pytest.raises(KeyError):
        reg.require("does_not_exist")


def test_list_queues():
    reg = QueueRegistry()
    names = reg.list()

    # System queues müssen enthalten sein
    assert "telemetry" in names
    assert "fsm" in names
    assert "mission" in names
    assert "gui" in names


def test_clear_dynamic():
    reg = QueueRegistry()

    reg.register("dyn1", BaseQueue)
    reg.register("dyn2", BaseQueue)

    reg.clear_dynamic()

    # System queues bleiben
    assert reg.exists("telemetry")
    assert reg.exists("fsm")
    assert reg.exists("mission")
    assert reg.exists("gui")

    # Dynamische Queues sind weg
    assert not reg.exists("dyn1")
    assert not reg.exists("dyn2")


def test_clear_all():
    reg = QueueRegistry()

    reg.register("dynA", BaseQueue)
    reg.register("dynB", BaseQueue)

    reg.clear_all()

    assert reg.list() == []
