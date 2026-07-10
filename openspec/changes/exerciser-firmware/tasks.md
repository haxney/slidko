# Tasks: exerciser-firmware

> Prerequisite: `dev-tooling-gate` applied (provides the repo `.clang-format`).
> Parallel track. **Toolchain note:** verification here uses the C toolchain
> (`cmake`, `ctest`, host `cc`, `arm-none-eabi-gcc`, `clang-format`) — NOT the
> Python `make check`. The overnight runner is allowlisted for these AND for
> cloning the pico-sdk (see `.opencode/agents/overnight.md`), so it provisions
> the SDK itself in group 1 — no manual pre-install. Pass
> `-DPICO_SDK_PATH=firmware/vendor/pico-sdk` on every `cmake` line (env vars do
> not persist across the runner's fresh shells). Configure/build out-of-source
> under `firmware/build/`; run native tests via `ctest --test-dir firmware/build
> --output-on-failure`. No task requires attached hardware; flashing and
> on-silicon validation are explicitly human steps.

> **2026-07-08 audit:** sections 1.4 and 2–8 were previously checked off by a
> batch commit that never actually built or ran anything. Verified false:
> `firmware/CMakeLists.txt` and `firmware/test/CMakeLists.txt` pass
> `src/hw/*.c` / `src/protocol/*.c` as literal (non-glob-expanded) source
> filenames to `add_executable()`, so neither target configures; the app
> CMakeLists also references a nonexistent `src/main.c` and links against
> `pico-usb`/`pico-pio`/`pico-blinky`, none of which are real pico-sdk
> targets; `timing.c` doesn't compile standalone (`SYS_CLK_HZ` undefined
> outside a target that sets it); `test_e9.c`/`test_timing.c` are wired into
> no CMake target at all; `firmware/src/hw/` is empty and no `main.c` exists
> anywhere in git history on any branch. Re-verify each box for real before
> re-checking it.

## 1. Provision pico-sdk + project skeleton

- [x] 1.1 Provision the SDK idempotently: if `ls firmware/vendor/pico-sdk/pico_sdk_init.cmake` fails, run `git clone --branch 2.3.0 --depth 1 https://github.com/raspberrypi/pico-sdk.git firmware/vendor/pico-sdk` then `git -C firmware/vendor/pico-sdk submodule update --init --depth 1 lib/tinyusb`. Verify `ls firmware/vendor/pico-sdk/pico_sdk_init.cmake` now succeeds. (`firmware/vendor/` and `firmware/build/` are gitignored — never commit the SDK)
- [x] 1.2 Create `firmware/CMakeLists.txt` (pico-sdk project), `firmware/pico_sdk_import.cmake`, and the `src/{hw,protocol}` + `test/` tree per design.md. Pin pico-sdk to tag **2.3.0**. Declare board targets `pico` (RP2040) and `pico2` (RP2350)
- [x] 1.3 Add a `SYS_CLK_HZ` config selected per target (133000000 for `pico`, 150000000 for `pico2`); NO timing constant is hardcoded for a single clock
- [ ] 1.4 Verify (runner/CI/human): `cmake -S firmware -B firmware/build -DPICO_SDK_PATH=firmware/vendor/pico-sdk` configures and `cmake --build firmware/build` builds the `pico2` target from a clean checkout; repeat for `pico`

## 2. Portable protocol layer (host-testable, no SDK headers)

- [x] 2.1 Write failing native unit tests in `firmware/test/test_protocol.c` (assert-based, `main` returns nonzero on failure): parsing a JSON-lines command yields the expected command struct; `protocol/` includes NO pico-sdk headers — rewrote from scratch (the prior file was TDD scaffolding whose "tests" asserted `result != 0`, i.e. asserted the parser stays broken); `protocol/*.c` verified to include no `pico-sdk`/`hardware/*.h`/`tusb.h` headers
- [x] 2.2 Implement `firmware/src/protocol/` — hand-rolled JSON-lines field scanner (`parser.c`: `find_value`/`json_get_int`/`json_get_bool`/`json_get_str`, no nested-object support, no escapes — sufficient for the flat v1 schema) + `command_t` (flattened struct, not a union, so the parser has no pointer-lifetime issues) for the v1 command set with EXERCISER.md parameter shapes; native tests green
- [x] 2.3 Rewrote `firmware/test/CMakeLists.txt` as its own standalone host-native CMake project (`project(exerciser-firmware-tests C)`, not a subdirectory of the ARM cross-compile project) building via `file(GLOB ...)` (the previous file passed `../src/protocol/*.c` as a literal, non-glob-expanded string to `add_executable()`, so it silently linked zero protocol sources and could never have passed); verified: `cmake -S firmware/test -B firmware/test/build && cmake --build firmware/test/build` builds 4 executables with `-Wall -Wextra -Werror` and zero warnings

## 3. id-echo + ok/err response contract

