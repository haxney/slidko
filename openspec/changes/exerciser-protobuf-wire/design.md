# Design: exerciser-protobuf-wire

## Context

The exerciser speaks JSON-lines over USB CDC (`firmware/src/protocol/`,
docs/EXERCISER.md). The host half does not exist yet — on the Python side
`"exerciser"` is only an *executor label* in `diagnose/instruction.py`; there
is no serial client. So this is less a migration than a chance to commit a
typed wire contract before the host client is written against it.

The channel is a **trickle**: one command → one response, at diagnostic-loop
("probe here next") cadence, payloads ≤64 bytes, over USB CDC (~1 MB/s
effective). Wire efficiency is irrelevant here; varint-vs-fixed is noise at
this volume. The value of a schema is entirely in **removing ambiguity and
enabling controlled evolution**, not in bytes saved.

This design decides: (1) the serialization (protobuf/nanopb) and why, over the
alternatives the exploration weighed; (2) the message shape; (3) framing; and
(4) the forward-looking rationale for the deferred pod data plane, recorded
here so the `bytes` decision is not relitigated later.

## Goals / Non-Goals

**Goals:**
- One canonical `.proto` as the single source of truth for firmware + host.
- Preserve the `id`-echo / `ok|err` contract and the v1 command set exactly.
- Fold read-command results (`i2c_scan`/`i2c_read`/`info`) onto the wire and
  make the error reason a typed enum.
- Keep the generated protocol layer free of pico-sdk headers so it stays
  host-unit-testable; codegen runs headless in CI.
- A cross-language (C ↔ Python) golden round-trip that locks the contract.

**Non-Goals:**
- **No pod code** (guardrail 1). The data-plane firehose serialization is out
  of scope; its rationale is recorded below as forward context only.
- No wire-efficiency optimization — the control channel does not need it.
- No new host serial *transport* (pyserial/pyftdi wiring) beyond the codec and
  its hardware-free round-trip tests; the transport adapter lands with the
  host client work, layered so the schema/framing above it are reused.

## Decisions

### Serialization: protobuf via nanopb

nanopb is the mature embedded protobuf: static allocation (no malloc),
generates plain C, and its generator is a Python script that plugs into CMake
— open, headless, no account-walls (clears the CLAUDE.md toolchain bar). The
generated `protocol/` code depends only on `pb_encode.c`/`pb_decode.c`, never
on pico-sdk headers, so it keeps the load-bearing host-testability property of
the existing `protocol/`↔`hw/` split.

The `.proto` is the **lingua franca across the three toolchains this project
will actually have**: nanopb (C, exerciser) → prost (Rust, deferred pod) →
protobuf (Python, host). The reused artifact is the *schema plus the host
codec*, not firmware C (the pod is Rust). Hand-maintained packed structs would
force re-maintaining the layout in C **and** Rust **and** Python; the IDL is
what makes the reuse real. Casting received bytes into structs is explicitly
rejected — endianness/versioning footgun with no schema enforcement.

The migration is near-mechanical: the flattened `command_t` (`command.h`) is
already a proto message-set collapsed into a C union; each command → a message,
`cmd` → a `oneof` tag.

On the varint objection: at this volume it is a non-issue, but it is also
avoidable by field-type choice (`fixed32` etc.) and does not appear on the
data plane at all (see below). It is not a reason to pick a different format.

### Message shape

A `oneof` envelope per direction, mirroring the existing dispatcher:

```proto
message Command {
  uint32 id = 1;
  oneof body { Info info = 2; Ws2812 ws2812 = 3; Dshot dshot = 4;
               Pwm pwm = 5;   UartTx uart_tx = 6; /* … i2c/spi/sync/loopback */ }
}
message Response {
  uint32 id = 1;
  oneof body { Ok ok = 2; Error error = 3;
               I2cScanResult scan = 4; I2cReadResult read = 5; Info info = 6; }
}
enum ErrorReason { PARSE_ERROR = 0; UNKNOWN_COMMAND = 1;
                   E9_UNAVAILABLE = 2; HAZARD_VIOLATION = 3; }
```

