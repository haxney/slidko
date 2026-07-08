"""
Guard tests to ensure narrate modules use canonical schema classes.
"""

import unittest

from slidko.decode.events import DecodedEvent as CanonicalDecodedEvent
from slidko.measure.smoke import SmokeFinding as CanonicalSmokeFinding
from slidko.narrate.coincidence import DecodedEvent, SmokeFinding


class TestCanonicalSchemas(unittest.TestCase):
    def test_coincidence_uses_canonical_decoded_event(self):
        """Ensure coincidence module imports and uses the canonical DecodedEvent"""
        # This should be the same class from the canonical location
        assert DecodedEvent is CanonicalDecodedEvent

    def test_coincidence_uses_canonical_smoke_finding(self):
        """Ensure coincidence module imports and uses the canonical SmokeFinding"""
        # This should be the same class from the canonical location
        assert SmokeFinding is CanonicalSmokeFinding