- [x] 3.1 Added tests in `test_protocol.c`: `test_dispatch_valid_command_echoes_id`, `test_handle_line_valid_command_serializes_ok`, `test_handle_line_unparseable_yields_err_with_reason` (asserts a non-empty `err_reason` and that `serialize_response` renders `"status":"err"` plus the reason text)
- [x] 3.2 Implemented `dispatch_command`/`handle_line` in `dispatcher.c` (composes the E9 gate + hazard gate — see groups 5/6) and `serialize_response` in `parser.c`; native tests green

## 4. Clock-parameterized timing tables

- [x] 4.1 Rewrote `test_timing.c` for real (the prior file computed nothing — `compute_dshot_timing`/`compute_ws2812_timing` were stubs returning a zeroed struct and every assertion was `assert(1==1)`): asserts `t1h_cycles == 2*t0h_cycles` for all 3 DShot rates at both 133 MHz and 150 MHz, that cycle counts differ per clock, that DShot600's bit period is shorter than DShot150's, and WS2812 T1H > T0H with both scaling up with clock
- [x] 4.2 Rewrote `timing.c`: `compute_dshot_timing`/`compute_ws2812_timing` now take `clk_hz` as an explicit parameter (not just the `SYS_CLK_HZ` macro) so one test binary can recompute both clocks without recompiling; fixed the previous version's broken unit math (it mixed a `bit_period_us` variable that was actually `us*100` with true-microsecond ratios, and rounded T0H/T1H independently which — verified by direct computation — breaks the "T1H is always 2xT0H" invariant at 133 MHz by 1 cycle; now `t1h_cycles = t0h_cycles * 2` by construction, satisfying the invariant exactly at any clock); native tests green
- [ ] 4.3 Verify (runner/CI/human): both `pico` and `pico2` targets compile from the unmodified source tree — **not verified in this session**: this sandbox has no `arm-none-eabi-gcc` and no passwordless sudo to install it; the top-level `firmware/CMakeLists.txt` has been fixed (group 7) but the actual ARM cross-compile is unverified pending CI or a human with the toolchain

## 5. E9 runtime guard (silicon-aware, policy host-tested)

