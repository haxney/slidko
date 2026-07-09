# Proposal: phase-3-smoke-detector

## Why

Analog faults leave digital fingerprints; pure edge-timestamp statistics can DETECT (not diagnose) digital-abstraction contract breaches and trigger the escalation move "smoke -> scope." This is docs/ROADMAP.md Phase 3; the false-positive rate on clean captures is the headline metric.

Status note: design.md and tasks.md deferred until pickup; proposal + specs define the contract now.

## What Changes

- Add edge-math anomaly checks: edge chatter (interval bursts ≪ bit period), runt/glitch pulses (1–2-sample pulses illegal for any symbol), per-protocol timing violations (WS2812 ±150 ns windows as direct numeric checks), protocol incoherence (framing/checksum failures, ACKs from nobody).
- Each detection emits a structured finding: check name, evidence window (sample range), severity, and an escalation suggestion.

## Capabilities

### New Capabilities

- `smoke-detector`: edge-math anomaly detection over captures + decoded events, with structured findings and scope-escalation suggestions.

### Modified Capabilities

(none)

## Impact

- New module under `src/slidko/measure/` (or `measure/smoke.py`); consumes Phase 0 edges, Phase 1 synthetics (dirty variants), Phase 2 decoded events for incoherence checks.
- Detection thresholds are learned parameters with n = this-bench (docs/CORPUS.md overfitting guard); every threshold must be a named constant with a doc comment stating its empirical status.