- `payload` fields (`uart_tx`, `spi_tx`) are proto `bytes` — this alone fixes
  the binary-as-C-string bug in `parser.c`.
- Read results become typed fields: `I2cScanResult { repeated uint32 addr }`,
  `I2cReadResult { bytes data }`, `Info { … repeated Capability caps }`. This
  closes the documented `main.c` gap where read commands executed but their
  results were dropped from the `response_t` (id/status/reason only).
- `ErrorReason` replaces the free-form `err_reason` string — the host switch
  becomes exhaustive and typo-drift is impossible.

### Framing

protobuf is not self-delimiting, so a stream needs framing. **Fixed 2-byte
little-endian length prefix** (messages are small and bounded; a u16 covers
any v1 message). Deliberately *not* nanopb's `pb_encode_delimited` varint
length — a fixed prefix keeps the payload offset trivial and honors the
no-varint preference even for the length.

**No application-layer CRC.** Both this link (TinyUSB CDC) and the future pod
(FT232H) are USB; USB bulk transfer carries a per-packet 16-bit CRC with
hardware retransmit and guarantees in-order delivery. On-wire byte loss is not
a realistic failure mode, unlike a raw UART. Resync-on-reconnect is handled by
the length prefix. (This corrects an earlier worry that binary framing would
need a CRC + resync layer — true over a bare UART, not over USB.)

### Host codec layering

The host client is layered so only the bottom swaps between the exerciser and
the deferred pod control plane:

```
   ┌─────────────────────────────┐
   │ protobuf decode (generated) │  ← shared, from the .proto
   ├─────────────────────────────┤
   │ length-delimit framing      │  ← shared
   ├─────────────────────────────┤
   │ transport adapter           │  ← the ONLY thing that differs:
   │  pyserial (CDC) | pyftdi     │     exerciser & pod-control = pyserial (CDC)
   └─────────────────────────────┘     pod-data = pyftdi (FT232H FIFO)
```

This change lands the top two layers + a stub/mock transport for tests; the
real transport adapter arrives with the host-client work.

## Deferred: pod data-plane serialization (record, do not build)

Recorded so the future pod does not relitigate this. **Not in scope of this
change** (guardrail 1).

The pod is already two ports by design (ARCHITECTURE.md): a **control plane**
on the RP2350's native USB CDC (same transport as the exerciser — the schema
here transfers directly) and a unidirectional **data-plane firehose**,
PIO→DMA→FT232H in FT245 sync FIFO mode (~35–40 MB/s), host-read via
libftdi/pyftdi (not a CDC serial port).

**One format across the whole system.** The firehose stays protobuf too — the
lever is *granularity*, not format: one `CaptureBlock` message per ~64 KB
block with samples as an opaque `bytes` field, not per-sample encoding.

```proto
enum SampleEncoding { RAW_8CH = 0; RLE = 1; }
message CaptureBlock {
  uint32 seq = 1; uint64 t0_ns = 2; uint32 sample_rate_hz = 3;
  uint32 channel_mask = 4; SampleEncoding enc = 5;
  bytes samples = 6;   // opaque BECAUSE the typed header describes it
}
```

**Why `bytes`, not a `repeated` field** (the recurring future objection). For
a fixed-width, byte-granular sample stream (8 channels → 1 byte/sample →
24 MS/s → 24 MB/s per the ARCHITECTURE.md gate), `bytes` is not a discipline
failure — it is the *correct* model. Every proto encoding of "packed byte
samples" is strictly worse or impossible:

