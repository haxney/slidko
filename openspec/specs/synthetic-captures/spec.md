# synthetic-captures

## Purpose

Ground-truth-labeled synthetic edge-stream generation for every Phase 1
protocol (UART/SBUS, I²C, SPI, WS2812, PWM/servo, DShot), with deliberate
fault/jitter injection. This is the program's test infrastructure — the
whole discriminator suite is evaluated against these generators — and the
single source of truth that `corpus/synthetic/` fixtures are serialized
from (see docs/CORPUS.md).

## Requirements

### Requirement: Ground-truth-labeled protocol generators
The test infrastructure SHALL generate in-memory edge streams / bit arrays with known ground truth for: UART frames at arbitrary baud including SBUS (100000 baud, 8E2), I²C transactions (start/stop, address, ACK/NAK structure), SPI bursts (all four CPOL/CPHA modes), WS2812 bit trains, PWM/servo pulses, and DShot frames. Every generated capture SHALL carry a machine-readable ground-truth label (protocol, parameters, payload).

#### Scenario: Generator output is self-describing
- **WHEN** any generator produces a capture
- **THEN** its ground-truth label contains the protocol name and all parameters needed to verify a discriminator's answer without re-deriving them

#### Scenario: WS2812 spec-exact timing
- **WHEN** the WS2812 generator runs at 24 MS/s with spec-exact timing
- **THEN** bit cells encode 800 kHz (~30 samples/bit) with high/low durations inside the ±150 ns spec windows

### Requirement: Deliberate fault and jitter injection
Generators SHALL support parameterized corruption — timing jitter, glitch/runt pulse insertion, WS2812 timing-window violations, framing errors — with the injected faults recorded in the ground-truth label (the smoke detector's tests consume dirty synthetics).

#### Scenario: Injected violation is labeled
- **WHEN** a WS2812 train is generated with a deliberate timing-window violation
- **THEN** the label records the violation class and the affected bit indices

### Requirement: Hardware-free and deterministic
Generation SHALL be pure in-memory computation, seedable for exact reproducibility, requiring no hardware, files, or network.

#### Scenario: Seeded reproducibility
- **WHEN** the same generator runs twice with the same seed and parameters
- **THEN** outputs are bit-identical
