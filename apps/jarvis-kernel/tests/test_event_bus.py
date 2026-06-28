"""Tests du bus d'événements (ADR-0004)."""

import unittest

from jarvis_kernel.kernel.event_bus import Event, EventBus


class TestEventBus(unittest.TestCase):
    def setUp(self):
        self.bus = EventBus()

    def test_exact_subscription(self):
        received = []
        self.bus.subscribe("intent.received", received.append)
        self.bus.emit("intent.received", x=1)
        self.bus.emit("other.event", y=2)
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].payload, {"x": 1})

    def test_wildcard_subscription(self):
        received = []
        self.bus.subscribe("presence.*", received.append)
        self.bus.emit("presence.detected")
        self.bus.emit("presence.cleared")
        self.bus.emit("motion.detected")
        self.assertEqual([e.name for e in received],
                         ["presence.detected", "presence.cleared"])

    def test_catch_all(self):
        received = []
        self.bus.subscribe("*", received.append)
        self.bus.emit("a.b")
        self.bus.emit("c.d")
        self.assertEqual(len(received), 2)

    def test_publish_returns_notified_count(self):
        self.bus.subscribe("x.y", lambda e: None)
        self.bus.subscribe("x.*", lambda e: None)
        n = self.bus.publish(Event(name="x.y"))  # publish renvoie le nb de handlers
        self.assertEqual(n, 2)

    def test_unsubscribe(self):
        received = []
        unsub = self.bus.subscribe("x.y", received.append)
        self.bus.emit("x.y")
        unsub()
        self.bus.emit("x.y")
        self.assertEqual(len(received), 1)

    def test_handler_exception_does_not_break_dispatch(self):
        received = []

        def boom(_e):
            raise RuntimeError("boom")

        self.bus.subscribe("x.y", boom)
        self.bus.subscribe("x.y", received.append)
        self.bus.emit("x.y")  # ne doit pas lever
        self.assertEqual(len(received), 1)

    def test_history(self):
        self.bus.emit("a.b")
        self.bus.emit("c.d")
        self.assertEqual([e.name for e in self.bus.history], ["a.b", "c.d"])

    def test_event_is_immutable(self):
        e = Event(name="x.y")
        with self.assertRaises(Exception):
            e.name = "z"  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
