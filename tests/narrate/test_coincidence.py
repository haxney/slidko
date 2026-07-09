import unittest

from slidko.decode.events import DecodedEvent as CanonicalDecodedEvent
from slidko.measure.smoke import SmokeFinding as CanonicalSmokeFinding
from slidko.narrate.coincidence import detect_coincidences

# Test the coincidence detection functionality


class TestCoincidence(unittest.TestCase):
    def test_coincident_events_create_assertion(self):
        """A NAK on one channel and a SmokeFinding on another, within the
        coincidence window, yield a single coincidence assertion naming both
        channels and the time delta in real units."""
        nak_event = CanonicalDecodedEvent(
            kind="i2c.nak",
            start_sample=100,
            end_sample=105,
            data={"address": 0x68},
            channel="0",
        )
        finding = CanonicalSmokeFinding(
            check="timing_violation",
            channel="1",
            start_sample=105,
            end_sample=110,
            severity="warn",
            summary="Test timing violation",
            escalation="smoke → scope: test",
            evidence={},
        )  # Within coincidence window

        results = detect_coincidences([nak_event], [finding], 1_000_000)
        coincidence_assertions = [a for a in results if a.kind == "coincidence"]
        assert len(coincidence_assertions) > 0

        assertion = coincidence_assertions[0]
        assert "0" in assertion.text
        assert "1" in assertion.text
        # Evidence must use real list-position indices (into events/findings),
        # not raw sample numbers, and must reference the finding via
        # finding_refs (not smuggled into event_indices).
        assert assertion.evidence.event_indices == (0,)
        assert assertion.evidence.finding_refs == (0,)
        assert assertion.evidence.sample_ranges == (
            (nak_event.start_sample, nak_event.end_sample),
            (finding.start_sample, finding.end_sample),
        )

    def test_non_coincident_events_do_not_coincide(self):
        """events outside the window do NOT coincide"""
        nak_event = CanonicalDecodedEvent(
            kind="i2c.nak",
            start_sample=100,
            end_sample=105,
            data={"address": 0x68},
            channel="0",
        )
        finding = CanonicalSmokeFinding(
            check="timing_violation",
            channel="1",
            start_sample=1000,
            end_sample=1005,
            severity="warn",
            summary="Test timing violation",
            escalation="smoke → scope: test",
            evidence={},
        )  # Outside coincidence window

        results = detect_coincidences([nak_event], [finding], 1_000_000)
        coincidence_assertions = [a for a in results if a.kind == "coincidence"]
        assert len(coincidence_assertions) == 0


if __name__ == "__main__":
    unittest.main()
