# === PFAD-B FULL FILE: QGCR/test/unittest/dummy_model.py ===

from collections import deque

from QGCR.core.queue_registry import QueueRegistry
from QGCR.logging.log_router import LogRouter
from QGCR.model.model import Model


class DummyModel(Model):
    """
    Echtes Model mit eigener QueueRegistry und LogRouter für FSM-Tests.
    """

    def __init__(self):
        super().__init__(queue_registry=QueueRegistry())
        self.log = LogRouter(self, self.queue_registry)

        # GUI-Events (von SubFSMs per popleft() gelesen)
        self.gui_events = deque()

    # ------------------------------------------------------------
    # Test-Helfer
    # ------------------------------------------------------------
    def gui_items(self):
        """Alle bisher in die GUI-Queue geschobenen Einträge."""
        return self.queue_registry.require("gui").pop_all()

    def qgcr_logs(self):
        """Alle bisher geloggten QGCR-Zeilen."""
        q = self.queue_registry.qgcr_log_queue
        items = []
        while not q.empty():
            items.append(q.get_nowait())
        return items
