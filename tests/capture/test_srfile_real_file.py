"""Real-file validation: reading an actual sigrok-cli demo-driver capture.

Uses the `demo_capture` fixture (tests/conftest.py), which generates the
fixture on demand and skips cleanly when sigrok-cli isn't installed — these
tests never require the suite to hard-depend on the binary.
"""

import zipfile

from slidko.capture.srfile import read_sr


def test_demo_capture_samplerate_and_channel_count(demo_capture):
    capture = read_sr(str(demo_capture))
    assert capture.samplerate_hz == 24_000_000
    assert len(capture.channels) == 8


def test_reader_selects_logic_chunks_and_ignores_interleaved_analog_chunks(
    demo_capture,
):
    with zipfile.ZipFile(demo_capture) as zf:
        names = zf.namelist()
    assert any(name.startswith("analog-1-") for name in names), (
        "fixture sanity check: the demo driver should emit interleaved analog "
        "chunks in the same zip"
    )

    # read_sr must not choke on, or accidentally ingest, the analog chunks.
    capture = read_sr(str(demo_capture))
    assert len(capture.channels) == 8
    for samples in capture.channels.values():
        assert samples.dtype == bool
