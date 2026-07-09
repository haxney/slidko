import os
import tempfile
import zipfile

import numpy as np
import pytest

from slidko.capture import Capture
from slidko.capture.srfile import read_sr, write_sr


@pytest.fixture
def tmp_sr_path():
    with tempfile.NamedTemporaryFile(suffix=".sr", delete=False) as tmp:
        path = tmp.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


def test_sr_round_trip_bit_exact(tmp_sr_path):
    """Asymmetric per-channel patterns must round-trip bit-for-bit, including
    samplerate, channel names, and provenance."""
    rng = np.random.default_rng(1234)
    channels = {
        "clk": np.array([True, False] * 17, dtype=bool),
        "data": rng.integers(0, 2, size=34).astype(bool),
        "cs_n": np.zeros(34, dtype=bool),
    }
    samplerate_hz = 24_000_000
    provenance = {
        "instrument": "fx2lafw",
        "samplerate_hz": samplerate_hz,
        "threshold_v": 1.8,
    }
    capture = Capture(
        channels=channels, samplerate_hz=samplerate_hz, provenance=provenance
    )

    write_sr(capture, tmp_sr_path)
    read_capture = read_sr(tmp_sr_path)

    assert read_capture.samplerate_hz == samplerate_hz
    assert list(read_capture.channels) == list(channels)
    for name, original in channels.items():
        np.testing.assert_array_equal(read_capture.channels[name], original)
    assert read_capture.provenance["instrument"] == "fx2lafw"
    assert read_capture.provenance["samplerate_hz"] == samplerate_hz
    assert read_capture.provenance["threshold_v"] == pytest.approx(1.8)


def test_sr_round_trip_multi_chunk(tmp_sr_path):
    """Data forced across multiple logic-1-* chunks reassembles contiguously."""
    rng = np.random.default_rng(99)
    n_samples = 500
    channels = {
        "a": rng.integers(0, 2, size=n_samples).astype(bool),
        "b": rng.integers(0, 2, size=n_samples).astype(bool),
    }
    capture = Capture(
        channels=channels,
        samplerate_hz=1_000_000,
        provenance={"instrument": "fx2lafw", "samplerate_hz": 1_000_000},
    )

    # Force a small chunk size so the packed stream (500 bytes) splits across
    # several logic-1-<n> chunks.
    write_sr(capture, tmp_sr_path, chunk_size=64)

    with zipfile.ZipFile(tmp_sr_path) as zf:
        logic_chunks = [n for n in zf.namelist() if n.startswith("logic-1-")]
    assert len(logic_chunks) > 1

    read_capture = read_sr(tmp_sr_path)
    for name, original in channels.items():
        np.testing.assert_array_equal(read_capture.channels[name], original)


def test_sr_round_trip_non_byte_multiple_channels(tmp_sr_path):
    """Channel counts that aren't multiples of 8 discard padding bits cleanly."""
    channels = {
        "ch1": np.array([True, False, True, True, False], dtype=bool),
        "ch2": np.array([False, False, True, False, True], dtype=bool),
        "ch3": np.array([True, True, False, False, True], dtype=bool),
    }
    capture = Capture(
        channels=channels,
        samplerate_hz=8_000_000,
        provenance={"instrument": "fx2lafw", "samplerate_hz": 8_000_000},
    )

    write_sr(capture, tmp_sr_path)
    read_capture = read_sr(tmp_sr_path)

    assert len(read_capture.channels) == 3
    for name, original in channels.items():
        np.testing.assert_array_equal(read_capture.channels[name], original)


def test_write_sr_exists():
    assert callable(write_sr)


def test_read_sr_exists():
    assert callable(read_sr)
