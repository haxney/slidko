"""
Tests for DecodedEvent dataclass.

This tests the requirements from design.md:
- DecodedEvent is a frozen dataclass with kind, start_sample, end_sample, data, channel
- event.seconds(samplerate_hz) returns start_sample/samplerate_hz
- equality by value
"""

import pytest

from slidko.decode.events import DecodedEvent


def test_decoded_event_attributes():
    """Test that DecodedEvent has the required attributes."""
    # Create an event with all required fields
    event = DecodedEvent(
        kind="uart.byte",
        start_sample=100,
        end_sample=200,
        data={"value": 0x41, "ascii": "A"},
        channel="D0",
    )

    # Check that all required attributes are present
    assert event.kind == "uart.byte"
    assert event.start_sample == 100
    assert event.end_sample == 200
    assert event.data == {"value": 0x41, "ascii": "A"}
    assert event.channel == "D0"


def test_decoded_event_seconds():
    """Test that seconds() method returns start_sample/samplerate_hz."""
    event = DecodedEvent(
        kind="uart.byte",
        start_sample=100,
        end_sample=200,
        data={"value": 0x41, "ascii": "A"},
        channel="D0",
    )

    # Test with sample rate of 24 MHz
    samplerate_hz = 24_000_000
    expected_seconds = 100 / samplerate_hz

    assert event.seconds(samplerate_hz) == expected_seconds


def test_decoded_event_equality():
    """Test that DecodedEvent equality is by value."""
    # Create two events with same values
    event1 = DecodedEvent(
        kind="uart.byte",
        start_sample=100,
        end_sample=200,
        data={"value": 0x41, "ascii": "A"},
        channel="D0",
    )

    event2 = DecodedEvent(
        kind="uart.byte",
        start_sample=100,
        end_sample=200,
        data={"value": 0x41, "ascii": "A"},
        channel="D0",
    )

    # They should be equal
    assert event1 == event2

    # Different value should not be equal
    event3 = DecodedEvent(
        kind="uart.byte",
        start_sample=100,
        end_sample=200,
        data={"value": 0x42, "ascii": "B"},
        channel="D0",
    )

    assert event1 != event3


def test_decoded_event_immutable():
    """Test that DecodedEvent is frozen (immutable)."""
    event = DecodedEvent(
        kind="uart.byte",
        start_sample=100,
        end_sample=200,
        data={"value": 0x41, "ascii": "A"},
        channel="D0",
    )

    # This should raise an AttributeError
    with pytest.raises(AttributeError):
        event.kind = "new.kind"  # type: ignore[misc]


if __name__ == "__main__":
    pytest.main([__file__])
