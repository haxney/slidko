# Roadmap

Phases are sequential on the critical path; the corpus/exerciser track runs
in parallel. Every acceptance criterion is a testable assertion — write it as
a pytest before building the feature.

## Phase 0 — Capture ingest & edge extraction

Scope: read captures into numpy; extract edge timestamps.

- .sr reader: open a sigrok session file (zip container), parse `metadata`
  (configparser format: samplerate, channel names/order, unit size), unpack
  `logic-1-*` binary chunks into per-channel bit arrays.
- Edge extraction: rising/falling edge timestamps per channel from bit arrays
  (vectorized: `np.diff` on the bit array; nonzero indices; sign gives
  polarity).
- sigrok-cli subprocess wrapper: timed capture from an fx2lafw device
  (`--driver fx2lafw --config samplerate=24m --time <ms> -o out.sr`),
  device-enumeration errors surfaced cleanly.

Acceptance:
- Round-trip: synthetic bit array → packed .sr-format bytes → reader →
  identical bit array.
- Edge extractor on a synthetic 1 kHz square wave at 24 MS/s yields intervals
  of 12,000 samples ± 0, correct polarity alternation.
- Reader handles multi-chunk .sr files and non-8-multiple channel counts.

## Phase 1 — Measure: the discriminator tree

Scope: signal auto-identification over a closed protocol list. The
drone/maker protocol universe is short: UART (+ costumed variants: SBUS,
CRSF, SmartAudio, MSP), I²C, SPI, WS2812, PWM/servo, DShot, CAN, analog
video (recognition only). ~8 hand-derivable discriminators built from
`numpy.histogram` / `numpy.diff` / `scipy.signal.find_peaks` /
autocorrelation. No general protocol-inference theory needed.

Per-protocol parameter inference (all HIGH confidence, previously derived):

- **I²C:** ~zero parameters (self-clocking). Start/stop conditions are
  structurally unique (SDA transitions while SCL high). SDA-vs-SCL
  discrimination: SCL shows regular periodicity; SDA transitions while SCL is
  low.
- **UART:** baud = min/GCD of inter-edge intervals, snapped to the standard
  baud table; frame = 8N1 default with a lookup table of exceptions (SBUS =
  100000-8E2, etc.). Idle-high line, start-bit framing check.
- **SPI:** clock = the bursty-but-regular line; CS = the line that frames
  bursts; CPOL from clock idle level; CPHA by decoding both candidates and
  keeping the coherent one; data lines transition on clock edges.
- **WS2812 / DShot / PWM:** fixed-by-spec timing → recognition via interval-
  histogram signature match, not estimation. WS2812 reference physics for
  tests: 800 kHz bit rate, ±150 ns spec windows; at 24 MS/s that is ~42 ns
  per sample and ~30 samples per bit — comfortably resolvable.
- **CAN:** bit-stuffing signature + standard bitrate table.

Acceptance:
- Discriminator tree classifies synthetic captures of every listed protocol
  at ≥99% accuracy with zero manual parameters.
- UART auto-baud is exact on all standard bauds plus SBUS, at SNR-clean
  synthetic streams; degrades gracefully (reports confidence, not a wrong
  answer) under injected jitter.
- Every Measure output claim carries a numeric confidence.
- Mixed multi-channel captures (e.g., I²C pair + UART + PWM on 4 channels)
  get per-channel role assignments with no cross-contamination.

## Phase 2 — Decode

Scope: wrap the sigrok decoder corpus behind `decode/backend.py`; feed it
Measure-inferred parameters; normalize decoder output into a common event
schema (timestamped, typed events).

Acceptance:
- End-to-end: raw synthetic UART capture → Measure → Decode → correct byte
  stream, zero manual configuration.
- Same for I²C (address + ACK/NAK events) and SPI.
- Backend abstraction proven by a second trivial backend (native UART
  decoder) passing the same tests.
- Decoder version pinned; a decoder-corpus checksum test fails loudly on
  unexpected upstream drift.

## Phase 3 — The smoke detector

Scope: edge-math anomaly checks — edge chatter, runt/glitch pulses, timing
violations (per-protocol spec windows), protocol incoherence (framing/
checksum failures, ACKs from nobody).

Acceptance:
- Fires on corpus/synthetic entries with injected faults; **silent on every
  clean entry** (false-positive rate is the headline metric).
- WS2812 timing-window violation detection exact against spec numbers.
- Each detection emits a structured finding with an escalation suggestion
  ("smoke → scope") and the evidence window.

## Phase 4 — Narrate

Scope: decoded events + smoke findings + cross-channel alignment →
diagnostically salient assertions (address → part-name lookup tables;
event-coincidence detection; quantitative statements with units).

Acceptance:
- Golden-file tests: corpus entry → expected assertion set (order-
  insensitive).
- Assertions are individually traceable to evidence (event indices/sample
  ranges).
- The known killer case narrates correctly: a capture that decodes cleanly at
  the instrument threshold but whose receiver verdict is "flickered" produces
  an explicit receiver-rule caveat, not a false "bus healthy."

## Phase 5 — Diagnose, the librarian, the poke loop

Scope: LLM integration (structured instruction schema with citation
enforcement — see ARCHITECTURE.md), librarian document retrieval, config-pull
first layer, the conversational loop.

Acceptance:
- Schema validation rejects any pad-level claim without a citation or
  explicit unknown flag (unit-testable without an LLM: validate against
  canned outputs).
- Fault-tree ordering respected: config-pull suggestions precede probe
  instructions for symptoms with known config causes.
- Hazard notes present on every exercise instruction; accessibility filter
  enforced (no fine-pitch IC-pad probing instructions).
- End-to-end scripted scenario: seeded symptom + corpus capture → plausible
  next-poke instruction, evaluated against a rubric.

## Parallel track — bench corpus & exerciser firmware

- Corpus tooling per CORPUS.md (capture + sidecar-metadata CLI, sweep-cell
  runner) — starts immediately; Phase 1+ consumes it.
- Exerciser firmware per EXERCISER.md — needed by the time sweep cells run;
  RP2040 acceptable initially with clock-parameterized timing constants
  (133→150 MHz migration must be a config change).
- Dual-instrument capture cells (reference instrument as corpus referee) are
  planned for the analog-hardening era; the metadata schema supports them
  from day one.

## Explicitly out of scope for v1

Pod code; ML training; scope integration beyond human-relayed escalation;
DUT writes of any kind; photo/vision intake; support for capture hardware
beyond fx2lafw-class + the exerciser.
