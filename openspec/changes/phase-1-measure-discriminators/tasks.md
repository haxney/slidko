# Tasks: phase-1-measure-discriminators

## 1. Synthetic generator core (tests/synth.py)

- [x] 1.1 Define `GroundTruth` label dataclass (protocol, parameters, payload, injected_faults, seed) + generator base returning `(Capture, GroundTruth)`
- [x] 1.2 UART generator: arbitrary baud, 8N1 + parameterized frames, SBUS (100000-8E2); test asserting frame timing against baud ground truth
- [x] 1.3 I²C generator: start/stop conditions, addresses, ACK/NAK; test asserting SDA-transitions-while-SCL-high only at start/stop
- [x] 1.4 SPI generator: all four CPOL/CPHA modes, CS framing; per-mode timing tests
- [x] 1.5 WS2812 generator: spec-exact 800 kHz cells at 24 MS/s; test asserting ±150 ns windows honored
- [ ] 1.6 PWM/servo and DShot generators with ground-truth pulse widths / frame values
- [ ] 1.7 Jitter + glitch/runt + WS2812-violation injection, faults recorded in labels; seeded-reproducibility test (same seed -> bit-identical)

## 2. Interval statistics (measure/intervals.py)

- [ ] 2.1 Failing tests: square-wave histogram single-cluster; known-period autocorrelation recovery (exact, confidence ≥ 0.9); jitter degrades confidence not correctness
- [ ] 2.2 Implement histograms, autocorrelation period estimation, dominant-period + periodicity-strength helpers with [0,1] confidence; tests green
- [ ] 2.3 Test SCL-vs-SDA periodicity separation on I²C synthetics; green

## 3. UART auto-baud (measure/uart.py)

- [ ] 3.1 Failing tests: exact inference on every standard baud + SBUS; idle-level detection; start-bit framing check; jitter -> reduced confidence never wrong-but-confident
- [ ] 3.2 Implement min/GCD interval estimation snapped to baud table (+ SBUS exception table as data); tests green

## 4. Per-protocol discriminators

- [ ] 4.1 I²C: start/stop structural detection, SDA/SCL role assignment; tests from generator ground truth
- [ ] 4.2 SPI: clock/CS/data role assignment, CPOL from idle, CPHA via coherent double-decode; all-four-modes test green
- [ ] 4.3 WS2812 / DShot / PWM: interval-histogram signature match against fixed-by-spec timing tables
- [ ] 4.4 CAN recognition: bit-stuffing signature + standard bitrate table (recognition only)
- [ ] 4.5 Analog-video recognition stub per ROADMAP scope (recognize, never decode)

## 5. Classifier tree + eval harness

- [ ] 5.1 `measure/classify.py`: rank candidates per channel from discriminator scores; per-channel role output with confidences
- [ ] 5.2 Eval matrix test (protocol × params × jitter): aggregated ≥99% accuracy assertion on clean synthetics, zero manual parameters
- [ ] 5.3 Mixed 4-channel capture test (I²C pair + UART + PWM): correct roles, no cross-contamination
- [ ] 5.4 Serialization test: every emitted claim carries a float confidence in [0,1]

## 6. Wrap-up

- [ ] 6.1 `ruff check .`, `ruff format --check .`, full `pytest` green; eval accuracy printed in test output for the record
