# Proposal: phase-4-narrate

## Why

Narrate is where the defensible value concentrates: flat decoded fields become diagnostically salient assertions ("37 I²C transactions to 0x68 — matches an IMU default address; transaction 38 NAKed, coincident with a rail dip on CH7"). This is docs/ROADMAP.md Phase 4 — the legibility layer of the fidelity->legibility->depth ordering.

Status note: design.md and tasks.md deferred until pickup; proposal + specs define the contract now.

## What Changes

- Add `narrate/`: decoded events + smoke findings + cross-channel alignment -> assertion set with units and quantities.
- Add address -> part-name lookup tables (I²C address book for common maker/drone parts).
- Add event-coincidence detection across channels (time-window alignment).
- Golden-file test harness: corpus/synthetic entry -> expected assertion set, order-insensitive.

## Capabilities

### New Capabilities

- `narration`: evidence-traceable, quantitative English assertions from decoded events + smoke findings, including receiver-rule caveats.

### Modified Capabilities

(none)

## Impact

- New modules under `src/slidko/narrate/`; consumes Phases 0–3 outputs.
- The receiver rule becomes testable product behavior here: a capture that decodes cleanly at instrument threshold but whose receiver verdict is "flickered" must narrate the caveat, not claim "bus healthy" (the killer case from docs/DESIGN.md § The receiver rule).
