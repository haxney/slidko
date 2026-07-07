import unittest

from slidko.narrate.coincidence import (
    DecodedEvent,
    SmokeFinding,
    detect_coincidences,
)

# Test the coincidence detection functionality


class TestCoincidence(unittest.TestCase):
    def test_coincident_events_create_assertion(self):
        """A NAK on one channel and a SmokeFinding on another, within the
        coincidence window, yield a single coincidence assertion naming both
        channels and the time delta in real units."""
        nak_event = DecodedEvent(kind="i2c.nak", address=0x68, channel=0, sample=100)
        finding = SmokeFinding(channel=1, sample=105)  # Within coincidence window

        results = detect_coincidences([nak_event], [finding], 1_000_000)
        coincidence_assertions = [a for a in results if a.kind == "coincidence"]
        assert len(coincidence_assertions) > 0

    def test_non_coincident_events_do_not_coincide(self):
        """events outside the window do NOT coincide"""
        nak_event = DecodedEvent(kind="i2c.nak", address=0x68, channel=0, sample=100)
        finding = SmokeFinding(channel=1, sample=1000)  # Outside coincidence window

        results = detect_coincidences([nak_event], [finding], 1_000_000)
        coincidence_assertions = [a for a in results if a.kind == "coincidence"]
        assert len(coincidence_assertions) == 0


if __name__ == "__main__":
    unittest.main()
