# Tasks: phase-0-capture-ingest

## 1. Capture container

- [x] 1.1 Write failing tests for `Capture` dataclass: construction, immutability, provenance fields (instrument, samplerate_hz, threshold_v)
- [x] 1.2 Implement `Capture` in `src/slidko/capture/__init__.py` (or `capture/model.py`); tests green

## 2. .sr writer + reader (round trip first)

- [x] 2.1 Write failing round-trip test: synthetic asymmetric per-channel bool arrays -> `write_sr` -> `read_sr` -> bit-exact equality including samplerate, channel names, provenance
- [x] 2.2 Implement `write_sr` in `src/slidko/capture/srfile.py` (zip: `metadata` INI + packed `logic-1-1` chunk, unitsize from channel count)
- [x] 2.3 Implement `read_sr`: parse metadata, unpack chunks via `np.unpackbits`, slice to channel count; round-trip test green
- [x] 2.4 Write failing test for multi-chunk files (write fixture with data split across `logic-1-1`/`logic-1-2`); implement chunk-ordered reassembly; green
- [x] 2.5 Write failing test for non-8-multiple channel counts (3 channels); implement padding-bit discard; green

## 3. Edge extraction

- [x] 3.1 Write failing test: 1 kHz square wave at 24 MS/s -> intervals exactly 12000 samples, strict polarity alternation
- [x] 3.2 Write failing tests for boundary conditions (array starts/ends mid-level; all-constant channel -> zero edges)
- [x] 3.3 Implement `src/slidko/measure/edges.py` (`np.diff`/`np.flatnonzero`; (sample_index, polarity) output); all edge tests green
- [x] 3.4 Write failing test for interval helpers against generator ground truth; implement helpers; green

## 4. sigrok-cli wrapper

- [x] 4.1 Write failing tests with mocked subprocess: argument-list construction (driver/samplerate/time/output); typed exceptions on nonzero exit carrying stderr
- [x] 4.2 Implement `src/slidko/capture/sigrokcli.py` with exception hierarchy (`CaptureError`, `DeviceNotFound`, `DriverError`); tests green
- [x] 4.3 Verify full suite passes with no sigrok-cli binary present (`pytest` in clean env)

## 5. Real-file validation gate

- [x] 5.1 Add a `demo_capture` pytest fixture in `tests/conftest.py`: returns the path to `tests/fixtures/generated/sigrok-demo-capture.sr` (creating the `generated/` dir), generating it on demand when absent via `sigrok-cli --driver demo --config samplerate=24000000 --time 10 -O srzip -o <path>`, and `pytest.skip`-ing cleanly when sigrok-cli is not installed. The `generated/` dir is gitignored — regenerable fixtures only; real hardware captures live elsewhere and are committed.
- [x] 5.2 Using `demo_capture`, add a test that reads the demo capture and sanity-checks samplerate (24 MHz) and 8 logic channels
- [x] 5.3 Add a test asserting the reader selects chunks by `logic-1-` prefix and ignores the interleaved `analog-1-<ch>-<n>` chunks the demo driver emits in the same zip — a real, confirmed property of sigrok-cli output (see `tests/fixtures/README.md`), not a hypothetical
- [x] 5.4 Confirm the real-file tests SKIP (not fail) on a machine with no sigrok-cli binary, consistent with the capture-acquisition "no sigrok installed" requirement

## 6. Wrap-up

- [x] 6.1 `ruff check .` and `ruff format --check .` clean; `pytest` fully green
