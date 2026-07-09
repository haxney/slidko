# Proposal: fix-regression-suite

## Why

The overnight chain that implemented `phase-2-decode-backend`, `phase-3-smoke-detector`,
`phase-4-narrate`, `phase-5-diagnose-loop`, and `corpus-tooling` left the suite
red — 12 failing tests — while its own task checkboxes read as complete or
near-complete (`phase-2-decode-backend` 21/24, `corpus-tooling` 13/15). This
directly violates the standing rule "never proceed past a red suite — fix it
or stop" (`.opencode/agents/overnight.md`).

Investigation (done directly, not delegated — see design.md for exact
diagnoses per failure) found three distinct classes of problem, not one:

1. **Leftover TDD scaffolding never cleaned up.** Several test functions in
   `tests/decode/test_sigrok_backend.py` and `tests/decode/test_e2e.py` wrap
   their real assertions in `with pytest.raises(NotImplementedError):` — a
   red-test placeholder from before the implementation existed. Once the
   implementation landed, the wrapper was never removed, so a genuinely wrong
   assertion inside the block raises a *different* exception than expected,
   which `pytest.raises` re-raises rather than swallows — masking exactly how
   broken the code under test is.
2. **Real implementation bugs**, some only visible once (1) is fixed:
   `Sidecar.from_json` mutates its input dict via `.pop()` on a live
   reference (an aliasing bug that corrupted the shared test fixture);
   `Sidecar.from_json` raises a raw `KeyError` instead of a graceful,
   named-field validation error when `receiver_verdict` is absent;
   `SigrokBackend._build_i2c_args`/`_build_spi_args` reference
   `capture.filename`, which does not exist on the real `Capture` dataclass;
   `_build_uart_args` renders `stop_bits` as `"1.0"` instead of `"1"`;
   `_decode_uart`/`_decode_i2c`/`_decode_spi` and the two output parsers are
   still `raise NotImplementedError(...)` stubs despite their task
   checkboxes reading `[x]`; `narrate/coincidence.py`'s
   `COINCIDENCE_WINDOW_SAMPLES` is a flat hardcoded `5000`, not derived from
   a real time window, so it flags events 900 microseconds apart as
   coincident; `narrate/transaction_summary.py` hardcodes address `0x68`
   instead of generalizing per-address as its own docstring promises.
3. **Wrong test fixtures, correct implementation.** `test_ws2812_timing_clean`
   asserts on hand-picked edge intervals that do not actually fall inside
   either the T0H or T1H spec window at 24 MS/s (verified by direct
   computation) — the smoke detector is correctly flagging them, the test
   data is wrong. `test_native_uart_decode_sbus` asks the *native* (8N1-only)
   backend to decode SBUS (8E2), which the implementation correctly refuses
   by design (SBUS routes through the sigrok backend) — this test is
   checking the wrong backend, not a wrong implementation.

Two more classes of drift surfaced later, while applying `dev-tooling-gate`
(see that change's session notes): once its mypy config was made to pass
tree-wide, `ruff check .` turned up ~80 pre-existing findings in `src/` and
`tests/` (long lines, unused variables, naming, ambiguous unicode, and 9
`pytest.raises`-with-multiple-statements findings that overlap with problem
class 1 above), and `pytest -q` fails at collection (`ModuleNotFoundError: No
module named 'tests'`) importing `tests/synth.py` from three `tests/decode/`
files, because `tests/` has no `__init__.py` and is not on `sys.path` as a
package under pytest's default import mode. Both are added to this change's
task list (group 9) rather than a new change, since this change already owns
the "red suite" / downstream-drift cleanup.

There is also a recurring architecture gap worth fixing once, in the design,
rather than patching per-symptom: `narrate/coincidence.py` and
`narrate/transaction_summary.py` each define their **own local, incompatible
`DecodedEvent`/`SmokeFinding` mini-schema** instead of importing the
canonical `slidko.decode.events.DecodedEvent` / `slidko.measure.smoke.SmokeFinding`
that `phase-2-decode-backend` and `phase-3-smoke-detector` already ship. And
both `Instruction` (`diagnose/instruction.py`) and `Sidecar`
(`corpus/sidecar.py`) are strict all-fields-required dataclasses being asked
to validate "canned/raw JSON output that might be missing a field" — a
scenario that is structurally unreachable when construction itself demands
every field. Both gaps get a single house-style fix applied consistently.

## What Changes

- Rewire `narrate/coincidence.py` and `narrate/transaction_summary.py` to
  consume the canonical `slidko.decode.events.DecodedEvent` and
  `slidko.measure.smoke.SmokeFinding` schemas instead of local mini-schemas.
- Fix `COINCIDENCE_WINDOW_SAMPLES` to derive from a real, named time window.
- Generalize `summarize_transactions` to any I²C address, not just `0x68`.
- Add a dict-level pre-validation step ahead of `Instruction` and `Sidecar`
  construction (or make the relevant fields `Optional` with `None` defaults
  plus a `validate()` pass) so "canned output missing a required field" is a
  representable, testable scenario instead of an unconditional `TypeError`/
  `KeyError` at construction time.
- Fix the `Sidecar.from_json` input-mutation bug (copy before `.pop()`).
- Finish the actual `SigrokBackend` implementation: real subprocess
  invocation + real output parsers per the exact confirmed sigrok-cli format
  already documented in `phase-2-decode-backend/design.md`; fix the
  `capture.filename` gap (accept an explicit `.sr` path, or write one
  internally via `capture/srfile.write_sr`); fix `stop_bits` formatting.
- Remove the leftover `pytest.raises(NotImplementedError)` scaffolding from
  `tests/decode/test_sigrok_backend.py` and `tests/decode/test_e2e.py`, and
  replace the tests' fictional mock stdout data with the real confirmed
  sigrok-cli output lines.
- Correct `test_ws2812_timing_clean`'s fixture to genuinely-clean edge data
  and either fix or retarget `test_native_uart_decode_sbus`.
- Reconcile every touched change's `tasks.md` checkboxes with what is
  actually implemented and passing (several currently read `[x]` for stub
  code) so future runs don't skip work that was never really done.
- Clean up the ~80 `ruff check` findings in `src/`/`tests/` and fix the
  `tests`-package import gap so `pytest -q` collects without error.

## Capabilities

### New Capabilities

- `regression-fixes`: two new house-style standing rules this change
  establishes (canonical event/finding schema reuse; representable
  dict-level validation for canned/raw output) plus the full-suite-green
  regression gate.

### Modified Capabilities

(none beyond the above — this change otherwise fixes conformance to
existing `protocol-decode`, `smoke-detector`, `narration`,
`corpus-management`, and `diagnosis` requirements; it does not change their
requirements)

## Impact

- Touches `src/slidko/{decode,narrate,corpus,diagnose}/` implementation
  files and their test files; no new modules.
- No spec deltas needed — the acceptance criteria this change targets are
  the ones already written in `phase-2-decode-backend`, `phase-3-smoke-detector`,
  `phase-4-narrate`, `phase-5-diagnose-loop`, and `corpus-tooling`'s existing
  `specs/`. This change makes the implementation actually satisfy them.
