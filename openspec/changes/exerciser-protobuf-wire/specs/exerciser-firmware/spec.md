# Delta: exerciser-firmware

## REMOVED Requirements

### Requirement: JSON-lines command interface
**Reason**: Replaced by a committed protobuf schema. JSON's implicit typing
admits silent cross-language ambiguity (e.g. a bare number read as int on one
side and float on the other), fails open on unknown/missing fields, and forced
binary `payload` to be carried as a C string — corrupting any `0x00`/`"` byte
(a documented gap in `firmware/src/main.c`). A canonical `.proto` forbids these
by construction and gives field-numbered schema evolution.
**Migration**: Firmware and host speak length-delimited protobuf per the new
"Protobuf command interface" requirement; the v1 command set and the
`id`-echo / `ok|err` contract are preserved unchanged — only the encoding
differs. `protoc --decode`/`--decode_raw` recovers human-readable wire dumps.

## ADDED Requirements

### Requirement: Protobuf command interface
The firmware SHALL speak length-delimited protobuf over USB CDC serial,
generated from a single canonical `.proto` shared by firmware and host. Each
command SHALL be a `Command { uint32 id; oneof body { … } }` carrying an `id`;
each reply SHALL be a `Response { uint32 id; oneof body { … } }` echoing that
`id` with an `ok` or `err` variant. Framing SHALL be a fixed 2-byte
little-endian length prefix, with NO application-layer CRC (USB bulk transfer
already guarantees integrity and in-order delivery). The v1 command set is
`info`, `ws2812`, `dshot`, `pwm`, `uart_tx` (incl. SBUS-style frames),
`i2c_scan`, `i2c_read`, `spi_tx`, `sync`, `loopback` per docs/EXERCISER.md
parameter shapes; binary fields (`uart_tx`/`spi_tx` `payload`) SHALL be proto
`bytes`.

#### Scenario: Response echoes id
- **WHEN** any valid command with `id = 42` is decoded and dispatched
- **THEN** the encoded response carries `id = 42` with an `ok` or `err` variant (verified by an encode/decode round-trip in a native or host-side harness, no hardware)

#### Scenario: Single schema, two languages
- **WHEN** a `Command` is encoded by the generated Python bindings and decoded by the generated firmware (nanopb) code, and vice versa
- **THEN** both sides recover identical field values (a cross-language golden round-trip, no hardware)

#### Scenario: Binary payload survives round-trip
- **WHEN** a `uart_tx`/`spi_tx` command carries a `payload` containing `0x00` and `0x22` (`"`) bytes
- **THEN** the decoded payload bytes and length match the input exactly

### Requirement: Typed response payloads
Read-style command results SHALL be carried as typed fields on the wire, not
dropped: `i2c_scan` SHALL return the responding addresses, `i2c_read` SHALL
return the read bytes, and `info` SHALL return firmware version, clock,
detected stepping, E9 posture, and a repeated capability list. Error replies
SHALL carry a typed `ErrorReason` enum (`PARSE_ERROR`, `UNKNOWN_COMMAND`,
`E9_UNAVAILABLE`, `HAZARD_VIOLATION`), not a free-form string.

#### Scenario: i2c_scan returns addresses
- **WHEN** an `i2c_scan` completes with responders at 0x68 and 0x76 (simulated in the protocol harness)
- **THEN** the `Response` carries both addresses in its repeated address field

#### Scenario: Error reason is a typed enum
- **WHEN** a push-pull command arrives without the believed-undriven assertion
- **THEN** the `Response` err variant carries `ErrorReason = HAZARD_VIOLATION`

#### Scenario: Info advertises silicon-aware capabilities
- **WHEN** `info` runs on A2 and on A4 configurations (simulated in the harness)
- **THEN** the `Response` info variant reports stepping + E9 posture, and the capability list differs exactly in the input-sensing entries

### Requirement: Schema-generated protocol layer
The firmware and host protocol code SHALL be generated from the canonical
`.proto` at build time (nanopb for firmware C, protobuf for the Python host).
The generated firmware protocol layer SHALL include NO pico-sdk headers so it
stays host-unit-testable, and codegen SHALL run headlessly in CI with an open
toolchain (no account-walled or Windows-only tools).

#### Scenario: Codegen runs headless in CI
- **WHEN** CI builds the firmware and Python jobs from a clean checkout
- **THEN** both generate their bindings from the `.proto`, and the native protocol tests compile and pass without attached hardware

#### Scenario: Protocol layer stays SDK-free
- **WHEN** the generated firmware protocol sources and the dispatch adapter are compiled by the host `cc` for the native test build
- **THEN** they build and link with no pico-sdk / `hardware/*.h` / `tusb.h` include
