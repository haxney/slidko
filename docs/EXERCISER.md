# The exerciser — firmware spec

Slidko's own known-firmware harness device: generates bus traffic, scans, and
stimulus on command. The same firmware the bench corpus requires — corpus
sweep cells and field "exercise" instructions share one implementation.
Session-optional: the poke loop degrades to watch + twiddle without it.

## Platform

- **RP2350 (Pico 2) is canonical.** RP2040 is acceptable for development; all
  timing constants MUST be parameterized by system clock (133 vs 150 MHz) so
  migration is a config change, not a re-derivation. PIO programs are
  forward-compatible (RP2350 PIO is a superset).
- **Variant ruling: RP2350A, A4 stepping.** Part-number grammar is
  `RP` + `235[flash]` + `[package]` + `0` + `[stepping]`:
  - Flash field: `2350` = 0 MB in-package (external QSPI flash on the board);
    `2354` = 2 MB stacked in-package. Irrelevant for a Pico 2 buyer — the board
    carries external flash. Only matters if spinning a custom PCB and deleting
    the external flash chip. Exerciser firmware is small; either is ample.
  - Package field: `A` = QFN-60 / 30 GPIO (this is what the Pico 2 uses);
    `B` = QFN-80 / 48 GPIO. **Get A.** Exerciser peak concurrent pin demand is
    well under 30; B solves a non-problem and only exists in custom-board form.
  - Stepping field: `A2` (E9-broken) vs `A4` (E9 hardware-fixed; adds 5V GPIO
    tolerance while powered). **Prefer A4** (see E9 section). A2 is adequate for
    pure output-stimulus duty; A4 is required once input-sensing features are
    enabled. Firmware detects stepping at boot and self-limits (see below).
  - Canonical orderable part / board: RP2350A0A4 chip, or a Pico 2 board whose
    listing states A4 stepping (treat silence as A2). Channel is deliberately
    mixed A2/A4 as of 2025 reporting; verify at point of purchase.
- **Toolchain: pico-sdk (C, CMake).** Requirements are hard: open toolchain,
  headless Linux builds, CI-friendly, no account-walled downloads, no
  Windows-only tools. Pin the pico-sdk version in the build.
- ESP32-family is rejected for this role: RMT vs PIO is a genuinely different
  stimulus programming model; building corpus firmware twice is pure waste.

## Command interface

JSON-lines over USB CDC serial (TinyUSB). The schema is **device-agnostic by
design** — the schema, not the silicon, defines the exerciser role. Every
command carries an `id`; every response echoes it with `ok|err` + payload.

Required commands (v1):

- `info` — firmware version, clock, pin map, capability list, **detected
  silicon (chip family + RP2350 stepping A2/A4) and E9 posture** (whether
  internal-pull-down / input-sensing features are enabled or self-disabled).
  The host uses this to know which capabilities are live; capability
  advertisement is silicon-aware, not hardcoded.
- `ws2812 {pin, count, pattern, repeat}` — PIO-generated, spec-exact timing.
- `dshot {pin, rate, value, repeat}` — DShot150/300/600 frames. Exact bit
  timing (source: Betaflight DShot docs, cross-checked against independent
  references; confidence HIGH — these are stable, long-published numbers):

  | Rate | Bit period | T0H | T1H |
  |---|---|---|---|
  | DShot150 | 6.67 µs | 2500 ns | 5000 ns |
  | DShot300 | 3.33 µs | 1250 ns | 2500 ns |
  | DShot600 | 1.67 µs | 625 ns | 1250 ns |

  Minimum inter-frame gap: ~2 µs. T1H is always 2× T0H; low time is the
  remainder of the bit period.
- `pwm {pin, freq_hz, duty | pulse_us}` — servo/PWM.
- `uart_tx {pin, baud, frame, payload, repeat}` — including SBUS-style
  non-standard frames.
- `i2c_scan {sda, scl, speed_hz}` — address scan; returns responding
  addresses.
- `i2c_read {sda, scl, addr, reg, len}` — register reads (device-ID
  interrogation of undocumented boards — highest-leverage dark-board tool).
- `spi_tx {sck, mosi, cs, mode, speed_hz, payload}`.
- `sync {pin, mode}` — reserved sync-channel marker: toggle the marker line
  at stimulus-emission events so the capture instrument gets free
  stimulus-to-capture alignment (costs one LA channel; see ARCHITECTURE.md).
