# Design: phase-2-decode-backend

## Context

Measure (Phase 1) says what a signal *is* and infers its parameters; Decode
turns the signal into events. The strategic ruling (docs/ARCHITECTURE.md
§ Sigrok posture) is **parasitic, not dependent**: wrap the sigrok decoder
corpus behind an abstraction and feed it Measure-inferred parameters, but never
couple product fate to it. A second, native UART decoder proves the abstraction
is real and gives the offline/test path a sigrok-free backend.

The exact sigrok-cli invocation and output format below were **verified locally
against sigrok-cli 0.7.2 / libsigrokdecode 0.5.3** by crafting `.sr` files with
known payloads and decoding them — they are confirmed, not assumed.

## Goals / Non-Goals

**Goals:**
- One normalized event schema; decoder-specific output never leaks past the
  backend boundary.
- Zero-configuration end-to-end: Measure infers, Decode consumes.
- Two backends (sigrok subprocess + native UART) passing one test suite.
- Version pinning with a loud drift alarm.

**Non-Goals:**
- No new protocols beyond UART/I²C/SPI in v1 Decode (WS2812/DShot are
  recognition-only in Measure; decoding them is not required here).
- No in-process libsigrok bindings — subprocess + `.sr` files only.
- No anomaly detection (Phase 3), no English (Phase 4).

## Decisions

### Normalized event schema

A decoded event is a frozen dataclass, protocol-agnostic at the envelope,
typed by `kind`:

```python
@dataclass(frozen=True)
class DecodedEvent:
    kind: str          # e.g. "uart.byte", "i2c.start", "i2c.address",
                       # "i2c.ack", "i2c.nak", "i2c.data", "i2c.stop",
                       # "spi.transfer"
    start_sample: int  # inclusive, in capture sample indices
    end_sample: int    # inclusive
    data: dict         # kind-specific payload, see below
    channel: str | None = None  # source role/line where meaningful
```

`data` conventions (keep these exact — Narrate depends on them):
- `uart.byte`: `{"value": int, "ascii": str|None}`
- `i2c.address`: `{"address": int, "rw": "read"|"write"}`
- `i2c.ack` / `i2c.nak`: `{}` (the kind carries the meaning)
- `i2c.data`: `{"value": int}`
- `spi.transfer`: `{"mosi": int|None, "miso": int|None}`

Seconds are derivable from `start_sample / samplerate_hz`; store samples as the
source of truth (integers, no float drift) and expose a `.seconds(samplerate)`
helper. Rationale: Phase 4 traceability requires every assertion to point at
sample ranges (ROADMAP Phase 4 acceptance).

### Backend interface

```python
class DecodeBackend(Protocol):
    def decode(self, capture: Capture, hypothesis: ProtocolHypothesis
               ) -> list[DecodedEvent]: ...
```

`ProtocolHypothesis` is the handoff object from Measure: protocol name +
inferred parameters + channel-role assignment. Define it in `decode/` (or import
from `measure/` if Phase 1 already exposes an equivalent — check
`measure/classify.py`; if it emits per-channel roles + params, adapt it, do not
duplicate). Minimum fields Decode needs:
- UART: `{"baud": int, "data_bits": 8, "parity": "none", "stop_bits": 1.0,
  "rx_channel": "D0"}`
- I²C: `{"scl_channel": "D0", "sda_channel": "D1"}`
- SPI: `{"clk": "D0", "mosi": "D1"|None, "miso": "D2"|None, "cs": "D3"|None,
  "cpol": 0, "cpha": 0, "wordsize": 8}`

### sigrok backend — exact, verified invocation

sigrok-cli decodes a `.sr` file with `-P <decoder>:<opts>` and emits annotations
with `-A <decoder>`. Use `--protocol-decoder-samplenum` to get sample ranges
(CONFIRMED format: `START-END decoder-1: text`). Filter to the machine-readable
annotation class so parsing is trivial and stable.

