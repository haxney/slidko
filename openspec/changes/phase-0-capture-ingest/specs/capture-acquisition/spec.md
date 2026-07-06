# Delta: capture-acquisition

## ADDED Requirements

### Requirement: Timed capture via sigrok-cli subprocess
The Capture layer SHALL orchestrate live acquisition by invoking `sigrok-cli` as a subprocess (`--driver fx2lafw --config samplerate=<rate> --time <ms> -o <out>.sr`), never via in-process libsigrok bindings, producing a .sr file readable by `capture-ingest`.

#### Scenario: Command construction from parameters
- **WHEN** a timed capture is requested with samplerate 24 MHz and duration 500 ms
- **THEN** the constructed sigrok-cli argument list contains exactly the corresponding driver, samplerate, time, and output arguments (verified without executing sigrok-cli)

### Requirement: Clean device and driver error surfacing
Device-enumeration and driver failures from sigrok-cli SHALL surface as typed Python exceptions carrying the underlying stderr text, never as silent empty results or raw CalledProcessError leaks.

#### Scenario: No device connected
- **WHEN** sigrok-cli exits nonzero with a device-not-found message (mocked subprocess)
- **THEN** a typed exception is raised whose message includes the sigrok-cli stderr content

### Requirement: Hardware isolation from the test suite
The wrapper SHALL be a mockable leaf: no test may require actual sigrok-cli execution or attached hardware; all tests run against mocked subprocess boundaries.

#### Scenario: Test suite runs without sigrok installed
- **WHEN** the full pytest suite runs on a machine with no sigrok-cli binary and no capture device
- **THEN** all capture-acquisition tests pass via mocks
