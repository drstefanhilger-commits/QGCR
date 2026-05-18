# QGCR/test/test_mission_substates.py

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

        self.request_mission_download = False
        self.request_mission_upload = False

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
    print("\n=== MISSION SUBSTATE HARNESS TEST ===\n")

    model = FakeModel()
    connection = FakeConnection()

    sm = MainStateMachine(model, connection)

    # Startup vollständig deaktivieren
    sm.startup_sm = None

    # Direkt in Mission-High-Level-State
    sm.state = MainState.MISSION
    sm.mission_sm.on_entrance()

    print("\n--- Anforderung: DOWNLOAD ---")
    model.request_mission_download = True
    sm.update()

    print("\n--- Sende MISSION_COUNT ---")
    connection.broadcast(mission_count(3))
    sm.update()

    print("\n--- Sende Mission Items ---")
    for i in range(3):
        connection.broadcast(mission_item(i))
        sm.update()
        time.sleep(0.1)
        
    # WICHTIG: Ein letzter update() für GOTO_READY → READY
    sm.update()

    print("\n=== ERGEBNIS ===")
    print(f"High-Level-State: {sm.state}")

    if sm.state == MainState.READY:
        print("✔ Test bestanden: Mission-Download → READY")
    else:
        print("❌ Test fehlgeschlagen")


if __name__ == "__main__":
    main()
