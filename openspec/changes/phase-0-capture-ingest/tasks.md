# Tasks: phase-0-capture-ingest

## 1. Capture container

- [ ] 1.1 Write failing tests for `Capture` dataclass: construction, immutability, provenance fields (instrument, samplerate_hz, threshold_v)
- [ ] 1.2 Implement `Capture` in `src/slidko/capture/__init__.py` (or `capture/model.py`); tests green

## 2. .sr writer + reader (round trip first)

- [ ] 2.1 Write failing round-trip test: synthetic asymmetric per-channel bool arrays -> `write_sr` -> `read_sr` -> bit-exact equality including samplerate, channel names, provenance
- [ ] 2.2 Implement `write_sr` in `src/slidko/capture/srfile.py` (zip: `metadata` INI + packed `logic-1-1` chunk, unitsize from channel count)
- [ ] 2.3 Implement `read_sr`: parse metadata, unpack chunks via `np.unpackbits`, slice to channel count; round-trip test green
- [ ] 2.4 Write failing test for multi-chunk files (write fixture with data split across `logic-1-1`/`logic-1-2`); implement chunk-ordered reassembly; green
- [ ] 2.5 Write failing test for non-8-multiple channel counts (3 channels); implement padding-bit discard; green

## 3. Edge extraction

- [ ] 3.1 Write failing test: 1 kHz square wave at 24 MS/s -> intervals exactly 12000 samples, strict polarity alternation
- [ ] 3.2 Write failing tests for boundary conditions (array starts/ends mid-level; all-constant channel -> zero edges)
- [ ] 3.3 Implement `src/slidko/measure/edges.py` (`np.diff`/`np.flatnonzero`; (sample_index, polarity) output); all edge tests green
- [ ] 3.4 Write failing test for interval helpers against generator ground truth; implement helpers; green

## 4. sigrok-cli wrapper

- [ ] 4.1 Write failing tests with mocked subprocess: argument-list construction (driver/samplerate/time/output); typed exceptions on nonzero exit carrying stderr
- [ ] 4.2 Implement `src/slidko/capture/sigrokcli.py` with exception hierarchy (`CaptureError`, `DeviceNotFound`, `DriverError`); tests green
- [ ] 4.3 Verify full suite passes with no sigrok-cli binary present (`pytest` in clean env)

## 5. Real-file validation gate

- [ ] 5.1 Add a test that reads `tests/fixtures/sigrok-demo-capture.sr` (real capture, already present — see `tests/fixtures/README.md`) and sanity-checks samplerate (24 MHz) and 8 logic channels
- [ ] 5.2 Add a test asserting the reader selects chunks by `logic-1-` prefix and ignores interleaved `analog-1-<ch>-<n>` chunks in the same fixture — this is a real, confirmed property of sigrok-cli output, not a hypothetical

## 6. Wrap-up

- [ ] 6.1 `ruff check .` and `ruff format --check .` clean; `pytest` fully green
