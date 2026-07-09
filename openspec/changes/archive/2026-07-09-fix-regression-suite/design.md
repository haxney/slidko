# Design: fix-regression-suite

## Context

Every finding below was diagnosed directly against the failing test's actual
traceback and the real implementation on disk (not guessed). Task groups in
tasks.md reference these findings by ID so the fix is mechanical, not
another round of diagnosis.

## House-style decisions (apply consistently, not per-symptom)

### Decision 1: canonical event/finding schemas, no local mini-schemas

`slidko.decode.events.DecodedEvent` (kind, start_sample, end_sample, data,
channel) and `slidko.measure.smoke.SmokeFinding` (check, channel,
start_sample, end_sample, severity, summary, escalation, evidence) are THE
schemas. Any module consuming decoded events or smoke findings imports these
directly — it does not define its own `DecodedEvent`/`SmokeFinding` dataclass
with different fields. `narrate/coincidence.py` and
`narrate/transaction_summary.py` currently violate this (local classes with
`.address`, `.is_nak`, `.sample` fields that don't exist on the real
schemas). Fix: import the real classes; adjust field access:
- `event.address` → `event.data["address"]` (present on `i2c.address` events)
- `event.kind == "i2c.nak"` stays as-is (kind IS the NAK marker; there is no
  separate `is_nak` field)
- `event.sample` → `event.start_sample`
- `finding.sample` → `finding.start_sample` (SmokeFinding has
  `start_sample`/`end_sample`, not `sample`)

Add a guard test (task 1.4) asserting these modules import the real classes
by identity (`from slidko.decode.events import DecodedEvent as
CanonicalEvent; assert coincidence.DecodedEvent is CanonicalEvent`), so this
cannot silently re-diverge.

### Decision 2: dict-level pre-validation for "canned output" scenarios

Both `Instruction` and `Sidecar` are strict dataclasses (every field
required at construction). Several spec scenarios describe validating "a
canned LLM output missing field X" or "a sidecar dict lacking
receiver_verdict" — inputs that are raw dict/JSON, not already-valid
instances. As currently implemented, missing a required field either raises
an uncontrolled `TypeError` (Instruction, if you try `Instruction(**d)`) or a
raw `KeyError` deep inside `from_json` (Sidecar) — neither is the
"field-level error" / "error naming the missing field" the specs ask for.

