# QGCR/test/test_mission_load_fsm.py

import time
from types import SimpleNamespace

from QGCR.states.main_state_machine import MainStateMachine
from QGCR.states.main_state import MainState


class FakeConnection:
    def __init__(self):
        self.subscribers = []

    def register_subscriber(self):
        from queue import Queue
        q = Queue()
        self.subscribers.append(q)
        return q

    def broadcast(self, msg):
        for q in self.subscribers:
            q.put(msg)


class FakeModel:
    def __init__(self):
        self.log_messages = []
        self.mission_expected = 0
        self.mission_received = 0
        self.mission_items = []

    def add_log(self, msg):
        print(msg)
        self.log_messages.append(msg)

    def clear_mission_sync(self):
        self.mission_expected = 0
        self.mission_received = 0
        self.mission_items = []

    def add_mission_item_raw(self, msg):
        self.mission_items.append(msg)
        self.mission_received += 1
        self.add_log(f"Mission item received: seq={msg.seq}")


def mission_count(n):
    return SimpleNamespace(
        get_type=lambda: "MISSION_COUNT",
        count=n
    )


def mission_item(seq):
    return SimpleNamespace(
        get_type=lambda: "MISSION_ITEM_INT",
        seq=seq
    )


def main():
    print("\n=== MISSION LOAD FSM HARNESS TEST ===\n")

    model = FakeModel()
    connection = FakeConnection()

    sm = MainStateMachine(model, connection)

    sm.state = MainState.MISSION_LOAD
    sm.mission_sm.on_entrance()

    print("\n--- Sende MISSION_COUNT ---")
    connection.broadcast(mission_count(5))
    sm.update()

    print("\n--- Sende Mission Items ---")
    for i in range(5):
        connection.broadcast(mission_item(i))
        sm.update()
        time.sleep(0.1)

    print("\n=== ERGEBNIS ===")
    print(f"High-Level-State: {sm.state}")

    if sm.state == MainState.READY:
        print("✔ Test bestanden: Mission geladen → READY")
    else:
        print("❌ Test fehlgeschlagen")


if __name__ == "__main__":
    main()
