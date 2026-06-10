# === PFAD-B FULL FILE: test_airborne_events.py ===

import unittest

from QGCR.states.airborne.airborne_events import (
    AirborneEvent,
    AirborneEventType,
    AirborneEvents
)


class TestAirborneEvents(unittest.TestCase):

    def test_event_types_are_correct(self):
        self.assertEqual(AirborneEvents.MODE_MANUAL.type, AirborneEventType.MODE_CHANGE)
        self.assertEqual(AirborneEvents.MISSION_STARTED.type, AirborneEventType.MISSION)
        self.assertEqual(AirborneEvents.FAILSAFE_GPS_LOST.type, AirborneEventType.FAILSAFE)
        self.assertEqual(AirborneEvents.TAKEOFF_COMPLETE.type, AirborneEventType.SYSTEM)
        self.assertEqual(AirborneEvents.INTERNAL_TICK.type, AirborneEventType.INTERNAL)

    def test_event_names_are_correct(self):
        self.assertEqual(AirborneEvents.MODE_POSCTL.name, "MODE_POSCTL")
        self.assertEqual(AirborneEvents.MODE_AUTO_RTL.name, "MODE_AUTO_RTL")
        self.assertEqual(AirborneEvents.MISSION_WAYPOINT_REACHED.name, "MISSION_WAYPOINT_REACHED")
        self.assertEqual(AirborneEvents.FAILSAFE_BATTERY_LOW.name, "FAILSAFE_BATTERY_LOW")
        self.assertEqual(AirborneEvents.LANDING_DETECTED.name, "LANDING_DETECTED")

    def test_event_payload_default_is_none(self):
        self.assertIsNone(AirborneEvents.MODE_MANUAL.payload)
        self.assertIsNone(AirborneEvents.MISSION_STARTED.payload)
        self.assertIsNone(AirborneEvents.FAILSAFE_GEOFENCE.payload)

    def test_event_is_instance_of_airborne_event(self):
        self.assertIsInstance(AirborneEvents.MODE_MANUAL, AirborneEvent)
        self.assertIsInstance(AirborneEvents.MISSION_FINISHED, AirborneEvent)
        self.assertIsInstance(AirborneEvents.FAILSAFE_RC_LOST, AirborneEvent)

    def test_constants_are_singletons(self):
        # Jede Konstante muss exakt dieselbe Instanz sein
        self.assertIs(AirborneEvents.MODE_MANUAL, AirborneEvents.MODE_MANUAL)
        self.assertIs(AirborneEvents.MODE_AUTO_MISSION, AirborneEvents.MODE_AUTO_MISSION)
        self.assertIs(AirborneEvents.FAILSAFE_GPS_LOST, AirborneEvents.FAILSAFE_GPS_LOST)

    def test_custom_payload(self):
        evt = AirborneEvent(AirborneEventType.MISSION, "MISSION_WAYPOINT_REACHED", payload={"wp": 5})
        self.assertEqual(evt.payload, {"wp": 5})
        self.assertEqual(evt.name, "MISSION_WAYPOINT_REACHED")
        self.assertEqual(evt.type, AirborneEventType.MISSION)


if __name__ == "__main__":
    unittest.main()