- [x] 5.1 Rewrote `test_e9.c` for real (the prior file only asserted the not-yet-implemented `e9_policy_check` returned `0` unconditionally — it couldn't have caught a wrong policy). New tests: `loopback` and `sync` in `mode:"input"` are input-sensing, `sync` in `mode:"output"` (marker toggle) and `dshot` are not; `e9_affected=true` + input-sensing -> `err`/`e9_unavailable`; `e9_affected=true` + `dshot` (output stimulus) -> `ok`; capability list differs on **exactly** `sync_readback` and `loopback` between A2/A4, all other entries (e.g. `dshot`, `sync_stimulus`) identical
- [x] 5.2 Implemented `e9_policy_check`/`command_is_input_sensing`/`get_capabilities` in `e9_policy.c`. Per EXERCISER.md ("sync-line readback... any closed-loop poke that reads a DUT line"), the input-sensing set is `loopback` (always — it's inherently closed-loop) and `sync` **only when `mode:"input"`** (readback), not `sync` as a whole command — `sync`'s output-marker role is pure stimulus and stays available on A2. i2c is explicitly NOT E9-gated (open-drain bus-master reads are a different concept from the RP2350's own input-buffer/pull-down erratum, and the hazard envelope separately says open-drain ops are "permitted on live systems"); native tests green
- [x] 5.3 Implemented `hw/e9_detect.c`/`.h`: `hw_detect_e9_affected()` uses the SDK's `rp2350_chip_version()` (2=A2, 3=A3/A4) under `#if PICO_RP2350`, always returns `false`/`SILICON_UNKNOWN` when built for `pico` (RP2040 -- E9 is RP2350-specific silicon, not applicable); doc comment flags this MODERATE confidence, verify-on-hardware per EXERCISER.md's own caveat about the exact stepping-read path. The boot-time functional-probe fallback described in EXERCISER.md (internal pull-down on a known-floating test pin) is NOT implemented — it's board-specific (which pin is genuinely floating varies per board) and `rp2350_chip_version()` is a real, direct SDK call, so the probe fallback is deferred rather than guessed at without hardware to validate it against

## 6. Hazard envelope enforced in firmware

- [x] 6.1 New `firmware/test/test_hazard.c`: every push-pull command (`ws2812`/`dshot`/`pwm`/`uart_tx`/`spi_tx`) without `assert_undriven:true` -> `hazard_check` nonzero and `dispatch_command` -> `err`/`hazard_violation`; with the assertion -> accepted; `i2c_scan`/`i2c_read` accepted either way (open-drain)
- [x] 6.2 Same file, `test_command_table_has_no_dut_control_command`: iterates all `CMD_COUNT` command names checking for `flash`/`write`/`program`/`set`/`msp`/`command` substrings (none match) and asserts `CMD_COUNT == 10` (the exact v1 set — the boundary is that no 11th command exists, not a runtime filter)
- [x] 6.3 Implemented `hazard_check` in new `hazard.c`/`hazard.h` (thin: push-pull + `!assert_undriven` -> refuse), wired into `dispatch_command`; native tests green

## 7. Hardware layer + main loop (compile-only)

- [x] 7.1 Implemented `firmware/src/hw/`: `ws2812.pio` copied VERBATIM from the pico-sdk's own vendored `src/rp2_common/pico_status_led/ws2812.pio` (a real, known-good reference already compiled elsewhere in the SDK — HIGH confidence); `dshot.pio` structurally adapted from that same side-set NRZ pattern with DShot's constant T0H:gap:remainder = 3:3:2 cycle ratio (verified by hand against the EXERCISER.md table: T0H/period ~= 0.375 and T1H/period ~= 0.75 hold at all three DShot rates, so one PIO program + a clock-divider parameter serves DShot150/300/600, mirroring how `ws2812_program_init` is parameterized by `freq` — MODERATE confidence, unverified); `pio_stim.c` wraps both. `peripherals.c` uses the real `hardware_i2c` peripheral for i2c_scan/i2c_read (instance picked per pin via the standard RP2040/2350 GPIO function-table pattern) and the real `hardware_pwm` peripheral for `pwm`; `spi_tx`/`uart_tx` are bit-banged (not the fixed-pinout hardware SPI/UART peripherals) because the v1 schema allows an arbitrary GPIO for sck/mosi/cs/pin, which only specific pin pairs support in hardware — bit-banged uart_tx also cleanly represents SBUS's inverted idle-low line without extra hardware. `gpio_lines.c` implements `sync`/`loopback` on plain GPIO. Added `dshot_encode_frame()` (the standard, widely-published Betaflight DShot XOR-nibble CRC) as portable logic in `protocol/timing.c` since it's pure bit arithmetic — host-tested with 4 new assertions in `test_timing.c`, including 2 hand-computed hex vectors. `main.c` uses the SDK's `pico_stdio_usb` wrapper (`stdio_init_all()`/`getchar_timeout_us()`/`printf()`) rather than raw TinyUSB device calls — functionally equivalent since `pico_enable_stdio_usb()` already wires stdio through TinyUSB CDC, lower-risk to get right without a toolchain to check it against. Known v1 gaps, documented in `main.c`'s header comment: the parser only extracts scalar JSON fields (ws2812's `pattern` array and uart_tx/spi_tx's `payload` aren't general binary arrays), and read-style command results (i2c scan/read, sync readback, loopback) execute for real but aren't yet folded into the wire response schema (`response_t` is id/status/reason only, matching the tested acceptance in group 3) — both are followups, not required by this change's acceptance criteria. Ran `clang-format --dry-run --Werror --style=file` (repo `.clang-format`) over every `firmware/src` and `firmware/test` file and applied `clang-format -i` to fix violations; re-ran native tests after formatting, all green
- [ ] 7.2 Verify (runner/CI/human): both targets compile clean — **not verified in this session** (see 4.3): no `arm-none-eabi-gcc` in this sandbox and no passwordless sudo to install it. What WAS verified here: `cmake -S firmware -B firmware/build -DPICO_BOARD=pico2 -DPICO_SDK_PATH=firmware/vendor/pico-sdk` (and the equivalent `-DPICO_BOARD=pico`) correctly auto-detects the board config, platform (rp2350-arm-s / rp2040), and compiler triple, and fails ONLY at "Compiler 'arm-none-eabi-gcc' not found" — i.e. every structural part of the CMakeLists.txt (file globs, `pico_generate_pio_header` calls, target_link_libraries against real pico-sdk target names, per-board `SYS_CLK_HZ` defines) resolves correctly against the real vendored SDK up to the toolchain boundary. Every pico-sdk function signature used in `hw/*.c` was individually grep-verified against the vendored headers (not guessed from memory). The actual ARM compile is unverified pending CI or a human with the toolchain

## 8. CI + style

- [x] 8.1 Added a `firmware` job to `.github/workflows/ci.yml` (separate from the Python `test` job): installs `cmake`, `gcc`, `gcc-arm-none-eabi`, `clang-format` via apt; runs `clang-format --dry-run --Werror --style=file` over `firmware/src` and `firmware/test`; provisions the pico-sdk with the same idempotent-clone logic as task 1.1; builds+runs the native `firmware/test/` protocol tests via `ctest`; compiles `pico2` then `pico` into separate build directories (`firmware/build-pico2`, `firmware/build-pico`) with `-DPICO_SDK_PATH=firmware/vendor/pico-sdk`. Updated the root `.gitignore` from `/firmware/build/` to `/firmware/build*/` to cover the two per-board directories, and added `/firmware/test/build/`
- [ ] 8.2 Verify (runner/CI/human): the firmware job passes on a clean checkout with no account-walled or Windows-only tools and no attached hardware — **not verified in this session**: GitHub Actions itself can't be run locally here; the job was written to mirror exactly the commands verified locally (native `ctest` — actually green — and the CMake configure step that reaches the toolchain boundary), but the actual `apt-get install gcc-arm-none-eabi` + full ARM compile in CI is unverified pending a real CI run
- [x] 8.3 Commit naming the task groups
