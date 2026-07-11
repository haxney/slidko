# Proposal: corpus-tooling

## Why

The bench corpus IS the test suite (one corpus, three consumers: eval harness now, few-shot exemplars at inference, training option preserved). Labeling discipline survives only if it is the path of least resistance — so the capture CLI must write raw capture + receiver verdict + sidecar in one motion. This is the parallel track in docs/ROADMAP.md, specified by docs/CORPUS.md; it starts immediately and Phase 1+ consumes it.

Status note: design.md and tasks.md deferred until pickup; proposal + specs define the contract now.

## What Changes

- Add `corpus/` package: sidecar JSON schema (per docs/CORPUS.md) as validated dataclasses/JSON Schema; storage-layout helpers (`corpus/cells/<cell>/entry-*.sr` + sidecars, `field-gold/`, `synthetic/`).
- Add the capture CLI: run the instrument (via capture-acquisition), prompt for the receiver verdict contemporaneously, write .sr + sidecar in one motion.
- Add the sweep-cell runner: parameterized entry sequences along a cell axis (e.g., cable length), fix-arm variants, producing degradation curves.
- Enforce field-gold holdout: CI check that no threshold/eval tunes against `field-gold/`.

## Capabilities

### New Capabilities

- `corpus-management`: schema-validated corpus entries, one-motion labeled capture, sweep-cell execution, field-gold holdout enforcement.

### Modified Capabilities

(none)

## Impact

- New modules under `src/slidko/corpus/`; consumes capture-acquisition (Phase 0).
- Sidecar schema must support the `referee` field from day one (dual-instrument cells are future work; the schema is not).
- Receiver verdicts are the gold labels — the CLI must make skipping the verdict harder than recording it.
