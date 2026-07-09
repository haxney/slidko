# Tasks: phase-3-smoke-detector

> Prerequisite: `dev-tooling-gate` applied. Consumes Phase 0 edges/intervals,
> Phase 1 synthetic generators (dirty variants + injected-fault labels), and
> Phase 2 `DecodedEvent`s for the incoherence check. TDD from the spec scenario.
> The headline gate is **zero findings on the clean suite** — write that test
> early and keep it green. End every group with `make check`.

## 1. Finding schema

- [x] 1.1 Write failing tests in `tests/measure/test_smoke_finding.py`: `SmokeFinding` frozen dataclass with `check, channel, start_sample, end_sample, severity, summary, escalation, evidence`; severity ∈ {info, warn, smoke}
- [x] 1.2 Implement `SmokeFinding` in `src/slidko/measure/smoke.py` per design.md; tests green

## 2. Edge chatter check

- [x] 2.1 Write failing test: a clean square wave / clean protocol capture yields NO chatter finding; a capture with injected multi-crossing chatter (Phase 1 glitch injection) yields a finding whose window covers the injected burst
- [x] 2.2 Implement `detect_edge_chatter(edges, t_bit, channel)` using `CHATTER_FRACTION`/`CHATTER_MIN_EDGES` named constants (doc-commented EMPIRICAL) per design.md; tests green

## 3. Runt / glitch check

- [x] 3.1 Write failing test: clean captures yield no runt finding; a capture with an injected 1–2-sample glitch yields a runt finding windowed on the glitch
- [x] 3.2 Implement `detect_runt_pulses(edges, channel)` using `RUNT_MAX_SAMPLES`; tests green

## 4. WS2812 timing-window violation (exact)

- [ ] 4.1 Write failing test using the Phase 1 WS2812 generator: a spec-exact train yields no timing finding; a train with deliberately violated bits flags EXACTLY the injected-fault bit indices (index-for-index against the generator's fault label)
- [x] 4.2 Implement `detect_ws2812_timing(edges, samplerate_hz, channel)`: derive T0H/T1H ± windows in samples from `WS2812_T0H_NS=400`, `WS2812_T1H_NS=800`, `WS2812_WINDOW_NS=150` and the capture samplerate (do NOT hardcode sample counts); a bit whose high-time falls in neither window is a violation; tests green
- [ ] 4.3 Verify exactness: assert the flagged bit set equals the injected-fault set with no extras and no misses

## 5. Protocol incoherence check

- [ ] 5.1 Write failing tests: coherent Phase 2 UART/I²C event streams yield no incoherence finding; a stream with injected framing errors (UART stop-bit violations) and an I²C "ACK from nobody" (ack event with no preceding addressed device) each yield a finding
- [ ] 5.2 Implement `detect_incoherence(events, hypothesis)` computing framing-error rate (UART) and orphan-ack detection (I²C) with `INCOHERENCE_FRAME_ERR_RATE` named constant; tests green

## 6. Orchestrator + the false-positive gate (headline)

- [ ] 6.1 Implement `run_smoke(capture, hypothesis, events=None) -> list[SmokeFinding]` running all four checks
- [ ] 6.2 Write the headline test: run `run_smoke` across the FULL clean synthetic suite (every protocol, no injected faults, swept over the generator's parameter matrix) and assert **zero findings total**. This is the false-positive gate; it must be green
- [ ] 6.3 Write the complementary test: every dirty synthetic with an injected fault produces at least one finding of the expected `check` type
- [ ] 6.4 Write the traceability test: for any emitted finding, re-running the same check on just `capture[start_sample:end_sample+1]` reproduces the finding

## 7. Structured findings + escalation

- [ ] 7.1 Write failing test: every finding carries a non-empty `escalation` string of the form `smoke → scope: ...` and an `evidence` dict with the numbers backing `summary`
- [ ] 7.2 Ensure each check populates `severity`, `summary` (quantitative, with units), `escalation`, and `evidence`; tests green

## 8. Wrap-up

- [ ] 8.1 `make check` green; the false-positive gate (6.2) and exactness test (4.3) both pass
- [ ] 8.2 Print the clean-suite finding count (must be 0) in test output for the record; commit naming the task groups
