# Design: phase-0-capture-ingest

## Context

First real pipeline code. The .sr format is a zip container (configparser `metadata` + packed `logic-1-*` chunks). Format details are now CONFIRMED against a real local capture (`tests/fixtures/generated/sigrok-demo-capture.sr`, generated via `sigrok-cli --driver demo`, no hardware/network required — see `tests/fixtures/README.md`): `unitsize=1`, multi-chunk (`logic-1-1`, `logic-1-2`, ...), and critically, **analog chunks (`analog-1-<ch>-<n>`) are interleaved in the same zip** — the reader must select strictly by `logic-1-` prefix. Architecture posture: parasitic on sigrok via subprocess + files, never in-process bindings (docs/ARCHITECTURE.md § Sigrok posture).

## Goals / Non-Goals

**Goals:**
- Deterministic ingest: .sr -> `Capture` (numpy bool arrays + provenance).
- Edge extraction exact on clean synthetics; vectorized throughout.
- Thin, mockable acquisition wrapper.

**Non-Goals:**
- No protocol inference (Phase 1). No decoding (Phase 2). No streaming ingest — batch files only in v1. No analog/threshold handling beyond recording metadata.

## Decisions

- **Own .sr reader, not sigrok's** — parsing zip+INI+binary is small, removes a runtime dependency for the ingest path, and is the robust integration route already ruled in ARCHITECTURE.md. sigrok-cli remains the *producer* of real files.
- **`Capture` as a frozen dataclass** holding `channels: dict[str, np.ndarray(bool)]`, `samplerate_hz: int`, `provenance: dict`. Immutable because captures are evidence.
- **Minimal writer lives beside the reader** (`capture/srfile.py`) — needed for round-trip acceptance and later for `corpus/synthetic/` fixtures; kept to the subset the reader consumes.
- **Unitsize/bit-packing**: unpack with `np.unpackbits` on the raw chunk bytes reshaped by unitsize, then slice to channel count — no per-sample loops.
- **Wrapper errors as a small exception hierarchy** (`CaptureError` -> `DeviceNotFound`, `DriverError`) wrapping stderr; subprocess boundary injected for tests.

## Risks / Trade-offs

- [.sr format assumptions wrong (chunk naming, unitsize semantics)] → RESOLVED: verified against `tests/fixtures/generated/sigrok-demo-capture.sr`, a real local capture. Remaining residual risk is narrow (other sigrok-cli versions/output modes might differ); assumptions stay isolated in one module.
- [Endianness/bit-order mistakes silently flip channels] → round-trip test uses asymmetric per-channel patterns that detect ordering errors.
- [Writer diverges from what sigrok-cli emits] → writer output is validated by our reader only; never claimed sigrok-compatible beyond the tested subset.
