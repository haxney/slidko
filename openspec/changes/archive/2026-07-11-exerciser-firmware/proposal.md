# Proposal: exerciser-firmware

## Why

The exerciser is Slidko's known-firmware harness device: it generates bus traffic, scans, and stimulus on command — the same firmware bench-corpus sweep cells require. Parallel track per docs/ROADMAP.md, specified by docs/EXERCISER.md; needed by the time sweep cells run.

Status note: design.md and tasks.md deferred until pickup; proposal + specs define the contract now. Agent sessions can compile-verify only — flashing and hardware validation are human steps.

## What Changes

- Add `firmware/` build tree: pico-sdk (C, CMake), pinned SDK version, headless Linux build, CI compile check. RP2350 canonical, RP2040 acceptable for development — all timing constants parameterized by system clock (133 vs 150 MHz is a config change).
- Add JSON-lines command interface over USB CDC (TinyUSB): `info`, `ws2812`, `dshot`, `pwm`, `uart_tx`, `i2c_scan`, `i2c_read`, `spi_tx`, `sync`, `loopback`; every command carries an `id`, every response echoes it with `ok|err`.
- Add the E9 runtime guard: detect silicon stepping at boot; on A2, self-disable input-sensing capabilities and internal pull-downs on DUT-facing pins, reporting them unavailable via `info` and `err e9_unavailable` — never a corrupt reading.
- Enforce the hazard envelope in firmware: open-drain bus-master ops permitted on live systems; push-pull output only onto believed-undriven lines through series resistance; no DUT write/control paths, ever.

## Capabilities

### New Capabilities

- `exerciser-firmware`: clock-parameterized stimulus/scan firmware with a device-agnostic JSON-lines command schema, silicon-aware capability advertisement, and the E9 guard.

### Modified Capabilities

(none)

## Impact

- New `firmware/` tree with its own CMake build; no Python-package coupling (the host talks to it over serial).
- CI gains an arm-none-eabi compile job; no test may require attached hardware.
- The command schema is device-agnostic by design — the schema, not the silicon, defines the exerciser role.
