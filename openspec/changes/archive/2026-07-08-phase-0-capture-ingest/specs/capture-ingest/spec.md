# Delta: capture-ingest

## ADDED Requirements

### Requirement: Read .sr session files into Capture objects
`read_sr(path)` SHALL parse a sigrok session file (zip container: `metadata` in configparser format carrying samplerate, channel names/order, and unitsize; binary chunk files `logic-1-1`, `logic-1-2`, ...) and return a `Capture` holding per-channel numpy bool arrays, samplerate in Hz, and channel names in metadata order.

#### Scenario: Multi-chunk file reassembly
- **WHEN** a .sr file whose logic data spans multiple `logic-1-*` chunks is read
- **THEN** per-channel bit arrays are contiguous across chunk boundaries with no dropped or duplicated samples

#### Scenario: Non-byte-multiple channel counts
- **WHEN** a .sr file with a channel count that is not a multiple of 8 (e.g., 3 channels, unitsize 1) is read
- **THEN** exactly that many channel arrays are returned and padding bits are discarded

### Requirement: Round-trip fidelity with the .sr writer
The package SHALL provide a minimal .sr writer sufficient for synthetic fixtures, and reading a written file SHALL reproduce the input exactly (the fidelity gate applied to our own tooling).

#### Scenario: Bit-exact round trip
- **WHEN** a synthetic per-channel bool array set is written to .sr bytes and read back with `read_sr`
- **THEN** the recovered arrays, samplerate, and channel names are equal to the originals bit-for-bit

### Requirement: Captures carry provenance
A `Capture` SHALL carry provenance metadata — instrument identity, sample rate, and (where known) input threshold voltage — preserved from acquisition through serialization; captures are evidence and must keep their chain of custody.

#### Scenario: Provenance survives round trip
- **WHEN** a Capture with instrument identity and threshold metadata is written and re-read
- **THEN** the provenance fields are intact and unmodified
