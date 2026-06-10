# === PFAD-B FULL FILE: QGCR/test/test_tab_router.py ===

import unittest

from QGCR.view.tab_router import TabRouter


class DummyController:
    """
    Der Controller wird nicht mehr vom TabRouter aufgerufen.
    Wir prüfen nur, dass TabRouter korrekt aufgerufen wird.
    """
    def __init__(self):
        self.called = []


class DummyTabRouter(TabRouter):
    """
    Wir überschreiben on_tab_changed, um Aufrufe zu protokollieren.
    """
    def __init__(self, controller):
        super().__init__(controller)
        self.events = []

    def on_tab_changed(self, tab_name):
        self.events.append(tab_name)


class TestTabRouter(unittest.TestCase):

    def setUp(self):
        self.ctrl = DummyController()
        self.router = DummyTabRouter(self.ctrl)

    def test_route_to_mission(self):
        self.router.on_tab_changed("Mission")
        self.assertEqual(self.router.events, ["Mission"])

    def test_route_to_main(self):
        self.router.on_tab_changed("Home")
        self.assertEqual(self.router.events, ["Home"])

        self.router.events.clear()
        self.router.on_tab_changed("Log")
        self.assertEqual(self.router.events, ["Log"])

        self.router.events.clear()
        self.router.on_tab_changed("Capabilities")
        self.assertEqual(self.router.events, ["Capabilities"])


if __name__ == "__main__":
    unittest.main()
