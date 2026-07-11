## 1. Reverse the ruling, update docs, supersede protobuf-wire

- [ ] 1.1 Update CLAUDE.md "Language ruling": exerciser firmware C/pico-sdk → Rust, recording the corrected rationale (protocols are PIO, port verbatim; USB stack is the only real gap); keep guardrails 1 (no pod) and 4 (no DUT control) intact. Verify: `grep -q "Rust" CLAUDE.md` in the exerciser ruling and `grep -q "No pod code" CLAUDE.md` still present.
- [ ] 1.2 Update docs/EXERCISER.md "Platform"/"Toolchain": pico-sdk C → Rust (`rp235x-hal`/`embassy-rp`, ARM Cortex-M33, `thumbv8m.main-none-eabi`, UF2/picotool flashing). Verify: `grep -qi "rp235x-hal\|embassy" docs/EXERCISER.md` and no remaining "pico-sdk (C, CMake)" toolchain line.
- [ ] 1.3 Lift the deferred pod data-plane serialization rationale from `openspec/changes/exerciser-protobuf-wire/design.md` into docs/ARCHITECTURE.md § Deferred (its own stated home). Verify: `grep -q "CaptureBlock\|bytes samples" docs/ARCHITECTURE.md`.
- [ ] 1.4 Remove the superseded `exerciser-protobuf-wire` change directory. Verify: `test ! -d openspec/changes/exerciser-protobuf-wire` and `openspec list --json` shows only `rust-exerciser-firmware` active.

## 2. Host policy crate scaffold

- [ ] 2.1 Create the Cargo workspace with a host `policy` lib crate and a `rust-toolchain.toml` pinning the channel + `thumbv8m.main-none-eabi` target. Verify: `cargo test -p policy` runs (empty pass) and `cargo metadata --format-version 1` lists `policy`.
- [ ] 2.2 Remove the vendored pico-sdk and gitignore Rust `target/`. Verify: `test ! -d firmware/vendor/pico-sdk` and `git status --porcelain` shows no `target/` artifacts.

## 3. RP2350 target bringup

- [ ] 3.1 Create the `exerciser` binary crate (`embassy-rp`, ARM core) with a valid RP2350 IMAGE_DEF (`imagedef-secure-exe`), a panic handler, and a minimal `main` that initialises clocks. Verify: `cargo build -p exerciser --target thumbv8m.main-none-eabi`.
- [ ] 3.2 Add the UF2 packaging step (`picotool`/`elf2uf2`) to the build/xtask. Verify: the build produces `*.uf2` (`test -f` the output path in the xtask/CI).
- [ ] 3.3 Add the boundary gate: assert the `policy` crate imports neither `embassy-rp` nor `rp235x-hal`. Verify: gate script `grep -L` check exits 0.

## 4. Protobuf wire codec (no-std)

- [ ] 4.1 Write the canonical `.proto` (`Command`/`Response` oneof envelopes, `bytes` payloads, `ErrorReason` enum) and a **failing** Rust host test: `Command{id=42}` round-trips to a `Response{id=42}` with an ok/err body, and a parse failure maps to `ErrorReason::PARSE_ERROR`. Verify: `cargo test -p policy` fails (no codec yet).
- [ ] 4.2 Wire the chosen no-std codec (design Q1) into `policy` to make 4.1 pass. Verify: `cargo test -p policy`.
- [ ] 4.3 Write a **failing** cross-language golden test: a fixture of encoded bytes with a `payload` containing `0x00` and `0x22` decodes byte-identically in Rust and Python. Verify: `cargo test -p policy` and `pytest tests/exerciser/test_wire.py` both fail first.
- [ ] 4.4 Generate the Python bindings from the same `.proto` and implement the host codec to make 4.3 pass. Verify: `pytest tests/exerciser/test_wire.py` and `cargo test -p policy`.
- [ ] 4.5 Implement the fixed 2-byte LE length-prefix framing (encode/decode, no CRC) in `policy`. Verify: `cargo test -p policy` framing test passes.

