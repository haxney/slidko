from dataclasses import is_dataclass

import numpy as np
import pytest

from slidko.capture import Capture


def test_capture_is_dataclass():
    """Test that Capture is implemented as a dataclass."""
    assert is_dataclass(Capture)


def test_capture_construction():
    """Test basic Capture construction with required fields."""
    channels = {"ch1": np.array([True, False, True], dtype=bool)}
    samplerate_hz = 24_000_000
    provenance = {
        "instrument": "fx2lafw",
        "samplerate_hz": samplerate_hz,
        "threshold_v": 1.8,
    }

    capture = Capture(
        channels=channels, samplerate_hz=samplerate_hz, provenance=provenance
    )

    assert capture.channels == channels
    assert capture.samplerate_hz == samplerate_hz
    assert capture.provenance == provenance


def test_capture_immutability():
    """Test that Capture objects are immutable."""
    channels = {"ch1": np.array([True, False, True], dtype=bool)}
    samplerate_hz = 24_000_000
    provenance = {
        "instrument": "fx2lafw",
        "samplerate_hz": samplerate_hz,
        "threshold_v": 1.8,
    }

    capture = Capture(
        channels=channels, samplerate_hz=samplerate_hz, provenance=provenance
    )

    # These should raise AttributeError since Capture is immutable
    with pytest.raises(AttributeError):
        capture.channels = {"ch2": np.array([False, True, False], dtype=bool)}  # type: ignore[misc]

    with pytest.raises(AttributeError):
        capture.samplerate_hz = 12_000_000  # type: ignore[misc]

    with pytest.raises(AttributeError):
        capture.provenance = {"instrument": "different"}  # type: ignore[misc]


def test_capture_provenance_fields():
    """Test that Capture accepts and stores provenance fields correctly."""
    channels = {"ch1": np.array([True, False, True], dtype=bool)}
    samplerate_hz = 24_000_000
    provenance = {
        "instrument": "fx2lafw",
        "samplerate_hz": samplerate_hz,
        "threshold_v": 1.8,
    }

    capture = Capture(
        channels=channels, samplerate_hz=samplerate_hz, provenance=provenance
    )

    assert capture.provenance["instrument"] == "fx2lafw"
    assert capture.provenance["samplerate_hz"] == samplerate_hz
    assert capture.provenance["threshold_v"] == 1.8


def test_capture_empty_channels():
    """Test Capture with empty channels dictionary."""
    capture = Capture(channels={}, samplerate_hz=24_000_000, provenance={})

    assert capture.channels == {}
    assert capture.samplerate_hz == 24_000_000
    assert capture.provenance == {}


def test_capture_multiple_channels():
    """Test Capture with multiple channels."""
    channels = {
        "ch1": np.array([True, False, True], dtype=bool),
        "ch2": np.array([False, True, False], dtype=bool),
        "ch3": np.array([True, True, False], dtype=bool),
    }

    capture = Capture(
        channels=channels,
        samplerate_hz=24_000_000,
        provenance={"instrument": "fx2lafw"},
    )

    assert capture.channels == channels
