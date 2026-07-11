# Proposal: exerciser-protobuf-wire

## Why

The exerciser command interface is JSON-lines over USB CDC with a hand-rolled
scanner (`firmware/src/protocol/parser.c`). JSON's schema is *implicit*, and
that lets whole classes of silent bug in: nothing forbids a bare number being
read as an int on one side and a float on the other, unknown/missing fields
fail open, and the parser reads binary `payload` as a C string so any `0x00`
or `"` byte in a UART/SPI payload corrupts it (a documented gap — see
`firmware/src/main.c` header). A committed `.proto` makes the wire contract
explicit and typed: those ambiguities are forbidden by construction, not
caught by convention. It also gives controlled, field-numbered schema
evolution and a single source of truth shared by the C firmware, the
(greenfield) Python host client, and — later — the Rust pod control plane.
`protoc --decode`/`--decode_raw` preserves wire debuggability.

Scope is the exerciser **control plane only**. The pod data-plane firehose is
out of scope (guardrail 1), but its serialization rationale is recorded in
design.md so the `bytes samples` / in-place-construction decision is not
relitigated when the pod is finally built.

## What Changes

- **BREAKING (wire):** replace JSON-lines with **length-delimited protobuf**
  over USB CDC. A canonical `.proto` is the single source of truth. Device:
  **nanopb** (static allocation, plain C — preserves the `protocol/`
  no-pico-sdk, host-testable property). Host: generated Python bindings.
- Envelope: `Command { uint32 id; oneof body { ... } }` and
  `Response { uint32 id; oneof body { Ok | Error | ... } }`. Every command
  still carries `id`; every response still echoes it with an `ok`/`err`
  variant — the existing contract is preserved, only the encoding changes.
- **Fold read results into the wire schema** (closes the `main.c` gap):
  `i2c_scan` → repeated address, `i2c_read` → `bytes` data, `info` → repeated
  capability + stepping/E9 posture. Error `reason` becomes an
  `enum ErrorReason` (`PARSE_ERROR`, `UNKNOWN_COMMAND`, `E9_UNAVAILABLE`,
  `HAZARD_VIOLATION`) — no more free-form strings.
- `uart_tx`/`spi_tx` `payload` becomes proto `bytes` — fixes the
  binary-as-C-string corruption.
- Framing: a fixed **2-byte little-endian length prefix** (messages are small
  and bounded; no varint even for the length). USB bulk transfer already
  guarantees integrity and in-order delivery, so **no application-layer CRC**.
- Build: generate nanopb C and Python from the `.proto` at configure time; CI
  runs codegen headlessly (nanopb's generator is a Python script — open
  toolchain, no account-walls).

## Capabilities

### Modified Capabilities

- `exerciser-firmware`: the JSON-lines command interface is replaced by a
  protobuf command interface with typed response payloads and
  schema-generated protocol code.

## Impact

- `firmware/src/protocol/parser.c` (hand-rolled JSON) is retired, replaced by
  generated nanopb + a thin dispatch adapter. `test_protocol.c` is rewritten
  to assert encode/decode round-trips instead of JSON substring matches. The
  E9, hazard, timing, and capability logic is untouched — this change swaps
  the codec, not the policy.
- New build dependency: the nanopb generator (`nanopb_generator.py`) and its
  runtime (`pb_encode.c`/`pb_decode.c`/`pb_common.c`, vendored like the SDK).
  Open, headless, CI-friendly.
- The greenfield Python host codec is built against the generated bindings and
  **layered** (protobuf decode → length framing → transport adapter) so the
  same schema + framing serve the future pod control plane — only the bottom
  transport swaps (pyserial CDC ↔ pyftdi FIFO). See ARCHITECTURE.md § Deferred.
- docs/EXERCISER.md and the `exerciser-firmware` spec's command-interface
  requirement are updated JSON → protobuf.
- No hardware dependency; every protocol-layer test stays host-native, plus a
  cross-language (C ↔ Python) golden round-trip that locks the contract.
