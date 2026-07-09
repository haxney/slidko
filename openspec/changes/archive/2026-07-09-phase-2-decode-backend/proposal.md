# Proposal: phase-2-decode-backend

## Why

Measure tells us what a signal is; Decode turns it into events. The sigrok decoder corpus (~150 protocol decoders) is person-years of framing knowledge we wrap rather than rewrite — fed with parameters Measure inferred, which is our contribution. This is docs/ROADMAP.md Phase 2.

Status note: design.md and tasks.md are intentionally deferred until this change is picked up (after Phase 0/1 land); proposal + specs define the contract now.

## What Changes

- Add `decode/backend.py`: backend abstraction — protocol + Measure-inferred parameters + Capture in, normalized timestamped typed events out.
- Add sigrok backend: invoke `sigrok-cli` as a subprocess with inferred decoder options; parse decoder output into the common event schema.
- Add a native UART decoder as the second backend, proving the abstraction with the same test suite.
- Pin the sigrok decoder version; add a decoder-corpus checksum test that fails loudly on unexpected upstream drift.

## Capabilities

### New Capabilities

- `protocol-decode`: backend-abstracted protocol decoding with Measure-parameter feeding, a normalized event schema, and version-pinned sigrok integration.

### Modified Capabilities

(none)

## Impact

- New modules under `src/slidko/decode/`; depends on phase-1 Measure outputs.
- Introduces a runtime dependency on an installed sigrok-cli for the sigrok backend path only; tests use the native backend and mocked subprocess so the suite stays hardware- and sigrok-free.
