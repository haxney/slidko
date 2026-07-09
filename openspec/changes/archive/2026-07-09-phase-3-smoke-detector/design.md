# Design: phase-3-smoke-detector

## Context

Analog faults leave *digital* fingerprints. The smoke detector runs pure
edge-math over Phase 0 edges (and, for incoherence, Phase 2 decoded events) to
DETECT — never diagnose — digital-abstraction contract breaches, then emits the
escalation move **smoke → scope** (docs/DESIGN.md § The smoke detector). The
headline metric is the false-positive rate on clean captures: the detector must
be **silent on every clean entry**. That asymmetry drives every threshold
decision here — when unsure, do not fire.

Sensitivity caveat baked into scope: at 24 MS/s one sample ≈ 41.67 ns, so
ringing above ~10 MHz falls between samples. This is a smoke detector, not a gas
chromatograph; it detects what survives into the edge stream.

## Goals / Non-Goals

**Goals:**
- Four deterministic checks: edge chatter, runt/glitch, timing-window violation,
  protocol incoherence.
- Structured findings with evidence windows that re-run reproducibly.
- Zero findings on the entire clean synthetic suite (asserted, not aspired).

**Non-Goals:**
- No diagnosis (that is Diagnose, Phase 5). No analog reconstruction. No new
  protocol decoding. No ML — every threshold is a named constant with a doc
  comment stating its empirical status (docs/CORPUS.md overfitting guard).

## Decisions

### Finding schema

```python
@dataclass(frozen=True)
class SmokeFinding:
    check: str            # "edge_chatter" | "runt_pulse" |
                          # "timing_violation" | "protocol_incoherence"
    channel: str          # source channel/role
    start_sample: int     # evidence window, inclusive
    end_sample: int
    severity: str         # "info" | "warn" | "smoke"
    summary: str          # human-readable, quantitative, with units
    escalation: str       # "smoke → scope: <what to capture>, expect <X>"
    evidence: dict        # check-specific numbers backing the summary
```

Every finding's `[start_sample, end_sample]` MUST index the source capture such
that re-running the same check on just that slice reproduces the finding
(ROADMAP acceptance: findings traceable to evidence).

### Check 1 — edge chatter

Ringing/slow edges cross threshold multiple times: a burst of toggles whose
inter-edge intervals are far below the established symbol/bit period. Algorithm:
given the channel's edges and the Measure-established bit period `T_bit`,
find runs where ≥ `CHATTER_MIN_EDGES` (default 3) consecutive inter-edge
intervals are each `< CHATTER_FRACTION * T_bit` (default 0.25). The evidence
window spans the burst. Named constants:
```python
CHATTER_FRACTION = 0.25   # EMPIRICAL, n=synthetic-only: intervals below a
                          # quarter of a bit are not legal signaling
CHATTER_MIN_EDGES = 3     # EMPIRICAL: need a burst, not one fast edge
```

### Check 2 — runt / glitch pulses

A pulse (high or low) of 1–2 samples is inconsistent with any legal symbol at
the established rate. Algorithm: any interval between consecutive edges that is
`<= RUNT_MAX_SAMPLES` (default 2) is a runt; its window is the pulse. This is
independent of protocol — no legal maker-bus symbol at ≤ 400 kHz/24 MS/s is
1–2 samples wide. Named constant:
```python
RUNT_MAX_SAMPLES = 2       # EMPIRICAL: 1–2 sample pulses illegal at 24 MS/s
                           # for the v1 protocol universe (≤ ~1 MHz symbol rate)
```

### Check 3 — timing-window violation (WS2812 is the exact case)

WS2812 timing is fixed-by-spec, so violations are a direct numeric check, not an
estimate. Reference physics (WS2812B datasheet; confidence HIGH — long-published
stable numbers), at 24 MS/s where 1 sample = 41.667 ns:

| Symbol | Nominal high time | ± window | Nominal samples | ± samples |
|---|---|---|---|---|
| bit period | 1.25 µs | — | 30.0 | — |
| T0H (0 high) | 0.40 µs | ±150 ns | 9.6 | ±3.6 |
| T1H (1 high) | 0.80 µs | ±150 ns | 19.2 | ±3.6 |

Algorithm: for each WS2812 bit (a high pulse followed by a low), measure the
high-time in samples; classify as 0 if within `T0H ± window`, 1 if within
`T1H ± window`, VIOLATION otherwise. A bit whose high-time falls in neither
window (the ambiguous gap between 13.2 and 15.6 samples, or outside both) is a
timing violation; its window is that bit. Constants derived from the table:
```python
SAMPLE_NS = 1e9 / SAMPLERATE_HZ            # 41.667 ns at 24 MS/s
WS2812_T0H_NS, WS2812_T1H_NS = 400, 800    # datasheet nominal high times
WS2812_WINDOW_NS = 150                      # datasheet ± tolerance
```
Compute the sample windows from these at runtime (do NOT hardcode 9.6/19.2 —
derive from `SAMPLERATE_HZ` so the check follows the capture's actual rate, per
CLAUDE.md's clock-parameterize discipline). The Phase 1 WS2812 generator already
emits spec-exact and deliberately-violated trains with injected-fault labels;
the check must flag exactly the labeled bits (index-for-index).

### Check 4 — protocol incoherence

Decode "succeeding" into garbage. Consumes Phase 2 decoded events:
- **UART:** framing-error rate — fraction of frames whose stop bit is not idle
  level. Fire if `> INCOHERENCE_FRAME_ERR_RATE` (default 0.0 for clean-synth
  gate; the check reports the rate and fires above threshold).
- **I²C:** an ACK/NAK bit present with no preceding addressed device on the bus,
  or a data byte outside any start/stop envelope ("ACKs from nobody").
- Checksum/parity failures where the protocol carries one.

Because the clean-synthetic gate demands zero findings, the default thresholds
are set so a perfectly coherent stream produces none; dirty synthetics (Phase 1
fault injection) push the measured rate above threshold.

### Threshold discipline

Every constant above is a module-level named constant with a doc comment stating
it is EMPIRICAL with n = synthetic/this-bench (docs/CORPUS.md). No magic numbers
inline. Thresholds are tuned so the **clean suite is silent** first; sensitivity
to injected faults is the secondary objective. When corpus entries arrive they
retune these — the constants are the tuning surface.

### Module placement

`src/slidko/measure/smoke.py` (edge-math lives in Measure). It imports Phase 0
edges/intervals and, for check 4, Phase 2 `DecodedEvent`s. A top-level
`run_smoke(capture, hypothesis, events=None) -> list[SmokeFinding]` orchestrates
the four checks.

## Risks / Trade-offs

- [Thresholds overfit to clean synthetics] → the clean-silence assertion runs
  over the WHOLE synthetic matrix from day one; constants are named and
  doc-commented as empirical; corpus retunes later (CORPUS.md overfitting guard).
- [Front-end masking hides fast chatter] → acknowledged in scope; the detector
  reports what reaches the edge stream and never claims completeness.
- [False positives are the cardinal sin] → default constants bias toward silence;
  a check that is unsure does not fire. The FP-rate test is the gate, not a
  nice-to-have.
