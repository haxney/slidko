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

- `info` — firmware version, clock, pin map, capability list.
- `ws2812 {pin, count, pattern, repeat}` — PIO-generated, spec-exact timing.
- `dshot {pin, rate, value, repeat}` — DShot150/300/600 frames.
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

Early RP2350 steppings latch GPIO inputs at ~2.1–2.2 V when internal
pull-downs are used — pathological for a device whose job is touching unknown
DUT circuits. **Design rule: external pull-downs only on DUT-facing pins.**
Remediation status in current steppings: UNKNOWN — verify before any board
design that relies on internal pull-downs. (Irrelevant to pure output/
stimulus duty; it bites inputs.)

## Bonus role (nearly free)

The on-chip ADC (12-bit, 500 kS/s, ~8.7 ENOB) as a crude analog rail-watcher:
useless for signal integrity, sufficient for ms-scale rail sags — an ANALOG
smoke detector the logic analyzer lacks at any price. `adc_watch {pin,
rate_hz, window_ms}` command reserved; MODERATE confidence on usability
pending grounding care.
