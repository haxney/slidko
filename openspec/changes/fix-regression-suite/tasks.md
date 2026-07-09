# Tasks: fix-regression-suite

> Prerequisite: `dev-tooling-gate` applied (it now is — `make check` /
> `.venv/bin/python -m pytest` /`.venv/bin/mypy` /`.venv/bin/ruff` all work).
> Every finding (F1-F9) and house-style decision is diagnosed in design.md —
> do not re-diagnose, implement the stated fix. Run the full suite
> (`.venv/bin/python -m pytest -q`) after every task group; the target is
> zero failures, not just the tests a group directly touches (fixes can
> interact). End every group with `make check`.

## 1. Canonical schema rewiring (House Decision 1)

- [x] 1.1 In `src/slidko/narrate/coincidence.py`: delete the local `DecodedEvent`/`SmokeFinding` dataclasses; `from slidko.decode.events import DecodedEvent` and `from slidko.measure.smoke import SmokeFinding`; update `detect_coincidences` field access: `event.address` -> `event.data["address"]`, `finding.sample` -> `finding.start_sample`, event's own coincidence-window comparison point -> `event.start_sample` (was `event.sample`) — already done in an earlier session (predates this apply pass)
- [x] 1.2 In `src/slidko/narrate/transaction_summary.py`: delete the local `DecodedEvent`; `from slidko.decode.events import DecodedEvent`; update `e.address` -> `e.data["address"]` throughout — already done
- [x] 1.3 Update `tests/narrate/test_coincidence.py` and `tests/narrate/test_transaction_summary.py` to construct real `DecodedEvent`/`SmokeFinding` instances — already done (both files pass)
- [x] 1.4 Add a guard test (`tests/narrate/test_canonical_schemas.py`) — already present and passing
- [x] 1.5 Verify: `.venv/bin/python -m pytest tests/narrate/ -q` — all green

## 2. Dict-level pre-validation (House Decision 2)

- [x] 2.1 In `src/slidko/corpus/sidecar.py`: `Sidecar.receiver_verdict` is now `ReceiverVerdict | None = None`; `from_json` builds it only when `data.get("receiver_verdict")` is not `None`; `Sidecar.validate()` already reported the missing-field error
- [x] 2.2 In `src/slidko/diagnose/instruction.py`: `expected_outcome_per_hypothesis` was already `dict[str, str] | None = None`; added the missing `validate_instruction` check (`if not instruction.expected_outcome_per_hypothesis: errors.append(...)`)
- [x] 2.3 Rewrote `tests/diagnose/test_validate.py::test_missing_expected_outcome_per_hypothesis_field` to construct `Instruction(**canned_output)` (legal now) and assert `validate_instruction` reports the field-level error; removed the `pytest.raises(TypeError)` stand-in
- [x] 2.4 Verified: all other `test_validate.py` and `test_sidecar.py` scenarios still pass

## 3. Sidecar `from_json` mutation bug (F1)

- [x] 3.1-3.3 Already fixed in an earlier session (`fault_injected_data = dict(...)` copy-before-pop is already in place); `test_sidecar_round_trip` passes

## 4. Finish `SigrokBackend` implementation (F3, F4, F5)

- [x] 4.1 Fixed `stop_bits` formatting via `_format_stop_bits()` (renders "1" not "1.0"); `test_sigrok_uart_args_building` expects `stop_bits=1`
- [x] 4.2 `SigrokBackend` now writes the `Capture` to a `tempfile.NamedTemporaryFile(suffix=".sr")` via `slidko.capture.srfile.write_sr` inside each `_decode_*` method, cleans up after, and passes the resolved path to `_build_*_args` (renamed their `capture` param to `sr_path: str` — no more `_SigrokInputSource` Protocol workaround)
- [x] 4.3 Removed the `pytest.raises(NotImplementedError)` wrapper from all 5 `test_sigrok_backend.py` tests; real assertions run unconditionally
- [x] 4.4 Implemented `_parse_uart_output` per the confirmed regex/schema
- [x] 4.5 Implemented `_parse_i2c_output` per the confirmed regex/schema (Start/Stop/ACK/NACK/Address/Data)
- [x] 4.6 Replaced fictional mock stdout with the real confirmed lines from design.md in both parser tests
- [x] 4.7 Wired `_decode_uart`/`_decode_i2c`/`_decode_spi` to invoke `subprocess.run` directly (no Phase 0 `capture/sigrokcli.py` wrapper exists in this tree to reuse) through a mockable `_run_sigrok(self, args)` method — unit tests monkeypatch this method rather than requiring real sigrok-cli, since the synthetic captures in `tests/synth.py` are 3-sample placeholders, not protocol-accurate signals real sigrok-cli can decode (confirmed empirically: real sigrok-cli rejects our simplified `capture/srfile.py` `.sr` writer's output with "no input module found for this file" — that writer's sigrok-format-compliance is a separate, deeper gap, out of scope here). Also implemented `_parse_spi_output`, which design.md left unconfirmed — added it by analogy to the uart line format (documented as EMPIRICAL/unconfirmed in a comment) since `test_e2e_spi_decode` needed it
- [x] 4.8 Removed the wrapper from `test_e2e_i2c_decode`/`test_e2e_spi_decode` (now monkeypatch `_run_sigrok` and assert real parsed events); left `test_e2e_uart_decode` untouched — it still asserts `NativeUARTBackend` raises `NotImplementedError`, which is honestly true (native decoder body is still a stub; see note below)
- [x] 4.9 Verified: `.venv/bin/python -m pytest tests/decode/ -q` — all green

