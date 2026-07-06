# Delta: exerciser-firmware

## ADDED Requirements

### Requirement: JSON-lines command interface
The firmware SHALL speak JSON-lines over USB CDC serial: every command carries an `id`; every response echoes that `id` with `ok` or `err` plus payload. The v1 command set is `info`, `ws2812`, `dshot`, `pwm`, `uart_tx` (incl. SBUS-style frames), `i2c_scan`, `i2c_read`, `spi_tx`, `sync`, `loopback` per docs/EXERCISER.md parameter shapes.

#### Scenario: Response echoes id
- **WHEN** any valid command with `id: 42` is processed
- **THEN** the response line carries `id: 42` and status `ok` or `err` (verified against the protocol handler in a host-side or unit-test harness, no hardware)

### Requirement: Clock-parameterized timing
All timing constants SHALL derive from the configured system clock; migrating RP2040 (133 MHz) -> RP2350 (150 MHz) SHALL require only a configuration change, no timing re-derivation.

#### Scenario: Two clocks, one source tree
- **WHEN** the firmware is compiled for 133 MHz and for 150 MHz
- **THEN** both builds succeed from unmodified sources with timing constants computed from the clock parameter

### Requirement: E9 runtime guard with silicon-aware capabilities
At boot the firmware SHALL detect the silicon stepping (chip-ID/bootrom, with a functional-probe fallback) and record `e9_affected`. On affected (A2) silicon it SHALL NOT enable internal pull-downs on DUT-facing input pins nor arm pull-down-sourced interrupts; input-sensing capabilities are self-disabled and reported unavailable by `info`; affected commands answer `err` with reason `e9_unavailable`, never a wrong reading.

#### Scenario: A2 degrades gracefully
- **WHEN** an input-sensing command arrives with `e9_affected = true` (simulated in the protocol harness)
- **THEN** the response is `err` with reason `e9_unavailable`; output-stimulus commands remain fully functional

#### Scenario: Capability advertisement is silicon-aware
- **WHEN** `info` runs on A2 and on A4 configurations
- **THEN** the capability list differs exactly in the input-sensing entries, and `info` reports stepping and E9 posture

### Requirement: Hazard envelope enforced in firmware
Open-drain bus-master operations (i2c_scan/i2c_read) are permitted on live systems; push-pull stimulus SHALL be refused unless the command asserts the line is believed undriven, and the DUT-control boundary is absolute: no flashing, no MSP writes, no commanding user firmware — the firmware exposes no such commands.

#### Scenario: Push-pull without undriven assertion refused
- **WHEN** a `ws2812`/`uart_tx` command arrives without the believed-undriven assertion field
- **THEN** the firmware answers `err` citing the hazard envelope

### Requirement: Headless CI build
The firmware SHALL build headless on Linux CI with a pinned pico-sdk (open toolchain only); compile success is the automated gate, hardware validation is explicitly a human step.

#### Scenario: CI compiles both targets
- **WHEN** CI runs the firmware job
- **THEN** RP2040 and RP2350 targets compile from a clean checkout without account-walled or Windows-only tools
