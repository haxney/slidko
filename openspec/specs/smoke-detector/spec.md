# smoke-detector

## Purpose

Deterministic edge-math anomaly detection over decoded captures: flags edge
chatter, runt/glitch pulses, per-protocol timing violations, and protocol
incoherence, emitting structured findings with escalation suggestions
("smoke -> scope"). Zero false positives on clean captures is the headline
metric.

## Requirements

### Requirement: Edge-math anomaly checks
The smoke detector SHALL implement, as deterministic edge mathematics: edge-chatter detection (toggle bursts with inter-edge intervals far below the established bit period), runt/glitch detection (1–2-sample pulses inconsistent with any legal symbol at the established rate), per-protocol timing-violation checks (spec windows as numeric bounds), and protocol-incoherence checks (framing/checksum failure rates, ACKs with no addressed device).

#### Scenario: WS2812 window violation exact
- **WHEN** a synthetic WS2812 train contains bits deliberately violating the ±150 ns spec windows
- **THEN** the timing check flags exactly the violated bits (indices match the generator's injected-fault label)

#### Scenario: Chatter burst detection
- **WHEN** a synthetic capture contains injected multi-crossing edge chatter
- **THEN** an edge-chatter finding fires whose evidence window covers the injected burst

### Requirement: Silence on clean captures
On every clean corpus/synthetic entry the detector SHALL emit zero findings — the false-positive rate is the headline metric and is asserted, not aspired to.

#### Scenario: Clean sweep stays silent
- **WHEN** the detector runs across the full clean synthetic suite (all protocols, no injected faults)
- **THEN** zero findings are emitted

### Requirement: Structured findings with escalation
Each detection SHALL emit a structured finding — check name, evidence window (sample range), severity, human-readable summary, and an escalation suggestion ("smoke -> scope: capture this line with an oscilloscope; expect X").

#### Scenario: Finding is traceable to evidence
- **WHEN** any finding is emitted
- **THEN** its evidence window indexes into the source capture and re-running the check on just that window reproduces the finding
