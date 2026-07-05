# The bench corpus

One corpus, three consumers by construction — what gets saved and labeled
today decides which consumers are possible later:

1. **Eval harness (primary, v1):** every entry is a replayable test at each
   pipeline layer — Measure signal ID, Decode parameter selection, smoke-
   detector checks (fire on faults, silent on clean), and end-to-end
   diagnosis. Eval-driven development: build discriminators against the
   corpus, TDD-style.
2. **Few-shot exemplars at inference:** labeled capture→diagnosis pairs
   injected into LLM context sharpen Narrate/Diagnose with zero training.
3. **Training set (deferred option):** if hand-built analog-hardening
   detectors hit their ceiling, this corpus is what a small gradient-boosted
   classifier over hand features would train on. NOT built in v1 — but the
   option is preserved by labeling discipline, which costs nothing now and is
   expensive to retrofit.

## Non-negotiable rules

- **Raw samples, always.** Full-rate LA binaries / scope waveform exports at
  acquisition depth. Never screenshots; never decoded output alone. (The
  fidelity gate applied to our own data.)
- **Gold label = receiver verdicts, not waveform appearance.** Record what
  the far end actually did — servo glitched / device NAKed / strip
  flickered — observed contemporaneously with capture. "Looks noisy/clean"
  labels reproduce the instrument's epistemic error at dataset level. The
  receiver verdict is also exactly the assertion Narrate must learn to emit.
- **Field gold is held out.** Real field captures are never tuned against;
  they are the exam, not the homework.
- **Sweep cells, not samples.** The same link at 1/5/10/30 m yields a
  degradation CURVE: where decode breaks, where the smoke detector first
  fires, where the receiver first errors. Curves tune detector thresholds and
  make evals quantitative. Sweep fix arms too (series-R values, termination,
  differential drive, bus extenders) → matched before/after pairs.

## Overfitting guard

Every hand-tuned detector threshold is a learned parameter with
n = this-bench. Bench conditions are clean, controlled, single-fault; field
conditions are compound-fault, ground-shifted, EMI-soaked. Mitigation:
maximize bench diversity deliberately — bad grounds, cheap PSUs, injected PWM
motor switching noise. How well bench diversity closes the bench→field gap is
the program's central empirical question (MODERATE confidence).

## Reference sweep cells (known-good starting set)

- **WS2812 long-run signal integrity:** data line over long UTP/Cat6 runs at
  800 kHz. Intra-bit reflection superposition (one-way delay ~5 ns/m vs.
  1.25 µs bit period) produces sawtooth/stairstep distortion. Fix arms:
  330–470 Ω series R at the driver, level shifting, differential driving
  over a twisted pair (resolves completely), shorter/slower. A representative
  field case with before/after captures exists as a template; the fault class
  is trivially reproducible with a cable spool — arguably better than field
  data (controllable length/termination sweep).
- **I²C over-capacitance:** long Cat6 runs blow the ~400 pF bus budget
  (~50 pF/m ⇒ ~30 m ≈ 1500 pF ≈ 4× over) — a guaranteed, controllable
  generator of analog-hardening signatures: RC-rounded edges, rise-time spec
  violations (300/1000 ns limits), eventual NAKs. Canonical fix arm:
  P82B715-class bus extender; stronger pull-ups as the crude version.
- **Level-mismatch (the receiver-rule cell):** 3.3 V driver into a 5 V
  WS2812 strip — the instrument decodes clean, the strip glitches. The single
  most important entry class in the corpus: it labels the primary
  instrument's own blind spot.

## Per-entry metadata schema (JSON sidecar)

```json
{
  "id": "cell-ws2812-cat6-len/entry-0042",
  "capture_file": "entry-0042.sr",
  "instrument": {"model": "fx2lafw-clone", "samplerate_hz": 24000000,
                  "threshold_v": 1.4, "channels": {"0": "DATA", "7": "SYNC"}},
  "driver": {"chip": "...", "vdd_v": 3.3, "series_r_ohm": 0},
  "transport": {"cable": "cat6-utp", "length_m": 10, "twisted": true,
                 "shielded": false, "termination": "none"},
  "receiver": {"part": "WS2812B", "vdd_v": 5.0, "vih_v": 3.5},
  "protocol": {"name": "ws2812", "nominal": {"bitrate_hz": 800000}},
  "fault_injected": {"class": "level-mismatch", "params": {}},
  "receiver_verdict": {"observed": "flicker", "notes": "...",
                        "contemporaneous": true},
  "sweep_cell": {"name": "ws2812-cat6-len", "axis": "length_m", "value": 10},
  "referee": null
}
```

`referee` is reserved for dual-instrument capture cells (a second,
adjustable-threshold instrument capturing the same bus at the receiver's real
V_IH, labeling what the primary instrument missed). Planned for the
analog-hardening era; schema-supported from day one.

## Storage layout

```
corpus/
  cells/<cell-name>/
    cell.json            # sweep-cell definition: axis, fixture, fix arms
    entry-*.sr           # raw captures
    entry-*.json         # sidecars (schema above)
  field-gold/            # held out; CI enforces no threshold tuned against it
  synthetic/             # generated fixtures used by unit tests
```

Corpus tooling to build: a capture CLI that runs the instrument, prompts for
the receiver verdict, and writes the sidecar in one motion — labeling
discipline survives only if it is the path of least resistance.
