#!/usr/bin/env python3
# === PFAD-B FULL FILE: QGCR/pytest/test_core_queues.py ===

import pytest
import queue

from QGCR.core.queues import (
    BaseQueue,
    RingBufferQueue,
    TelemetryQueue,
    FSMEventQueue,
    MissionQueue,
    GUIEventQueue,
)


# ------------------------------------------------------------
# Helper: Typname via dict-dispatch
# ------------------------------------------------------------
def typename(obj):
    dispatch = {
        TelemetryQueue: "telemetry",
        RingBufferQueue: "ring",
        BaseQueue: "base",
        FSMEventQueue: "fsm",
        MissionQueue: "mission",
        GUIEventQueue: "gui",
    }
    for cls, name in dispatch.items():
        if isinstance(obj, cls):
            return name
    return "unknown"


# ------------------------------------------------------------
# BaseQueue Tests
# ------------------------------------------------------------

def test_basequeue_push_and_pop_all():
    q = BaseQueue()
    q.push(1)
    q.push(2)
    q.push(3)

    items = q.pop_all()
    assert items == [1, 2, 3]

    # danach leer
    assert q.pop_all() == []


def test_basequeue_thread_safety():
    q = BaseQueue()

    for i in range(50):
        q.push(i)

    items = q.pop_all()
    assert len(items) == 50
    assert items[0] == 0
    assert items[-1] == 49


# ------------------------------------------------------------
# RingBufferQueue Tests
# ------------------------------------------------------------

def test_ringbuffer_maxlen():
    q = RingBufferQueue(maxlen=3)

    q.push("A")
    q.push("B")
    q.push("C")
    q.push("D")  # A wird gedroppt

    items = q.pop_all()
    assert items == ["B", "C", "D"]


def test_ringbuffer_overflow_multiple():
    q = RingBufferQueue(maxlen=2)

    q.push(1)
    q.push(2)
    q.push(3)
    q.push(4)

    items = q.pop_all()
    assert items == [3, 4]


# ------------------------------------------------------------
# TelemetryQueue Tests (RingBufferQueue)
# ------------------------------------------------------------

def test_telemetryqueue_is_ringbuffer():
    q = TelemetryQueue()
    assert typename(q) == "telemetry"

    # Default maxlen = 5
    for i in range(10):
        q.push(i)

    items = q.pop_all()
    assert items == [5, 6, 7, 8, 9]


# ------------------------------------------------------------
# FSMEventQueue Tests
# ------------------------------------------------------------

def test_fsmqueue_drops_nothing():
    q = FSMEventQueue()

    for i in range(10):
        q.push(i)

    items = q.pop_all()
    assert items == list(range(10))


# ------------------------------------------------------------
# MissionQueue Tests
# ------------------------------------------------------------

def test_missionqueue_order():
    q = MissionQueue()

    q.push("upload")
    q.push("download")
    q.push("clear")

    items = q.pop_all()
    assert items == ["upload", "download", "clear"]


# ------------------------------------------------------------
# GUIEventQueue Tests
# ------------------------------------------------------------

def test_guieventqueue_basic():
    q = GUIEventQueue()

    q.push("click")
    q.push("keypress")

    items = q.pop_all()
    assert items == ["click", "keypress"]


def test_guieventqueue_is_bounded_ring():
    q = GUIEventQueue()
    assert isinstance(q, RingBufferQueue)

    for i in range(GUIEventQueue.MAXLEN + 100):
        q.push(i)

    items = q.pop_all()
    assert len(items) == GUIEventQueue.MAXLEN
    assert items[0] == 100
    assert items[-1] == GUIEventQueue.MAXLEN + 99


def test_guieventqueue_custom_maxlen():
    q = GUIEventQueue(maxlen=3)
    for i in range(5):
        q.push(i)
    assert q.pop_all() == [2, 3, 4]
