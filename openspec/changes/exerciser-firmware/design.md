# Design: exerciser-firmware

## Context

The exerciser is Slidko's known-firmware harness device: it generates bus
traffic, scans, and stimulus on command, and it is the same firmware the bench
corpus sweep cells require (docs/EXERCISER.md, ARCHITECTURE.md). Platform:
RP2350 canonical, RP2040 acceptable for development — all timing constants
parameterized by system clock so 133→150 MHz is a config change, not a
re-derivation (CLAUDE.md guardrail 6). Toolchain: pico-sdk (C, CMake), open and
headless. **Agent sessions can compile-verify only** — flashing and hardware
validation are human steps; no test may require attached hardware.

The design's central move that makes this testable at all: **split the
protocol/command logic (portable C, host-unit-tested) from the hardware drivers
(compile-only).** The JSON-lines command parser, dispatcher, capability
advertisement, E9 posture logic, and hazard-envelope checks are pure functions
over plain data — they build and run natively on the CI host with a tiny
assert-based harness. Only the PIO/GPIO/TinyUSB layer needs the ARM toolchain,
and it is gated by compile success alone.

## Goals / Non-Goals

**Goals:**
- JSON-lines command interface (id-echoed, `ok|err`) with the v1 command set.
- Clock-parameterized timing (one source tree, two clocks).
- E9 runtime guard with silicon-aware capability advertisement.
- Hazard envelope enforced in firmware; no DUT-control paths, ever.
- Headless CI: native host unit tests for the protocol layer + arm-none-eabi
  compile for both targets.

**Non-Goals:**
- No pod code (guardrail 1). No DUT write/control — no flashing, no MSP writes,
  no commanding user firmware (guardrail 4, absolute). No `adc_watch` beyond a
  reserved command stub (bonus role, deferred). No hardware-in-the-loop tests.

## Decisions

### Directory + build split

```
firmware/
  CMakeLists.txt            # pico-sdk project; pins SDK version; two board targets
  pico_sdk_import.cmake     # standard SDK import shim
  src/
    main.c                  # TinyUSB CDC loop; calls protocol/ dispatch
    hw/                     # PIO/GPIO/TinyUSB drivers (compile-only)
    protocol/               # PORTABLE C — parser, dispatch, caps, e9, hazards
  test/
    CMakeLists.txt          # native (host) build of protocol/ + assert harness
    test_protocol.c         # unit tests, no SDK, no hardware
```
`protocol/` includes NO pico-sdk headers — it operates on structs and returns
result structs, so `test/` compiles it with the host `cc`. `hw/` is the only
code that touches `hardware/pio.h`, `tusb.h`, etc.

### pico-sdk pin

Pin pico-sdk to a released tag in `CMakeLists.txt` (via `PICO_SDK_FETCH_FROM_GIT`
tag or a submodule). Use **2.3.0** (latest release as of 2026-07-06; first-class
RP2350 + RISC-V support landed in 2.0.0). Board targets: `pico` (RP2040) and
`pico2` (RP2350). CMake builds both from unmodified sources.

### Clock-parameterized timing

A single `SYS_CLK_HZ` config (133_000_000 for RP2040, 150_000_000 for RP2350)
drives every timing constant. Bit/symbol timings are computed from `SYS_CLK_HZ`
at build time (PIO clock dividers) or as sample counts — never hardcoded for one
clock. The DShot table (docs/EXERCISER.md; confidence HIGH — stable published
numbers, T1H always 2× T0H, low time is the remainder of the bit period):

| Rate | Bit period | T0H | T1H |
|---|---|---|---|
| DShot150 | 6.67 µs | 2500 ns | 5000 ns |
| DShot300 | 3.33 µs | 1250 ns | 2500 ns |
| DShot600 | 1.67 µs | 625 ns | 1250 ns |

WS2812: 800 kHz, spec-exact PIO timing (T0H≈0.4 µs, T1H≈0.8 µs, ±150 ns). All
derived from `SYS_CLK_HZ`. The "two clocks, one source tree" acceptance is met
by parameterization, verified by compiling both targets.