Note: `NativeUARTBackend.decode()` itself is still unimplemented (raises `NotImplementedError`) — that's the separate "weekend algorithm" design.md flags as its own scope, not one of F1-F9, and no currently-red test requires it. Left as-is.

## 5. Test-data-only fixes (F6, F7)

- [x] 5.1 No existing SBUS-via-sigrok coverage found; rewrote `test_native_uart_decode_sbus` to assert `NativeUARTBackend.decode()` raises `ValueError` matching `"8N1"` (documents the by-design refusal) rather than adding new sigrok-side SBUS coverage (out of scope for this pass)
- [x] 5.2 Rewrote `test_ws2812_timing_clean`'s fixture to two genuinely-clean bits (10 samples high = "0" bit, 18 samples high = "1" bit) per the T0H/T1H window math; asserts zero findings
- [x] 5.3 Verified: both files green

## 6. Coincidence window derivation (F8)

- [x] 6.1-6.2 Already fixed in an earlier session (`COINCIDENCE_WINDOW_US = 100`, samplerate-derived); both `test_coincidence.py` scenarios pass

## 7. Transaction summary generalization (F9)

- [x] 7.1-7.4 Already fixed in an earlier session (groups by `event.data["address"]`, per-address NAK counting); `test_transaction_summary.py` passes

## 8. Reconcile task checkboxes with reality

- [ ] 8.1 Re-read `phase-2-decode-backend/tasks.md` task group 4 (sigrok backend) against the NOW-real implementation from group 4 above; the checkboxes should already read `[x]` accurately once this change lands — if any remain aspirational, fix them
- [ ] 8.2 Re-read `phase-4-narrate/tasks.md` groups 4 (coincidence) and 3 (transaction summary) the same way
- [ ] 8.3 Re-read `corpus-tooling/tasks.md` group 1 (sidecar) the same way
- [ ] 8.4 Re-read `phase-5-diagnose-loop/tasks.md` group 2 (validator) the same way
- [ ] 8.5 Do NOT check a box unless the corresponding test is green in the full-suite run in wrap-up below

## 9. Ruff-lint debt and test-package import fix

> Surfaced while applying `dev-tooling-gate`: once that change's mypy config
> went green tree-wide, two more classes of downstream drift showed up. Both
> predate this task file and are left for this change since it already owns
> "red suite" / drift cleanup.

- [x] 9.1 Run `.venv/bin/ruff check .` and fix the ~80 findings across `src/`
  and `tests/` (long lines, unused variables, `N806` non-lowercase locals,
  `RUF059` unused-unpacked-variable, `B007` unused loop vars, ambiguous
  unicode chars, import-private-name, etc.) — done: `ruff check .` and
  `ruff format --check .` both exit 0. The 9 `PT012` findings in
  `tests/decode/test_sigrok_backend.py` were fixed mechanically (single
  statement per `pytest.raises` block, aspirational assertions moved to a
  comment) without removing the `NotImplementedError` scaffolding itself —
  task group 4 still owns dedenting these into real assertions once the
  parsers are implemented. `float-equality-comparison` findings in
  `tests/test_intervals.py` and `tests/capture/test_model.py` fixed with
  `pytest.approx`, not a blanket ignore. Also moved `Capture` out of
  `src/slidko/capture/__init__.py` into `src/slidko/capture/model.py` (with
  a re-export) to satisfy `RUF067` (`__init__` should only contain
  docstrings/re-exports) — `from slidko.capture import Capture` still works
  everywhere.
- [ ] 9.2 `.venv/bin/python -m pytest` (and `make test`, which uses
  `$(PY) -m pytest`) collect fine — running `python -m pytest` adds the repo
  root to `sys.path`, so `from tests.synth import ...` resolves. But invoking
  the installed `pytest` console-script directly (`.venv/bin/pytest`) does
  NOT add the cwd to `sys.path`, so it still fails collection with
  `ModuleNotFoundError: No module named 'tests'` on
  `tests/decode/test_native_uart.py`, `tests/decode/test_e2e.py`, and
  `tests/decode/test_backend_compatibility.py`. `tests/` has no
  `__init__.py` anywhere, so it is not a real package. Resolve by either
  adding `tests/__init__.py` (confirm no other implicit-namespace-package
  assumption is now stale) or setting `pythonpath = ["."]` under
  `[tool.pytest.ini_options]` in `pyproject.toml` — pick whichever also
  keeps `.venv/bin/mypy`'s `explicit_package_bases`/`mypy_path = "src"`
  setup (`pyproject.toml` `[tool.mypy]`) working, since that was tuned
  against the same `tests/synth` ambiguity. Low priority given `make check`
  already works; fix for consistency/robustness.
- [ ] 9.3 Verify: `.venv/bin/ruff check .` exits 0 (done) and
  `.venv/bin/pytest -q` (the bare console script, not `python -m pytest`)
  collects with zero errors

## 10. Wrap-up

- [x] 10.1 `make check` green
- [x] 10.2 `.venv/bin/python -m pytest -q` reports zero failures across the ENTIRE suite (85 passed) — this is the actual acceptance bar for this change
- [ ] 10.3 Commit naming the task groups (multiple commits are fine, one per group, per the standing overnight-agent discipline)
