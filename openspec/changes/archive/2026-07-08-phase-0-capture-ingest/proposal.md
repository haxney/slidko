# Proposal: phase-0-capture-ingest

## Why

Every pipeline stage consumes captures as numpy bit arrays; nothing downstream (Measure, Decode, the smoke detector) can exist until raw acquisitions can be read, and edges extracted, deterministically. This is docs/ROADMAP.md Phase 0 (Capture ingest & edge extraction), covering docs/TASKS.md items 2 (.sr reader), 3 (edge extraction), and 7 (sigrok-cli wrapper).

## What Changes

- Add `capture/srfile.py`: read sigrok session (.sr) files — zip container with configparser-format `metadata` and packed binary `logic-1-*` chunks — into a `Capture` (per-channel numpy bool arrays + samplerate + channel names + provenance metadata). Include a minimal .sr writer so synthetic fixtures round-trip without hardware.
- Add `measure/edges.py`: vectorized per-channel rising/falling edge timestamps (sample_index, polarity) from bit arrays, plus inter-edge interval helpers.
- Add `capture/sigrokcli.py`: thin subprocess wrapper for timed capture from an fx2lafw-class device to .sr; device enumeration; clean driver-error surfacing. Mockable leaf dependency; never imported by tests as a requirement.

## Capabilities

### New Capabilities

- `capture-ingest`: .sr read/write into `Capture` objects with provenance (chain of custody: instrument identity, samplerate, threshold).
- `edge-extraction`: edge timestamp and interval extraction from bit arrays.
- `capture-acquisition`: sigrok-cli subprocess orchestration for live capture (hardware-touching; excluded from the test suite's execution path).

### Modified Capabilities

(none)

## Impact

- New modules under `src/slidko/capture/` and `src/slidko/measure/`; test fixtures under `tests/`.
- Depends on bootstrap-python-package being applied.
- Format-detail risk: .sr chunk naming and unitsize handling are MODERATE confidence until verified against a real sigrok-cli-generated file (flagged in TASKS.md); the reader must be validated against one real capture before Phase 1 relies on it.
