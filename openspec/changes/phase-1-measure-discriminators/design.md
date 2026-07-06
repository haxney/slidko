# Design: phase-1-measure-discriminators

## Context

The protocol universe is deliberately closed (drone/maker bench reality); every core task has a known closed-form solution (docs/DESIGN.md § DSP first). Discriminator algorithms are already derived in docs/ROADMAP.md Phase 1 at HIGH confidence — this design settles module structure and the tuning/eval loop, not the math.

## Goals / Non-Goals

**Goals:**
- ≥99% classification on clean synthetics with zero manual parameters; confidence-honest degradation on dirty ones.
- Generators rich enough that Phase 3 (smoke detector) reuses them unchanged.

**Non-Goals:**
- No decoding (Phase 2 wraps sigrok). No anomaly detection (Phase 3). No general protocol-inference theory — closed list only. No ML anywhere.

## Decisions

- **`tests/synth.py` is program infrastructure, not throwaway** — generators emit `Capture` objects + a `GroundTruth` dataclass label; docs/CORPUS.md `corpus/synthetic/` fixtures are serialized from these same generators (single source of truth for synthetic signals).
- **Discriminator = small pure functions per protocol** (`measure/uart.py`, `measure/i2c.py`, ...) each mapping edge/interval features -> `(claim, confidence)`; a thin `measure/classify.py` decision tree ranks candidates. Keeps the parameter-inference layer cleanly separable (ARCHITECTURE.md requirement).
- **Confidence semantics**: heuristic scores normalized to [0,1] with documented meaning per discriminator (e.g., fraction of frames passing framing check). Doc comments flag empirical/untested thresholds per CLAUDE.md discipline.
- **Eval harness as pytest parametrization** over generator matrix (protocol × params × jitter level); the ≥99% bar is a single aggregated assertion so accuracy regressions fail CI loudly.
- **Baud table + SBUS exceptions as data** (module-level constant tables), not branching logic.

## Risks / Trade-offs

- [Thresholds overfit to clean synthetics] → jitter/glitch sweeps in the eval matrix from day one; corpus entries take over as they arrive (CORPUS.md overfitting guard).
- [CPHA disambiguation via double-decode needs a byte-coherence heuristic] → start with printable/entropy heuristic on synthetic payloads with known answers; mark confidence LOW when both decodes look coherent.
- [CAN full discrimination is heavier than recognition] → v1 requires recognition only (bit-stuffing signature + bitrate table), matching ROADMAP scope.