**House answer:** make the specific fields the scenarios test as missing
`Optional[...] = None` at the dataclass level (mirroring the pattern
`corpus/sidecar.py` already uses correctly for `sweep_cell`/`referee`), and
do the "is it actually present and non-None" check in a separate
`validate()` function that returns a list of human-readable error strings
naming the field. This means:
- `Sidecar.receiver_verdict: ReceiverVerdict | None = None`; `from_json`
  builds it if present, else leaves `None`; `Sidecar.validate()` (already
  exists as a staticmethod per the earlier session's partial work) checks
  `if sidecar.receiver_verdict is None: errors.append("receiver_verdict is
  required")`.
- `Instruction.expected_outcome_per_hypothesis: dict[str, str] | None =
  None`; `validate_instruction()` checks
  `if not instruction.expected_outcome_per_hypothesis: errors.append(...)`
  in addition to its existing rules. The test that currently does
  `Instruction(**canned_output)` under `pytest.raises(TypeError)` (a
  documented stand-in for the missing pre-validation step, added in the
  `lint:` commit that unblocked this branch) gets replaced with a real
  `validate_instruction(Instruction(**canned_output_with_default), retrieval)`
  call asserting the field-level error appears.

Do not generalize further than these two fields right now — only the fields
actual spec scenarios exercise as "missing."

## Per-failure diagnosis

### F1 — `tests/corpus/test_sidecar.py::test_sidecar_round_trip`

`Sidecar.from_json` does:
```python
fault_injected_data = data.get("fault_injected", {})
if "class" in fault_injected_data:
    fault_injected_data["class_"] = fault_injected_data.pop("class")
```
`fault_injected_data` is a reference to `data["fault_injected"]`, not a copy.
`.pop("class")` mutates the caller's dict in place. The test passes the
module-level `CORPUS_EXAMPLE` fixture directly to `from_json`, which
silently deletes `CORPUS_EXAMPLE["fault_injected"]["class"]` as a side
effect; the test's later comparison against `CORPUS_EXAMPLE["fault_injected"]["class"]`
then hits `KeyError` on the RIGHT-hand side.

**Fix:** `fault_injected_data = dict(data.get("fault_injected", {}))` (copy
before mutating). Apply the same copy-before-pop discipline anywhere else in
`from_json` that pops from an input sub-dict.

### F2 — `tests/corpus/test_sidecar.py::test_missing_receiver_verdict_validation`

`from_json` does `ReceiverVerdict(**data["receiver_verdict"])` unconditionally
— a bare `KeyError` when the key is absent, not a validation error. Apply
House Decision 2: make `receiver_verdict` Optional, build it only if present,
and have `validate()` report the missing field.

### F3 — `tests/decode/test_sigrok_backend.py` (all 5 tests) and `tests/decode/test_e2e.py` (i2c, spi; re-check uart)

Every one of these wraps its real assertions in
`with pytest.raises(NotImplementedError):`. This was appropriate scaffolding
before `SigrokBackend` existed; it was never removed. Under the hood,
`_decode_uart`/`_decode_i2c`/`_decode_spi` in `src/slidko/decode/sigrok_backend.py`
are STILL literally:
```python
raise NotImplementedError("Sigrok UART decoder not implemented yet")
```
(same for I2C/SPI), and `_parse_uart_output`/`_parse_i2c_output` are the same
kind of stub — despite `phase-2-decode-backend/tasks.md` task 4.3 reading
`[x]`. This is not a subtle bug: the implementation was never finished, and
the checkbox was marked done anyway. Fix for real, using the format already
confirmed in `phase-2-decode-backend/design.md` (verified locally against
sigrok-cli 0.7.2 / libsigrokdecode 0.5.3 — do not reinvent):

- UART parse target: lines like `4368-6036 uart-1: 41` (samplenum range,
  decoder tag, hex byte) → `DecodedEvent(kind="uart.byte", start_sample=4368,
  end_sample=6036, data={"value": 0x41, "ascii": "A"}, channel=None)`.
- I²C parse target: `780-3300 i2c-1: Address write: 68` → `i2c.address`
  event with `data={"address": 0x68, "rw": "write"}`; `3660-4020 i2c-1: ACK`
  → `i2c.ack`; `4020-6900 i2c-1: Data write: AA` → `i2c.data` with
  `data={"value": 0xAA}`; also handle `Start`/`Stop`/`NACK`/`Address read`.
- The two failing stdout-parsing tests currently feed FICTIONAL mock data
  (`"0.012345 0x41"`, `"0.001234 START"`) that sigrok-cli never actually
  produces. Replace this mock data with the real confirmed lines above.

### F4 — `tests/decode/test_e2e.py::test_e2e_i2c_decode` / `test_e2e_spi_decode`

Once F3's wrapper is removed, this surfaces:
```
AttributeError: 'Capture' object has no attribute 'filename'
```
`_build_i2c_args`/`_build_spi_args` do `capture.filename` — the real
`Capture` dataclass (`src/slidko/capture/__init__.py`) only has `channels`,
`samplerate_hz`, `provenance`. sigrok-cli needs an actual `.sr` file path on
disk (`-i <path>`); an in-memory `Capture` has none. **Fix:** give
`SigrokBackend.decode()` (or the private `_build_*_args` helpers) an explicit
way to get a file path — write the `Capture` to a temp `.sr` internally via
`capture/srfile.write_sr` (cleanup with a context manager / `tempfile`), and
use that path for `-i`. Do not add a `filename` field to `Capture` itself —
captures are in-memory evidence objects (Phase 0 design); the file is a
sigrok-backend-specific implementation detail.

### F5 — `tests/decode/test_sigrok_backend.py::test_sigrok_uart_args_building`

Distinct from F3/F4: even once implemented, `stop_bits` renders as `"1.0"`
(Python `str(1.0)`) but the confirmed sigrok option value is `"1"`. Format
`stop_bits` without a trailing `.0` when it's a whole number, e.g.
`f"{stop_bits:g}"` or `str(int(stop_bits)) if stop_bits == int(stop_bits)
else str(stop_bits)`.

### F6 — `tests/decode/test_native_uart.py::test_native_uart_decode_sbus`

Not an implementation bug. `native_uart.py` correctly raises `ValueError`
for any non-8N1 configuration (SBUS is 8E2 — even parity, 2 stop bits) per
`phase-2-decode-backend/tasks.md` task 3.1's own scope note ("native handles
8N1 standard bauds ... SBUS is handled by the sigrok path"). The TEST asks
the wrong backend to decode SBUS. **Fix the test, not the implementation:**
either delete this test (SBUS-via-sigrok coverage belongs in, and may
already exist in, the sigrok backend's test suite — verify before deleting)
or rewrite it to assert the `ValueError` is raised (documenting the
by-design refusal) instead of asserting successful SBUS decode.

### F7 — `tests/measure/test_ws2812_timing.py::test_ws2812_timing_clean`

Not an implementation bug. At 24 MS/s (1 sample = 41.667 ns), the WS2812
windows from `phase-3-smoke-detector/design.md` are:
- T0H: nominal 400 ns ± 150 ns → [250, 550] ns → **[6.0, 13.2] samples**
- T1H: nominal 800 ns ± 150 ns → [650, 950] ns → **[15.6, 22.8] samples**

The test's fixture (`edges = [0, 10, 20, 25, 40, 45]`, high-times 10, 5, 5
samples) has two high-times of 5 samples — below the T0H lower bound of 6.0,
so they are genuinely NOT within either window. The smoke detector correctly
flags them; the test's docstring claim "(10, 5, 5) ... within window" is
wrong. **Fix the test fixture**, not the implementation: pick high-times
that actually land inside a window, e.g. 10 samples (→ T0H, "0" bit) and 18
samples (→ T1H, "1" bit) for a genuinely clean 2-3 bit train, and recompute
the `edges` array and low-time gaps to match (low time = bit period (~30
samples) minus high time, per the WS2812 encoding).

### F8 — `tests/narrate/test_coincidence.py::test_non_coincident_events_do_not_coincide`

`COINCIDENCE_WINDOW_SAMPLES = 5000  # 5ms at 1MHz sample rate (arbitrary for
demo)` in `narrate/coincidence.py` is a flat constant, not derived from
samplerate as `phase-4-narrate/design.md` specifies
(`COINCIDENCE_WINDOW_SAMPLES` should derive from a named TIME window, e.g.
100 microseconds, at the capture's actual samplerate). At 1 MHz, a flat 5000
samples = 5 ms — so two events 900 microseconds apart (test: sample 100 vs
sample 1000, `samplerate_hz=1_000_000`) both fall inside it, wrongly
flagging as coincident. **Fix:** replace the flat constant with
`COINCIDENCE_WINDOW_US = 100` (or similar) and compute
`window_samples = COINCIDENCE_WINDOW_US * samplerate_hz / 1_000_000` inside
`detect_coincidences`, so the window is a real, samplerate-independent time
duration. Verify against BOTH existing coincidence tests (the "within
window" positive case uses a 5-sample delta at 1 MHz = 5 microseconds, well
inside 100 microseconds; the "outside window" case uses 900 microseconds,
outside it).

### F9 — `narrate/transaction_summary.py` hardcoded to address 0x68

`summarize_transactions` filters `e.kind == "i2c.start" and e.address ==
0x68` — hardcoded, despite the docstring reading "For each address, count
number of transactions and NAKs." No currently-failing test catches this
(the 0x76 test only asserts the function returns `[]`, which happens to be
literally true for the wrong reason), but it directly contradicts the spec
requirement (phase-4-narrate `specs/narration/spec.md`: "Narrate SHALL
convert decoded events ... quantitative"). **Fix:** group `i2c.start` events
by `event.data["address"]` (after Decision 1's schema fix — recall real
events carry `address` inside `data`, not as a top-level attribute) and emit
one `transaction.summary` assertion per address that has traffic, matching
NAKs per-address the same way. Update `test_transaction_summary_different_address`
to assert a real summary is produced for 0x76 instead of asserting `[]`.

## Risks / Trade-offs

- [Rewiring coincidence.py/transaction_summary.py to canonical schemas
  touches working code] → both modules currently only pass tests because the
  tests use the SAME local wrong schema; there is no currently-correct
  behavior being protected. Low risk.
- [House Decision 2's Optional-field pattern could mask genuinely missing
  data elsewhere] → scoped narrowly to the two fields actual scenarios test;
  do not make every field Optional.
- [F6/F7 fixes are test-only] → double-check by re-reading the relevant
  implementation once more before touching only the test — if either turns
  out to have a real bug after all, fix the implementation instead and note
  the correction in the task's commit.
