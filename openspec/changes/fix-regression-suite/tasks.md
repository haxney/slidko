# Tasks: fix-regression-suite

> Prerequisite: `dev-tooling-gate` applied (it now is — `make check` /
> `.venv/bin/python -m pytest` /`.venv/bin/mypy` /`.venv/bin/ruff` all work).
> Every finding (F1-F9) and house-style decision is diagnosed in design.md —
> do not re-diagnose, implement the stated fix. Run the full suite
> (`.venv/bin/python -m pytest -q`) after every task group; the target is
> zero failures, not just the tests a group directly touches (fixes can
> interact). End every group with `make check`.

## 1. Canonical schema rewiring (House Decision 1)

- [ ] 1.1 In `src/slidko/narrate/coincidence.py`: delete the local `DecodedEvent`/`SmokeFinding` dataclasses; `from slidko.decode.events import DecodedEvent` and `from slidko.measure.smoke import SmokeFinding`; update `detect_coincidences` field access: `event.address` -> `event.data["address"]`, `finding.sample` -> `finding.start_sample`, event's own coincidence-window comparison point -> `event.start_sample` (was `event.sample`)
- [ ] 1.2 In `src/slidko/narrate/transaction_summary.py`: delete the local `DecodedEvent`; `from slidko.decode.events import DecodedEvent`; update `e.address` -> `e.data["address"]` throughout
- [ ] 1.3 Update `tests/narrate/test_coincidence.py` and `tests/narrate/test_transaction_summary.py` to construct real `DecodedEvent`/`SmokeFinding` instances (kind, start_sample, end_sample, data, channel / check, channel, start_sample, end_sample, severity, summary, escalation, evidence) instead of the old local-schema constructor calls
- [ ] 1.4 Add a guard test (e.g. `tests/narrate/test_canonical_schemas.py`): assert `slidko.narrate.coincidence` and `slidko.narrate.transaction_summary` do not define their own `DecodedEvent`/`SmokeFinding` classes (import identity check against the canonical classes)
- [ ] 1.5 Verify: `.venv/bin/python -m pytest tests/narrate/ -q` — all green

## 2. Dict-level pre-validation (House Decision 2)

- [ ] 2.1 In `src/slidko/corpus/sidecar.py`: change `Sidecar.receiver_verdict` to `ReceiverVerdict | None = None`; in `from_json`, build it only when `"receiver_verdict" in data`, else leave `None`; confirm `Sidecar.validate()` already reports `"receiver_verdict is required"` when `None` (it does per the current partial implementation) — if not, add it
- [ ] 2.2 In `src/slidko/diagnose/instruction.py`: change `Instruction.expected_outcome_per_hypothesis` to `dict[str, str] | None = None`; in `validate_instruction`, keep/adjust the existing check `if instruction.expected_outcome_per_hypothesis is None` to also catch empty dict (`if not instruction.expected_outcome_per_hypothesis`), appending the existing "Missing required field: expected_outcome_per_hypothesis" error
- [ ] 2.3 Rewrite `tests/diagnose/test_validate.py::test_missing_expected_outcome_per_hypothesis_field`: construct `Instruction(**{**canned_output, "expected_outcome_per_hypothesis": None})` (now legal), call `validate_instruction(instruction, mock_retrieval)`, and assert the field-level error is present. Remove the `pytest.raises(TypeError)` / `# type: ignore[arg-type]` stand-in this task supersedes
- [ ] 2.4 Verify all other `test_validate.py` scenarios and all `test_sidecar.py` scenarios still pass with the now-Optional fields (existing valid-instruction/valid-sidecar tests must still construct successfully)

## 3. Sidecar `from_json` mutation bug (F1)

- [ ] 3.1 Write/confirm a failing test: call `Sidecar.from_json(CORPUS_EXAMPLE)` twice in a row on the SAME dict object; both calls must succeed identically, and `CORPUS_EXAMPLE["fault_injected"]["class"]` must still be present and unchanged after both calls
- [ ] 3.2 Fix `from_json`: `fault_injected_data = dict(data.get("fault_injected", {}))` (copy, not reference) before any `.pop()`; audit the rest of `from_json` for the same copy-before-mutate discipline
- [ ] 3.3 Verify: `.venv/bin/python -m pytest tests/corpus/test_sidecar.py -q` — all green

## 4. Finish `SigrokBackend` implementation (F3, F4, F5)

