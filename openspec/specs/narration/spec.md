# narration

## Purpose

Converts decoded events and smoke findings into diagnostically salient
English assertions — quantitative, protocol-aware, cross-channel, and
individually traceable to evidence — with receiver-rule caveats where
instrument threshold and receiver V_IH diverge.

## Requirements

### Requirement: Diagnostically salient assertions
Narrate SHALL convert decoded events plus smoke findings into English assertions that are quantitative (numbers with units), protocol-aware (I²C addresses resolved against a part-name lookup table), and cross-channel (event coincidences within configurable time windows stated explicitly).

#### Scenario: Address resolution
- **WHEN** decoded events show repeated transactions to I²C address 0x68
- **THEN** the assertion names the address and the matching known-part candidates (e.g., common IMU default address)

#### Scenario: Cross-channel coincidence
- **WHEN** a NAK event and a smoke finding on another channel fall within the coincidence window
- **THEN** a single assertion states both events, their channels, and the time delta

### Requirement: Assertions are evidence-traceable
Every assertion SHALL be individually traceable to evidence: it carries the event indices and/or sample ranges it derives from.

#### Scenario: Trace-back survives serialization
- **WHEN** an assertion set is serialized and reloaded
- **THEN** each assertion's evidence references still index valid events/samples in the source capture

### Requirement: Golden-file evaluation
Narration SHALL be tested by golden files: a corpus or synthetic entry maps to an expected assertion set, compared order-insensitively.

#### Scenario: Golden comparison ignores order
- **WHEN** narration emits the expected assertions in a different order than the golden file
- **THEN** the test still passes; missing or extra assertions still fail

### Requirement: Receiver-rule caveats (the killer case)
When capture metadata indicates the instrument threshold differs materially from the receiver's V_IH, and the receiver verdict (where present) contradicts a clean decode, Narrate SHALL emit an explicit receiver-rule caveat and SHALL NOT assert bus health.

#### Scenario: Clean decode, flickering strip
- **WHEN** a capture decodes cleanly at the 1.4 V instrument threshold but the entry's receiver verdict records "flickered" (5 V WS2812, V_IH ≈ 3.5 V)
- **THEN** the assertion set contains a receiver-rule caveat naming both thresholds and contains no "bus healthy" claim