| Field type | bytes/sample | throughput | CPU/sample | verdict |
|---|---|---|---|---|
| `bytes samples` | 1 | 24 MB/s ✓ | **none** (verbatim) | fits, zero-touch |
| `repeated uint32 [packed]` | 1–2 varint | 24–48 MB/s | varint ×24M/s | CPU-bound; non-uniform; busts ceiling when bit7 set |
| `repeated fixed32 [packed]` | 4 | **96 MB/s** ✗ | expand u8→u32 | 4× blowup past the ~40 MB/s FIFO ceiling; also models an 8-bit sample as a 32-bit int |
| `repeated uint32` (unpacked) | 2–6 | 48+ MB/s ✗ | tag+varint each | dead on both axes |

protobuf has no `uint8`/`uint16`; the smallest no-varint type is `fixed32`
(4 bytes). So there is no faithful packed-byte representation except `bytes`.
This is not a protobuf wart — FlatBuffers `[ubyte]`, Cap'n Proto
`List(UInt8)`/`Data` all represent a packed primitive array as a length prefix
+ raw region. **No serialization structures individual samples**, because
structuring 24M items/s is physically impossible, not a library limitation.
Precedent: sigrok's own `.sr` is raw sample blobs + a metadata sidecar — the
samples are opaque, the *geometry* is the schema. The firehose's schema is its
typed header; the samples are correctly opaque.

**In-place / DMA export.** `bytes` is also the *enabling* choice, not the
awkward one. On the wire `bytes` is `tag | length | verbatim payload`; make
`samples` the last field and a whole valid message is
`[precomputed header prefix][raw sample region]`. The CPU builds the ~10-byte
prefix each block (seq/t0 change anyway) and points PIO/DMA at the region right
after it — scatter-gather, two descriptors, **the CPU never touches a sample
byte and no protobuf encoder runs over the firehose**. A `repeated` field
would force the encoder to touch every element — precisely what breaks the
zero-CPU DMA path. Variable final blocks use a fixed-width (non-minimal)
varint length so the payload offset stays constant.

**FlatBuffers / Cap'n Proto evaluated and declined** for the firehose:
`CreateUninitializedVector` (flatbuffers) and Cap'n Proto's in-place `Data`
*do* support reserve-then-fill, so the in-place pipeline is feasible in all
three — but none structures the samples (still an opaque region), and adopting
one reintroduces a second serialization runtime on the MCU + the two-format
split, to gain a nicer envelope around an opaque payload. Net negative. The
only genuinely open pod-era detail is the scatter-gather plumbing for the
trailing-`bytes` prefix — a hardware decision, deferred with the pod, touching
neither the exerciser nor the control schema.

## Risks / Trade-offs

- **[Generated `protocol/` accidentally pulls a pico-sdk/hardware dep → loses
  host-testability]** → the load-bearing property from the original firmware
  change. Enforce by the native test build linking only generated pb + nanopb
  runtime + dispatch adapter, and a grep gate that `protocol/` includes no
  `pico-sdk`/`hardware/*.h`/`tusb.h`. Confidence: HIGH — nanopb output is plain
  C by construction.
- **[nanopb `oneof` + `bytes`/`repeated` field sizing]** → nanopb needs max
  sizes for static allocation (`.options` file: `payload` max 64, `addr` max
  16, caps max 16). Get these from `command.h`'s existing `COMMAND_MAX_*`
  constants so buffers stay identical. Compile-time `<Message>_size` macros
  give the bounded-buffer property the "fixed-length" instinct wanted — without
  any struct casting.
- **[Wire break with any deployed host]** → there is no deployed host yet
  (host side is greenfield), so the break is free now and expensive later.
  This is the moment to make it.
- **[Two codegen steps in the build]** → firmware (nanopb C) and host (Python)
  both generate from the one `.proto`. Mitigated by a cross-language golden
  round-trip in CI so the two generators can never silently diverge.
- **[Debuggability vs JSON-in-a-terminal]** → lost the type-a-command-by-hand
  affordance. Mitigated by `protoc --decode_raw` on captured bytes and a small
  host CLI that encodes/decodes; acceptable given the contract-safety gain.
