# Tasks: exerciser-protobuf-wire

> Prerequisite: `dev-tooling-gate` applied (repo `.clang-format`, ruff/mypy).
> **Toolchain note:** verification here spans BOTH toolchains — the C side
> (`cmake`, `ctest`, host `cc`, `arm-none-eabi-gcc`, `clang-format`) and the
> Python side (`make check`). Plus a new codegen dependency: the **nanopb
> generator** (`nanopb_generator.py` + runtime `pb_encode.c`/`pb_decode.c`/
> `pb_common.c`) and `protoc` (or nanopb's bundled descriptor path). Vendor
> nanopb into a gitignored, repo-relative path and provision it idempotently,
> exactly like the pico-sdk (task 1.1); pass its location to CMake explicitly.
> Pass `-DPICO_SDK_PATH=firmware/vendor/pico-sdk` on every `cmake` line.
> No task requires attached hardware; flashing and on-silicon validation stay
> explicitly human steps. This change swaps the **codec only** — E9, hazard,
> timing, and capability *policy* logic is preserved, not rewritten.

## 1. Canonical schema + codegen provisioning

- [ ] 1.1 Provision nanopb idempotently into `firmware/vendor/nanopb` (gitignored): if the generator/runtime is absent, clone the pinned nanopb release; skip when present. Record the pinned version in design/notes. Verify the generator and `pb_encode.c`/`pb_decode.c`/`pb_common.c` are on disk.
- [ ] 1.2 Author the canonical `firmware/proto/exerciser.proto`: `Command`/`Response` `oneof` envelopes, one message per v1 command (`Info`, `Ws2812`, `Dshot`, `Pwm`, `UartTx`, `I2cScan`, `I2cRead`, `SpiTx`, `Sync`, `Loopback`), response variants (`Ok`, `Error`, `I2cScanResult`, `I2cReadResult`, `Info`), and `enum ErrorReason`. Field shapes per docs/EXERCISER.md; `payload` fields are `bytes`. Add a nanopb `.options` file sizing every `bytes`/`repeated` field from the existing `COMMAND_MAX_*` constants in `command.h` so buffers are identical.
- [ ] 1.3 Wire codegen into CMake: generate `exerciser.pb.{c,h}` (nanopb) at configure time into the build tree; the app and native-test targets compile the generated sources + nanopb runtime. Generate Python bindings into `src/slidko/` (or a generated subpackage) for the host. Both from the one `.proto`.

## 2. Firmware protocol layer: decode + dispatch (host-testable)

- [ ] 2.1 Rewrite `firmware/test/test_protocol.c` to assert **encode/decode round-trips**, not JSON strings: decoding a `Command` yields the expected fields for `info`/`dshot`/`i2c_read`/`sync`(input); malformed/truncated bytes fail cleanly; an unknown `oneof` tag is rejected. Assert `protocol/` (generated + adapter) includes no pico-sdk/`hardware/*.h`/`tusb.h`.
- [ ] 2.2 Replace `parser.c` with a thin `dispatch.c` adapter over the generated types: decode a length-prefixed `Command` → the existing dispatch/E9/hazard gates (unchanged) → encode a `Response`. Retire the hand-rolled JSON scanner. Framing: fixed 2-byte LE length prefix (not `pb_encode_delimited`). Native tests green.
- [ ] 2.3 Binary-payload regression: a `uart_tx`/`spi_tx` `payload` containing `0x00` and `0x22` round-trips byte-exact (the bug the old string-based parser could not represent). Native test green.

## 3. id-echo + ok/err contract, now typed

- [ ] 3.1 Tests: a valid `Command{id:42}` → `Response{id:42, ok}`; a push-pull command without `assert_undriven` → `Response{error, ErrorReason=HAZARD_VIOLATION}`; an input-sensing command with `e9_affected` → `ErrorReason=E9_UNAVAILABLE`; unparseable bytes → `ErrorReason=PARSE_ERROR`. (Reuses the group-5/6 policy from the firmware change — assert the enum, not a string.)
- [ ] 3.2 Update `dispatcher.c`/response encoding to emit the `ErrorReason` enum and the `id`-echoing `Response`; delete `err_reason` string plumbing. Native tests green.

## 4. Typed response payloads (close the main.c gap)

- [ ] 4.1 Tests: `i2c_scan` with simulated responders at 0x68/0x76 → `I2cScanResult` carrying both; `i2c_read` → `I2cReadResult{data=bytes}` matching the read buffer; `info` → `Info` variant with stepping + E9 posture + a capability list that differs on exactly the input-sensing entries between A2/A4.
- [ ] 4.2 Wire the real `hw_i2c_scan`/`hw_i2c_read`/`get_capabilities` results into the encoded `Response` (previously executed but dropped — see `main.c` header). `print_info_response`'s hand-built JSON is replaced by encoding the `Info` message. Native tests green.

## 5. main loop: framed protobuf over CDC (compile-only)

- [ ] 5.1 Replace the newline-delimited `getchar` line reader in `main.c` with a length-prefixed frame reader (read 2-byte LE length, then N bytes into a bounded buffer sized by the generated `Command_size` macro; overlong/again-timeout handling preserved). Dispatch → encode `Response` → write `[len][bytes]`. Compile-verify both `pico` and `pico2` targets, zero warnings.
- [ ] 5.2 Verify both targets build from unmodified sources with codegen in the loop (`exerciser.pb.c` generated, not committed). `.elf`/`.uf2` produced for each. Grep the build log clean of warnings.

## 6. Host codec (Python, hardware-free)

- [ ] 6.1 Failing tests in `tests/` (or `tests/exerciser/`): a `slidko` codec module frames + encodes a `Command` and decodes a `Response` using the generated Python bindings; a length-prefix framer splits a concatenated byte stream into messages and resyncs on a partial trailing frame. Transport is a stub/mock (no pyserial).
- [ ] 6.2 Implement the codec + framing layer (protobuf decode → length framing → transport adapter interface, per design.md layering). Only the codec + framing land now; the real pyserial/pyftdi transport is left to the host-client work. `make check` green.

## 7. Cross-language golden round-trip (contract lock)

- [ ] 7.1 A golden test that encodes a representative `Command`/`Response` set in Python, feeds the bytes to a small native C decoder harness (and vice versa), and asserts identical field recovery — so the nanopb and Python generators can never silently diverge. Wire it into both the C (`ctest`) and Python (`make check`) sides, or a dedicated CI step. No hardware.

## 8. Docs, spec, CI

- [ ] 8.1 Update docs/EXERCISER.md "Command interface": JSON-lines → length-delimited protobuf; note the canonical `.proto`, the `bytes` payload, the typed `ErrorReason`, and the framing/no-CRC-over-USB rationale (point to this change's design.md for the full reasoning incl. the deferred pod data-plane record).
- [ ] 8.2 Add nanopb provisioning + codegen to the CI `firmware` job (mirror the pico-sdk idempotent-clone) and Python-binding generation to the `test` job; run the cross-language golden as a gate. Both jobs stay headless, open-toolchain, no attached hardware. Update `.gitignore` for `firmware/vendor/nanopb` and generated `*.pb.{c,h}`/Python bindings.
- [ ] 8.3 Commit naming the task groups; `openspec validate exerciser-protobuf-wire --strict` clean.
