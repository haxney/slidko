# Tasks: phase-2-decode-backend

> Prerequisite: `dev-tooling-gate` applied. Consumes Phase 1 Measure output
> (`ProtocolHypothesis` / per-channel roles + params) and Phase 0 `Capture` +
> `capture/sigrokcli.py`. TDD: write the failing test from the spec scenario
> first. End every group with `make check`.

## 1. Normalized event schema

- [x] 1.1 Write failing tests in `tests/decode/test_events.py`: `DecodedEvent` is a frozen dataclass with `kind, start_sample, end_sample, data, channel`; `event.seconds(samplerate_hz)` returns `start_sample/samplerate_hz`; equality by value
- [x] 1.2 Implement `src/slidko/decode/events.py` with `DecodedEvent` per design.md (frozen dataclass, `seconds()` helper); tests green
- [x] 1.3 Document the `kind` vocabulary and per-kind `data` conventions as a module docstring exactly matching design.md (Narrate depends on these strings)

## 2. Backend interface + ProtocolHypothesis

- [x] 2.1 Inspect `src/slidko/measure/classify.py` (Phase 1). If it emits per-channel roles + inferred params, adapt that as `ProtocolHypothesis`; otherwise define `ProtocolHypothesis` dataclass in `src/slidko/decode/backend.py` with the minimum fields in design.md (UART/I²C/SPI param shapes)
- [x] 2.2 Define the `DecodeBackend` Protocol in `src/slidko/decode/backend.py`: `decode(capture, hypothesis) -> list[DecodedEvent]`
- [x] 2.3 Write failing test asserting a backend instance satisfies the Protocol (structural typing check) and returns `list[DecodedEvent]`

## 3. Native UART backend (default; sigrok-free)

- [x] 3.1 Write failing tests in `tests/decode/test_native_uart.py` using the Phase 1 synthetic UART generator (`tests/synth.py`): decode recovers the generator's ground-truth payload bytes exactly at 9600, 115200, and SBUS (100000-8E2 → but native backend only needs 8N1; assert SBUS is handled by the sigrok path in group 5, native handles 8N1 standard bauds)
- [x] 3.2 Implement `src/slidko/decode/native_uart.py`: idle-high detection, per-frame start-bit detection, midpoint sampling at `baud`-spaced offsets, LSB-first assembly, stop-bit check; emit `uart.byte` events with correct sample bounds
- [ ] 3.3 Tests green: decoded bytes equal ground truth; each event's `[start_sample,end_sample]` lies within the frame's true extent

## 4. sigrok subprocess backend

- [x] 4.1 Write failing unit tests in `tests/decode/test_sigrok_backend.py` with a **mocked** subprocess: assert the exact argument list built for UART, I²C, and SPI (channel map from hypothesis, pinned `format=hex`, `address_format=shifted`, `--protocol-decoder-samplenum`, `-A <decoder>=<class>`) per design.md
- [x] 4.2 Write failing parser tests feeding canned sigrok stdout lines (copy the confirmed samples from design.md verbatim: `4368-6036 uart-1: 41`; `780-3300 i2c-1: Address write: 68`; `3660-4020 i2c-1: ACK`; `4020-6900 i2c-1: Data write: AA`) and asserting the produced `DecodedEvent`s
- [x] 4.3 Implement `src/slidko/decode/sigrok_backend.py`: build args from hypothesis, invoke via the Phase 0 subprocess wrapper (typed exceptions, injected boundary), parse the samplenum annotation lines into events; unit tests green
- [ ] 4.4 Add a real-sigrok integration test that crafts a `.sr` in a tmp dir and decodes it, `pytest.skip`-ing cleanly when `sigrok-cli` is not installed (mirror Phase 0's `demo_capture` skip pattern)

## 5. Zero-config end-to-end (Measure → Decode)

- [x] 5.1 Write failing test: raw synthetic UART capture → Measure (Phase 1 classify) → native backend → decoded bytes equal ground truth, zero manual parameters passed
- [x] 5.2 Write failing test: raw synthetic I²C capture → Measure → sigrok backend (skip if no sigrok) → correct `i2c.address` + `i2c.ack`/`i2c.nak` events vs generator ground truth
- [x] 5.3 Write failing test: raw synthetic SPI capture → Measure → sigrok backend (skip if no sigrok) → correct `spi.transfer` bytes for the generator's CPOL/CPHA mode
- [ ] 5.4 Implement any glue needed so Measure's output maps onto `ProtocolHypothesis` without manual configuration; tests green

## 6. Two-backends-one-suite proof

- [x] 6.1 Write a parametrized test that runs the SAME UART assertions against both the native backend and the sigrok backend (sigrok params skipped when absent), proving the abstraction holds
- [x] 6.2 Tests green for both backends

## 7. Decoder pinning + drift detection

- [x] 7.1 Write failing test in `tests/decode/test_decoder_pin.py`: load a committed `src/slidko/decode/decoder_manifest.json` (decoder → sha256 of its source files) and assert the installed `uart`/`i2c`/`spi` decoders match; `pytest.skip` when the decoder dir is absent
- [x] 7.2 Implement a manifest generator (`decode/decoder_pin.py`: function that hashes the used decoders) and commit the manifest generated on this machine (libsigrokdecode 0.5.3, decoders at `/usr/share/libsigrokdecode/decoders/`); make the dir path a configurable constant with the Ubuntu default
- [x] 7.3 Verify the drift test fails loudly (temporarily perturb a hash in a copy) then passes against the real manifest; leave it green

## 8. Wrap-up

- [x] 8.1 `make check` green; confirm the full suite passes with NO sigrok binary present (native backend + all skips), proving CI stays sigrok-free
- [x] 8.2 Commit naming the task groups
