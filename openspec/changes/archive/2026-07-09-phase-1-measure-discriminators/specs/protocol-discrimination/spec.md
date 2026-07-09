# Delta: protocol-discrimination

## ADDED Requirements

### Requirement: Closed-list protocol classification
Measure SHALL classify each channel (or channel group) of a capture against the closed protocol list — UART (+ SBUS/CRSF/SmartAudio/MSP as UART costumes), I²C, SPI, WS2812, PWM/servo, DShot, CAN (recognition), analog video (recognition only) — using hand-derived discriminators over interval/autocorrelation features. No ML; no manual protocol parameter input.

#### Scenario: Headline accuracy on clean synthetics
- **WHEN** the discriminator tree classifies a suite of clean synthetic captures covering every listed protocol
- **THEN** classification accuracy is ≥ 99% with zero manually supplied parameters

#### Scenario: Mixed multi-channel role assignment
- **WHEN** a 4-channel capture carries an I²C pair, a UART line, and a PWM line simultaneously
- **THEN** each channel receives the correct protocol role with no cross-channel contamination

### Requirement: UART auto-baud inference
UART discrimination SHALL infer baud via min/GCD of inter-edge intervals snapped to the standard baud table, treat SBUS (100000, 8E2) via an exception table, detect idle level, and sanity-check start-bit framing.

#### Scenario: Exact on all standard bauds
- **WHEN** auto-baud runs on clean synthetic UART at each standard baud plus SBUS
- **THEN** the inferred baud and frame parameters equal ground truth exactly

#### Scenario: Graceful degradation under jitter
- **WHEN** auto-baud runs on UART with injected jitter beyond clean thresholds
- **THEN** the output reports reduced confidence rather than a wrong baud stated confidently

### Requirement: Per-protocol parameter inference
For each recognized protocol the discriminator SHALL emit the parameters Decode needs: I²C (SDA/SCL role assignment via start/stop structure and SCL periodicity), SPI (clock/CS/data roles, CPOL from idle level, CPHA by decoding both candidates and keeping the coherent one), WS2812/DShot/PWM (signature match against fixed-by-spec timing, not estimation), CAN (bit-stuffing signature + standard bitrate table).

#### Scenario: SPI mode recovery
- **WHEN** SPI synthetic bursts are generated in each of the four CPOL/CPHA modes
- **THEN** the inferred (CPOL, CPHA) matches ground truth in all four cases

#### Scenario: DShot rate recognition by bit timing
- **WHEN** a synthetic DShot capture is generated at DShot150 (bit period 6.67 µs, T0H 2500 ns, T1H 5000 ns), DShot300 (3.33 µs / 1250 ns / 2500 ns), or DShot600 (1.67 µs / 625 ns / 1250 ns) per docs/EXERCISER.md
- **THEN** the discriminator recognizes the correct rate from the interval-histogram signature, zero manual parameters

### Requirement: Numeric confidence on every claim
Every Measure output claim (protocol, role, parameter) SHALL carry a numeric confidence in [0, 1]; downstream layers and tests consume the confidence, not prose hedges.

#### Scenario: Confidence present and machine-readable
- **WHEN** any classification result is serialized
- **THEN** each claim includes a float confidence field
