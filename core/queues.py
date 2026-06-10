# === PFAD-B FULL FILE: QGCR/core/queues.py ===

import queue
import threading


class BaseQueue:
    """
    Basisklasse für thread-sichere Queues.
    Einheitliche API:
    - push(item)
    - pop_all()
    - get_nowait()
    """
    def __init__(self):
        self._queue = queue.Queue()
        self._lock = threading.Lock()

    def push(self, item):
        with self._lock:
            self._queue.put(item)

    def pop_all(self):
        items = []
        while True:
            try:
                items.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return items

    def get_nowait(self):
        """
        Liefert ein einzelnes Element ohne Blockieren.
        Kompatibel zur alten SimpleQueueWrapper-API.
        """
        with self._lock:
            return self._queue.get_nowait()


class RingBufferQueue(BaseQueue):
    """
    Ring-Buffer-ähnliche Queue für hochfrequente Daten (z.B. Telemetrie).
    Behält nur die letzten N Einträge.
    """
    def __init__(self, maxlen=5):
        super().__init__()
        self._maxlen = maxlen

    def push(self, item):
        with self._lock:
            # Leeren, bis Platz ist
            while self._queue.qsize() >= self._maxlen:
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    break
            self._queue.put(item)


class TelemetryQueue(RingBufferQueue):
    """
    Spezialisierte Queue für Telemetrie.
    """
    pass


class FSMEventQueue(BaseQueue):
    """
    Queue für FSM-Events (deterministisch, nichts droppen).
    """
    pass


class MissionQueue(BaseQueue):
    """
    Queue für Mission-Operationen (Upload/Download).
    """
    pass


class GUIEventQueue(BaseQueue):
    """
    Queue für GUI-Events, die im Tk-Thread verarbeitet werden.
    """
    pass