### JSON-lines command schema

One JSON object per line over USB CDC. Every command carries `id`; every response
echoes it with `"ok"` or `"err"` + payload. v1 command set (EXERCISER.md
parameter shapes): `info`, `ws2812 {pin,count,pattern,repeat}`,
`dshot {pin,rate,value,repeat}`, `pwm {pin,freq_hz,duty|pulse_us}`,
`uart_tx {pin,baud,frame,payload,repeat}` (incl. SBUS-style frames),
`i2c_scan {sda,scl,speed_hz}`, `i2c_read {sda,scl,addr,reg,len}`,
`spi_tx {sck,mosi,cs,mode,speed_hz,payload}`, `sync {pin,mode}`,
`loopback {generator...,capture_pin}`. The parser + dispatcher live in
`protocol/` and are host-unit-tested: given an input line, assert the parsed
command struct; given a command + a (mocked/simulated) hardware-result, assert
the response line echoes `id` with the right status. Use a minimal embedded JSON
approach (hand-rolled tokenizer or a vendored single-header parser); keep it in
`protocol/` so it is host-testable.

### E9 runtime guard (silicon-aware)

At boot, detect silicon stepping (chip-ID/bootrom revision; functional-probe
fallback per EXERCISER.md) and record `e9_affected` (true on A2, false on A4).
The *policy* is pure logic in `protocol/` and takes `e9_affected` as an input,
so it is host-testable without silicon:
- On `e9_affected`, input-sensing capabilities (sync readback, closed-loop
  reads, any pull-down-sourced sensing) are self-disabled; `info` reports them
  unavailable; an affected command answers `err` with reason `e9_unavailable` —
  never a wrong reading.
- On A4, all input features enabled.
- `info` capability list is silicon-aware: A2 vs A4 differ EXACTLY in the
  input-sensing entries, and `info` reports stepping + E9 posture.
The actual stepping-read (hardware) lives in `hw/` and feeds the flag into the
`protocol/` policy. Tests exercise the policy with `e9_affected` true/false.

### Hazard envelope in firmware

- Open-drain bus-master ops (`i2c_scan`, `i2c_read`) permitted on live systems.
- Push-pull stimulus (`ws2812`, `uart_tx`, `spi_tx`, `pwm`, `dshot` output)
  REFUSED unless the command asserts the target line is believed undriven (a
  required boolean field, e.g. `assert_undriven: true`); otherwise the firmware
  answers `err` citing the hazard envelope. Series-resistor framing is the
  physical rule the host/Diagnose must honor; the firmware's gate is the
  assertion field.
- DUT-control boundary is absolute: the firmware exposes NO flash/write/command
  path — there is simply no such command in the schema. A test asserts the
  command table contains none.
All of this is `protocol/`-layer logic and host-testable.

### CI

Two jobs, both headless:
1. **Protocol unit tests (host):** `cmake` the native `test/` target with the
   host `cc`, run `test_protocol` (assert-based; nonzero exit on failure).
2. **Firmware compile:** install `arm-none-eabi-gcc` + `cmake` + the pinned
   pico-sdk (open toolchain, no account-walled/Windows-only tools); build the
   `pico` and `pico2` targets; success is the gate. `clang-format --dry-run
   --Werror` (using the repo `.clang-format` from dev-tooling-gate) style-gates
   `firmware/`.

## Risks / Trade-offs

- [Protocol logic entangled with SDK → untestable] → the `protocol/`↔`hw/` split
  is the load-bearing decision; `protocol/` must not include SDK headers, so it
  compiles on the host. Enforce by the native test build linking only
  `protocol/`.
- [Stepping-read path uncertain on real silicon] → EXERCISER.md flags this
  MODERATE; the policy is host-tested regardless, and the hardware read has a
  functional-probe fallback. Confidence: the read path is verify-on-hardware
  (human step); the policy is fully tested now.
- [Hazard field is bypassable by a careless host] → the firmware refuses
  push-pull without the assertion; that is the firmware's half. The other half
  (series resistor, believed-undriven judgement) is Diagnose's, mirrored here so
  neither side is the sole guard.
