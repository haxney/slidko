# Tasks: exerciser-firmware

> Prerequisite: `dev-tooling-gate` applied (provides the repo `.clang-format`).
> Parallel track. **Toolchain note:** verification here uses the C toolchain
> (`cmake`, `ctest`, host `cc`, `arm-none-eabi-gcc`, `clang-format`) — NOT the
> Python `make check`. The overnight runner is allowlisted for these (see
> `.opencode/agents/overnight.md`); pico-sdk must be pre-provisioned at
> `$PICO_SDK_PATH` (no network overnight — a missing SDK is a BLOCKED.md stop).
> Configure/build out-of-source under `firmware/build/`; run native tests via
> `ctest --test-dir firmware/build --output-on-failure`. No task requires
> attached hardware; flashing and on-silicon validation are explicitly human
> steps.

## 1. Project skeleton + pico-sdk pin

- [ ] 1.1 Create `firmware/CMakeLists.txt` (pico-sdk project), `firmware/pico_sdk_import.cmake`, and the `src/{hw,protocol}` + `test/` tree per design.md. Pin pico-sdk to tag **2.3.0**. Declare board targets `pico` (RP2040) and `pico2` (RP2350)
- [ ] 1.2 Add a `SYS_CLK_HZ` config selected per target (133000000 for `pico`, 150000000 for `pico2`); NO timing constant is hardcoded for a single clock
- [ ] 1.3 Verify (runner/CI/human): `cmake` configures and the `pico2` target builds from a clean checkout with the pinned SDK; repeat for `pico`

## 2. Portable protocol layer (host-testable, no SDK headers)

- [ ] 2.1 Write failing native unit tests in `firmware/test/test_protocol.c` (assert-based, `main` returns nonzero on failure): parsing a JSON-lines command yields the expected command struct; `protocol/` includes NO pico-sdk headers
- [ ] 2.2 Implement `firmware/src/protocol/` — JSON-lines tokenizer + command parser + a `command_t` struct for the v1 command set (`info, ws2812, dshot, pwm, uart_tx, i2c_scan, i2c_read, spi_tx, sync, loopback`) with EXERCISER.md parameter shapes; native tests green
- [ ] 2.3 Add `firmware/test/CMakeLists.txt` building the native test target with the host `cc`, linking ONLY `protocol/` (proving the SDK split); verify it runs and passes

## 3. id-echo + ok/err response contract

- [ ] 3.1 Write failing native test: dispatching any valid command with `id:42` produces a response line carrying `id:42` and status `ok` or `err`; an unparseable line yields `err` with a reason
- [ ] 3.2 Implement the dispatcher + response serializer in `protocol/`; native tests green

## 4. Clock-parameterized timing tables

- [ ] 4.1 Write failing native test: the DShot T0H/T1H/bit-period values (DShot150/300/600 from design.md) and WS2812 timings are computed from `SYS_CLK_HZ`, and recomputing at 133 vs 150 MHz yields the correct per-clock divider/counts (T1H == 2×T0H for DShot)
- [ ] 4.2 Implement the timing computations as portable functions of `SYS_CLK_HZ` in `protocol/` (the PIO program in `hw/` consumes them); native tests green
- [ ] 4.3 Verify (runner/CI/human): both `pico` and `pico2` targets compile from the unmodified source tree — the "two clocks, one source tree" acceptance

## 5. E9 runtime guard (silicon-aware, policy host-tested)

- [ ] 5.1 Write failing native tests: with `e9_affected=true`, an input-sensing command (e.g. sync readback / closed-loop read) returns `err` reason `e9_unavailable` and output-stimulus commands stay functional; `info` capability list on A2 vs A4 differs EXACTLY in the input-sensing entries and reports stepping + E9 posture
- [ ] 5.2 Implement the E9 policy as pure logic in `protocol/` taking `e9_affected` as input per design.md; native tests green
- [ ] 5.3 Implement the hardware stepping-read + functional-probe fallback in `hw/` (compile-only; feeds the flag into the policy) — mark with a doc comment that the read path is verify-on-hardware (human step)

## 6. Hazard envelope enforced in firmware

- [ ] 6.1 Write failing native tests: a push-pull stimulus command (`ws2812`/`uart_tx`/`spi_tx`/`pwm`/`dshot`) WITHOUT `assert_undriven:true` returns `err` citing the hazard envelope; WITH it, the command is accepted; open-drain `i2c_scan`/`i2c_read` are accepted without the assertion
- [ ] 6.2 Write a native test asserting the command table contains NO flash/write/DUT-control command (the boundary is structural — no such command exists)
- [ ] 6.3 Implement the hazard gate in `protocol/`; native tests green

## 7. Hardware layer + main loop (compile-only)

- [ ] 7.1 Implement `firmware/src/hw/` (PIO stimulus for ws2812/dshot/pwm, bit-banged or PIO uart_tx/spi_tx, i2c master scan/read, sync line) and `main.c` (TinyUSB CDC read-line → `protocol/` dispatch → write response). These are compile-verified only
- [ ] 7.2 Verify (runner/CI/human): both targets compile clean

## 8. CI + style

- [ ] 8.1 Add a firmware CI job to `.github/workflows/ci.yml`: install `cmake`, `gcc` (host), and `arm-none-eabi-gcc` via apt (open toolchain only); build+run the native `protocol/` tests; compile `pico` and `pico2` targets. Add `clang-format --dry-run --Werror --style=file` over `firmware/**/*.{c,h}` using the repo `.clang-format`
- [ ] 8.2 Verify (runner/CI/human): the firmware job passes on a clean checkout with no account-walled or Windows-only tools and no attached hardware
- [ ] 8.3 Commit naming the task groups
