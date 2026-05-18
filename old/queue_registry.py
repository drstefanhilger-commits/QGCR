# === PFAD-B FULL FILE: QGCR/communication/queue_registry.py ===

import queue


class SimpleQueueWrapper:
    """
    Ein dünner Wrapper um queue.Queue, damit wir eine einheitliche API haben:
    - push(item)
    - get_nowait()
    """

    def __init__(self):
        self._q = queue.Queue()

    def push(self, item):
        self._q.put(item)

    def get_nowait(self):
        return self._q.get_nowait()


class QueueRegistry:
    """
    Zentrale Queue-Sammlung für GUIEventLoop und Model.
    - gui: Events für das GUI (telemetry, status, log, mission_item)
    """

    def __init__(self):
        # GUI-Event-Queue
        self.gui = SimpleQueueWrapper()