## 5. Policy: dispatch, E9 guard, hazard envelope

- [ ] 5.1 Write a **failing** test: the dispatcher echoes `id` and returns an ok/err body for every v1 command variant. Verify: `cargo test -p policy` fails.
- [ ] 5.2 Implement the dispatcher over the decoded `oneof` to make 5.1 pass. Verify: `cargo test -p policy`.
- [ ] 5.3 Write a **failing** test: with `e9_affected = true` an input-sensing command returns `err(E9_UNAVAILABLE)`, and `info`'s capability list differs A2 vs A4 in exactly the input-sensing entries. Verify: `cargo test -p policy` fails.
- [ ] 5.4 Implement the E9 policy (stepping-agnostic core taking an `e9_affected` flag) to make 5.3 pass. Verify: `cargo test -p policy`.
- [ ] 5.5 Write a **failing** test: push-pull (`ws2812`/`uart_tx`) without the believed-undriven assertion returns `err(HAZARD_VIOLATION)`; `i2c_scan`/`i2c_read` are permitted. Verify: `cargo test -p policy` fails.
- [ ] 5.6 Implement the hazard-envelope checks to make 5.5 pass. Verify: `cargo test -p policy`.

## 6. PIO stimulus and timing

- [ ] 6.1 Write a **failing** host test: the DShot clock-divider/timing computation for 150/300/600 matches the docs/EXERCISER.md table (periods 6.67/3.33/1.67 µs, T1H = 2×T0H) across the 133 MHz and 150 MHz clocks. Verify: `cargo test -p policy` fails.
- [ ] 6.2 Implement the clock→divider/timing math (no-HAL, host-testable) to make 6.1 pass. Verify: `cargo test -p policy`.
- [ ] 6.3 Port the WS2812 and DShot PIO programs to `pio-proc` inline assembly in the `exerciser` crate, driven by the 6.2 divider. Verify: `cargo build -p exerciser --target thumbv8m.main-none-eabi`.

## 7. HAL command handlers (target)

- [ ] 7.1 Implement silicon-stepping detection (PAC/SYSINFO, functional-probe fallback) producing the `e9_affected` flag fed to the policy layer, and have `info` report stepping + E9 posture. Verify: `cargo build -p exerciser --target thumbv8m.main-none-eabi` (host unit test on any pure mapping helper).
- [ ] 7.2 Implement the HAL handlers: `i2c_scan`/`i2c_read` (open-drain), `spi_tx`, `pwm`, `uart_tx` (incl. SBUS 8E2 inverted), `sync`, `loopback`, `adc_watch` (reserved → unavailable), and series-resistor push-pull GPIO. Verify: `cargo build -p exerciser --target thumbv8m.main-none-eabi`.
- [ ] 7.3 Wire the `embassy-usb` CDC-ACM transport + length framing to the dispatcher. Verify: `cargo build -p exerciser --target thumbv8m.main-none-eabi`.

## 8. CI, cleanup, and deferred gate

- [ ] 8.1 Replace the firmware CI job with: `cargo build -p exerciser --target thumbv8m.main-none-eabi`, `cargo test -p policy`, the boundary gate (3.3), and the Python golden (`pytest tests/exerciser/`). Verify: CI config invokes all four; they run green locally.
- [ ] 8.2 Delete the C firmware tree (`firmware/src`, `firmware/test`, `firmware/CMakeLists.txt`, `firmware/pico_sdk_import.cmake`, `firmware/build-pico*`). Verify: `test ! -e firmware/CMakeLists.txt` and the workspace still builds (`cargo build --workspace`).
- [ ] 8.3 Run `openspec validate rust-exerciser-firmware --strict` and document the deferred real-silicon validation gate (CDC-ACM enumeration first, then per-protocol scope checks) in docs/EXERCISER.md. Verify: `openspec validate rust-exerciser-firmware --strict` exits 0 and `grep -qi "validation" docs/EXERCISER.md`.