**UART** (confirmed): channel map uses the decoder's channel name = the
capture's probe name. For a capture whose RX line is probe `D0`:
```
sigrok-cli -i cap.sr -P uart:rx=D0:baudrate=115200:data_bits=8:parity=none:stop_bits=1 \
           -A uart=rx-data --protocol-decoder-samplenum
```
`-A uart=rx-data` yields exactly one line per decoded byte:
`4368-6036 uart-1: 41` (hex byte value between the sample bounds). Parse
`^(\d+)-(\d+) uart-1: ([0-9A-Fa-f]+)$` → `uart.byte {value=0x41}`. (Default
`format` is hex; pin `format=hex` explicitly so a config change never breaks the
parser.)

**I²C** (confirmed): channels `scl` and `sda`; annotation class `i2c` gives the
address/data/ack rows. Confirmed output lines include:
`780-3300 i2c-1: Address write: 68`, `3660-4020 i2c-1: ACK`,
`4020-6900 i2c-1: Data write: AA`, `Start`, `Stop`, `NACK`.
```
sigrok-cli -i cap.sr -P i2c:scl=D0:sda=D1 -A i2c=addr-data --protocol-decoder-samplenum
```
Map by the leading word: `Start`→`i2c.start`, `Address write/read: XX`→
`i2c.address {address=0xXX, rw=...}`, `ACK`→`i2c.ack`, `NACK`→`i2c.nak`,
`Data write/read: XX`→`i2c.data {value=0xXX}`, `Stop`→`i2c.stop`. The address is
already shifted-7-bit (`address_format=shifted`, the default; pin it).

**SPI** (confirmed interface): channels `clk`, `mosi`, `miso`, `cs`; options
`cpol`, `cpha`, `wordsize`, `cs_polarity`. Use `-A spi=mosi-data` (and/or
`miso-data`) with samplenum:
```
sigrok-cli -i cap.sr -P spi:clk=D0:mosi=D1:miso=D2:cs=D3:cpol=0:cpha=0:wordsize=8 \
           -A spi=mosi-data --protocol-decoder-samplenum
```
One line per word; parse to `spi.transfer`.

**Subprocess discipline:** reuse the Phase 0 `capture/sigrokcli.py` subprocess
pattern (typed exceptions, injected boundary for tests). Tests MUST NOT require
sigrok installed on the general path — mock the subprocess for unit tests and
mark the real-sigrok integration tests to `pytest.skip` when `sigrok-cli` is
absent, exactly as Phase 0 does for `demo_capture`.

### Native UART backend — proves the abstraction

A pure-numpy UART decoder over the RX bit array: find the idle-high level,
detect each start bit (falling edge after idle), sample the midpoint of each of
the 8 data bits at `baud`-spaced offsets, assemble LSB-first, check the stop
bit. Emits the same `uart.byte` events with the same sample bounds semantics.
This is a weekend algorithm (docs: "reimplementing UART/SPI/I²C is a weekend")
and it is the backend the test suite uses by default so CI never needs sigrok.

### Version pinning + drift detection

sigrok's decoder corpus is the asset; pin it and alarm on drift. Implement a
checksum test: hash the sorted contents of the installed decoder directory
(default `/usr/share/libsigrokdecode/decoders/`, overridable by env), restricted
to the decoders we actually use (`uart`, `i2c`, `spi`) to avoid false alarms
from unrelated decoders. Store the expected manifest (decoder name → sha256 of
its `pd.py` + `__init__.py`) as a committed JSON. The test loads the manifest,
recomputes, and fails naming any decoder whose hash moved. When sigrok is
absent, the test skips (not fails) — pinning is about *detecting* drift where
sigrok exists, not requiring it.

## Risks / Trade-offs

- [sigrok output format differs across versions] → parser targets the
  machine-readable annotation *class* rows (`=rx-data`, `=addr-data`) with
  `--protocol-decoder-samplenum`, the most stable surface; format options
  (`format=hex`, `address_format=shifted`) are pinned explicitly so a default
  change upstream cannot silently shift them.
- [Decoder path is distro-specific] → path is a configurable constant with the
  Debian/Ubuntu default baked in; the checksum test skips when the path is
  absent.
- [ProtocolHypothesis duplicates Measure output] → adapt Measure's existing
  per-channel role/param output; only define new fields Decode strictly needs.
