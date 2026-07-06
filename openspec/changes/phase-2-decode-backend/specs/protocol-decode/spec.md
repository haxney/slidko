# Delta: protocol-decode

## ADDED Requirements

### Requirement: Backend abstraction with normalized event schema
Decode SHALL define a backend interface taking (Capture, protocol hypothesis, Measure-inferred parameters) and returning events in one normalized schema: timestamped (sample index + seconds), typed (e.g., uart-byte, i2c-start, i2c-addr, i2c-ack/nak, spi-transfer), with payload fields per type. Decoder-specific output formats never leak past the backend boundary.

#### Scenario: Two backends, one test suite
- **WHEN** the same synthetic UART capture is decoded by the sigrok backend and the native UART backend
- **THEN** both produce equivalent normalized event streams passing the identical assertions

### Requirement: Zero-configuration end-to-end decode
Raw synthetic captures SHALL decode with no manual parameters: Measure infers, Decode consumes the inference.

#### Scenario: UART end to end
- **WHEN** a raw synthetic UART capture flows Measure -> Decode
- **THEN** the decoded byte stream equals the generator's ground-truth payload with zero manual configuration

#### Scenario: I²C and SPI end to end
- **WHEN** raw synthetic I²C and SPI captures flow Measure -> Decode
- **THEN** I²C yields correct address + ACK/NAK events and SPI yields correct transfer bytes, zero manual configuration

### Requirement: Pinned decoder corpus with drift detection
The sigrok decoder version SHALL be pinned, and a checksum test over the decoder corpus SHALL fail loudly when upstream content drifts from the pin.

#### Scenario: Upstream drift detected
- **WHEN** the decoder-corpus checksum no longer matches the pinned manifest
- **THEN** the drift test fails with a message naming the changed decoders
