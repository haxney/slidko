"""
Golden-file evaluation (design.md § Golden-file harness, task group 7):
run `narrate` on a synthetic entry, compare its assertion set against a
committed golden ORDER-INSENSITIVELY - missing/extra assertions fail,
reordering passes. The committed goldens are the contract; regenerate them
deliberately via `tests/narrate/regenerate_goldens.py`, never automatically.
"""

import json
from pathlib import Path

import pytest

from slidko.narrate.model import Assertion, Evidence
from slidko.narrate.narrate import narrate
from tests.narrate.golden_scenarios import SCENARIOS

GOLDEN_DIR = Path(__file__).parent / "golden"


def load_golden(name: str) -> list[Assertion]:
    data = json.loads((GOLDEN_DIR / f"{name}.json").read_text())
    return [Assertion.from_json(json.dumps(item)) for item in data]


def assert_matches_golden(actual: list[Assertion], expected: list[Assertion]) -> None:
    """Order-insensitive comparison: Assertion (and its Evidence) are
    frozen, hashable dataclasses, so set comparison naturally reports
    missing/extra without caring about order."""
    assert set(actual) == set(expected)


@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_matches_golden(name: str):
    capture, events, findings, sidecar = SCENARIOS[name]()
    actual = narrate(capture, events, findings, sidecar=sidecar)
    expected = load_golden(name)
    assert_matches_golden(actual, expected)


def test_comparator_rejects_extra_assertion():
    """A golden with an extra expected assertion (not produced by narrate)
    must fail - the comparator is not lax."""
    actual = load_golden("healthy_i2c_imu")
    extra = Assertion(
        kind="transaction.summary",
        text="an assertion narrate() never produced",
        evidence=Evidence(event_indices=(99,)),
        confidence=0.5,
    )
    expected_with_extra = [*actual, extra]

    with pytest.raises(AssertionError):
        assert_matches_golden(actual, expected_with_extra)


def test_comparator_accepts_reordering():
    """A reordered golden must still pass - the comparator is
    order-insensitive."""
    actual = load_golden("i2c_nak_coincidence")
    assert len(actual) >= 2  # sanity: reordering is meaningful here
    reordered = list(reversed(actual))

    assert_matches_golden(actual, reordered)  # must not raise


if __name__ == "__main__":
    pytest.main([__file__])