- `loopback {generator..., capture_pin}` — self-test: emit known stimulus
  into the device's own input (or into the DLA) to verify the instrument
  chain (probe/threshold/decoder) before any DUT conclusion is drawn. Every
  credible instrument self-tests.

## Hazard envelope (v1 rules — enforced in firmware AND in Diagnose)

- **Open-drain bus-master operations (I²C scan/read) are permitted on live
  systems** — multi-master contention is survivable by design.
- **Push-pull output ONLY onto lines believed undriven,** ALWAYS through a
  series resistor (a few hundred Ω) limiting contention current, and always
  delivered with instructed-hazard framing to the user. Contention on
  push-pull lines can destroy drivers — this is the one way the tool breaks a
  board; the asymmetry is the rule.
- The exerciser never crosses the DUT-control line: it is always Slidko's own
  hardware speaking standard protocols into the DUT's connectors, like a
  human with a known-good module. No flashing, no writes, no commanding user
  firmware.

## RP2350 E9 erratum (application-critical)

E9: on the **A2 stepping**, a GPIO input can latch near ~2.1–2.2 V when the
input buffer is enabled — pathological for a device whose job is touching
unknown DUT circuits. Community testing found it more pervasive than the
original erratum text: the latch can occur with a pull-down enabled AND with
no pull at all, so "just add an external pull-down" was an incomplete
workaround on A2.

**Fix status (corrected — verify at point of purchase):**
- **A4 stepping fixes E9 in hardware** (the fix rode in on the internal A3
  stepping and carries into A4; A4 adds bootrom/security hardening on top).
  On A4, internal pulls work as on RP2040, and A4 additionally provides **5V
  GPIO tolerance while powered** — a real safety margin for DUT-facing inputs.
- **A2 is still in the channel** (deliberately mixed; distributor dead stock).
  Confidence: HIGH on the A2/A4 fix map per the July 2025 PCN; MODERATE on any
  given vendor's current stock — verify.

**Design rules:**
- Target A4 (RP2350A0A4). On A4, internal pull-downs on DUT-facing pins are
  usable.
- On A2, or when probing unknown rails generally, use **external pull-downs on
  DUT-facing input pins** and avoid relying on internal pull-downs / edge
  interrupts sourced from them.
- E9 is an INPUT pathology only — irrelevant to pure output/stimulus duty. It
  gates input-sensing features (sync-line readback, `adc_watch`, any
  closed-loop poke that reads a DUT line).

**Runtime guard (required — the firmware must not blindly trigger E9):**
- At boot, **detect the silicon stepping** (chip-ID / bootrom-reported
  revision) and record an `e9_affected` flag (true on A2, false on A4).
- On an `e9_affected` chip, the firmware **must not enable internal pull-downs
  on DUT-facing input pins and must not arm pull-down-sourced edge
  interrupts**; input-sensing capabilities (`adc_watch`, sync readback,
  closed-loop reads) are **self-disabled or degraded**, and `info` reports
  them as unavailable rather than silently misbehaving. If such a command
  arrives on an affected chip, respond `err` with an explicit
  `e9_unavailable` reason, not a wrong reading.
- On A4, all input features are enabled.
- Rationale: the same firmware image runs on whatever stepping arrives; it
  degrades gracefully on A2 (output stimulus fully functional) rather than
  producing corrupt input readings that would poison corpus ground truth.
- Detection caveat: exact chip-ID/stepping read path should be verified
  against the current pico-sdk and RP2350 datasheet §chip identification
  before trusting it. Confidence: MODERATE that a clean stepping read is
  exposed; if not, fall back to a boot-time functional probe (enable internal
  pull-down on a known-floating internal test pin, read: high/latched ⇒ A2,
  low ⇒ A4).

## Bonus role (nearly free)

The on-chip ADC (12-bit, 500 kS/s, ~8.7 ENOB) as a crude analog rail-watcher:
useless for signal integrity, sufficient for ms-scale rail sags — an ANALOG
smoke detector the logic analyzer lacks at any price. `adc_watch {pin,
rate_hz, window_ms}` command reserved; MODERATE confidence on usability
pending grounding care.