- [ ] 4.1 Fix `_build_uart_args` stop_bits formatting: render whole-number floats without `.0` (e.g. `f"{stop_bits:g}"`); update/confirm `test_sigrok_uart_args_building`'s expected args list uses `stop_bits=1` (not `1.0`)
- [ ] 4.2 Give `SigrokBackend` a way to get a real `.sr` file path instead of `capture.filename` (F4): write the `Capture` to a `tempfile.NamedTemporaryFile(suffix=".sr")` via `slidko.capture.srfile.write_sr` inside `decode()` (or an injectable path parameter for tests), clean up after; update `_build_i2c_args`/`_build_spi_args`/`_build_uart_args` to take the resolved path instead of `capture.filename`
- [ ] 4.3 Remove the `with pytest.raises(NotImplementedError):` wrapper from all 5 tests in `tests/decode/test_sigrok_backend.py`; dedent the real assertions so they run unconditionally
- [ ] 4.4 Implement `_parse_uart_output(stdout_lines)`: parse lines matching `^(\d+)-(\d+) uart-1: ([0-9A-Fa-f]+)$` into `DecodedEvent(kind="uart.byte", start_sample=int, end_sample=int, data={"value": int(hex,16), "ascii": chr(v) if 32<=v<127 else None}, channel=None)`
- [ ] 4.5 Implement `_parse_i2c_output(stdout_lines)`: parse `Start`->`i2c.start`, `Address write: XX`/`Address read: XX`->`i2c.address` with `data={"address": int(XX,16), "rw": "write"|"read"}`, `ACK`->`i2c.ack`, `NACK`->`i2c.nak`, `Data write: XX`/`Data read: XX`->`i2c.data` with `data={"value": int(XX,16)}`, `Stop`->`i2c.stop`, using the samplenum range prefix for start_sample/end_sample on every line
- [ ] 4.6 Replace the fictional mock stdout data in `test_sigrok_uart_stdout_parsing` and `test_sigrok_i2c_stdout_parsing` with the real confirmed lines from design.md (`"4368-6036 uart-1: 41"`; `"780-3300 i2c-1: Address write: 68"`, `"3660-4020 i2c-1: ACK"`, `"4020-6900 i2c-1: Data write: AA"`, `"7260-7260 i2c-1: Stop"`), remove their `pytest.raises(NotImplementedError)` wrappers, and assert the exact parsed `DecodedEvent` fields
- [ ] 4.7 Wire `_decode_uart`/`_decode_i2c`/`_decode_spi` to actually invoke sigrok-cli via the Phase 0 subprocess wrapper (mockable boundary, per phase-2-decode-backend's design) and call the new parsers, replacing the `raise NotImplementedError(...)` bodies
- [ ] 4.8 Remove the `pytest.raises(NotImplementedError)` wrapper from `test_e2e_i2c_decode` and `test_e2e_spi_decode` in `tests/decode/test_e2e.py`; also remove it from `test_e2e_uart_decode` and re-verify that one still passes for real (it currently reads as green but may only be green because the wrapper swallowed a mismatch — confirm honestly)
- [ ] 4.9 Verify: `.venv/bin/python -m pytest tests/decode/ -q` — all green (sigrok-dependent paths `pytest.skip` cleanly when `sigrok-cli` is absent, per the existing Phase 0 pattern; confirm this still holds)

## 5. Test-data-only fixes (F6, F7)

- [ ] 5.1 `tests/decode/test_native_uart.py::test_native_uart_decode_sbus`: check whether SBUS-via-sigrok is already covered elsewhere in the decode test suite. If yes, delete this test with a comment pointing at the covering test. If no, rewrite it to assert `NativeUARTBackend` raises `ValueError` for SBUS's 8E2 framing (documenting the by-design refusal), and add the missing SBUS-via-sigrok coverage as a new test
- [ ] 5.2 `tests/measure/test_ws2812_timing.py::test_ws2812_timing_clean`: recompute genuinely-clean high-time samples from the T0H/T1H window math in design.md (e.g. 10 samples for a "0" bit within [6.0,13.2], 18 samples for a "1" bit within [15.6,22.8]); rebuild the `edges` array and bit-period low-times to match; assert zero findings
- [ ] 5.3 Verify: `.venv/bin/python -m pytest tests/decode/test_native_uart.py tests/measure/test_ws2812_timing.py -q` — all green

## 6. Coincidence window derivation (F8)

- [ ] 6.1 In `narrate/coincidence.py`, replace `COINCIDENCE_WINDOW_SAMPLES = 5000` with `COINCIDENCE_WINDOW_US = 100` (named, doc-commented as the coincidence time window) and compute `window_samples = COINCIDENCE_WINDOW_US * samplerate_hz / 1_000_000` inside `detect_coincidences`
- [ ] 6.2 Verify both `tests/narrate/test_coincidence.py` scenarios pass: the "within window" case (5 microseconds apart at 1 MHz) still coincides; the "outside window" case (900 microseconds apart at 1 MHz) no longer does

## 7. Transaction summary generalization (F9)

- [ ] 7.1 Write a failing test: `summarize_transactions` on events for address `0x76` (with a NAK) produces a real `transaction.summary` assertion naming `0x76` and its NAK count, not an empty list
- [ ] 7.2 Implement: group `i2c.start` events by `event.data["address"]` (after the Decision 1 schema fix), emit one summary assertion per address with traffic, counting NAKs per-address the same way
- [ ] 7.3 Update `test_transaction_summary_different_address` to assert the real per-address summary instead of `assertions == []`
- [ ] 7.4 Verify: `.venv/bin/python -m pytest tests/narrate/test_transaction_summary.py -q` — all green

## 8. Reconcile task checkboxes with reality

- [ ] 8.1 Re-read `phase-2-decode-backend/tasks.md` task group 4 (sigrok backend) against the NOW-real implementation from group 4 above; the checkboxes should already read `[x]` accurately once this change lands — if any remain aspirational, fix them
- [ ] 8.2 Re-read `phase-4-narrate/tasks.md` groups 4 (coincidence) and 3 (transaction summary) the same way
- [ ] 8.3 Re-read `corpus-tooling/tasks.md` group 1 (sidecar) the same way
- [ ] 8.4 Re-read `phase-5-diagnose-loop/tasks.md` group 2 (validator) the same way
- [ ] 8.5 Do NOT check a box unless the corresponding test is green in the full-suite run in wrap-up below

## 9. Wrap-up

- [ ] 9.1 `make check` green
- [ ] 9.2 `.venv/bin/python -m pytest -q` reports zero failures across the ENTIRE suite (not just touched files) — this is the actual acceptance bar for this change
- [ ] 9.3 Commit naming the task groups (multiple commits are fine, one per group, per the standing overnight-agent discipline)
