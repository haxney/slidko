# Proposal: phase-1-measure-discriminators

## Why

Measure is Slidko's differentiated contribution: "measure it, don't ask" replaces "user, please specify protocol and baud." This is docs/ROADMAP.md Phase 1 (signal auto-identification over the closed drone/maker protocol list), covering docs/TASKS.md items 4 (synthetic generator), 5 (interval statistics), 6 (UART auto-baud), then the discriminator tree.

## What Changes

- Add `tests/synth.py`: in-memory synthetic capture generators with ground-truth labels — UART at arbitrary baud (+ SBUS 100000-8E2), I²C transactions (start/stop/ACK/NAK), SPI bursts (all CPOL/CPHA), WS2812 bit trains (spec-exact and deliberately violated timing), PWM/servo, DShot; parameterized jitter and glitch injection.
- Add `measure/intervals.py`: inter-edge interval histograms, autocorrelation period estimation, dominant-period extraction with confidence.
- Add `measure/uart.py`: auto-baud via min/GCD of inter-edge intervals snapped to the standard baud table (+ SBUS exception), idle-level detection, start-bit framing check, numeric confidence.
- Add the discriminator tree: hand-derived per-protocol discriminators (UART family, I²C, SPI, WS2812, PWM/servo, DShot, CAN recognition, analog-video recognition) with per-channel role assignment on multi-channel captures. Deterministic DSP only — no ML.

## Capabilities

### New Capabilities

- `synthetic-captures`: ground-truth-labeled synthetic edge-stream generation for all Phase 1 protocols, with fault/jitter injection (test infrastructure the whole program consumes; see docs/CORPUS.md `synthetic/`).
- `interval-statistics`: interval histogram / autocorrelation / dominant-period primitives with confidence outputs.
- `protocol-discrimination`: closed-list protocol classification and per-protocol parameter inference (including UART auto-baud), every claim carrying numeric confidence.

### Modified Capabilities

(none)

## Impact

- New modules under `src/slidko/measure/`; substantial test-infrastructure addition under `tests/`.
- Depends on phase-0-capture-ingest (edge extraction, Capture).
- Accuracy bar is part of the spec: ≥99% classification on clean synthetics; graceful confidence degradation under jitter, never a confidently wrong answer.
