# regression-fixes

## Purpose

Cross-cutting correctness rules that keep the pipeline's data model
coherent as modules multiply: a single canonical schema per shared
concept (events, findings), validation errors that are named and
catchable rather than uncontrolled exceptions, and a full-suite green
gate that isn't satisfied by per-module passing tests alone.

## Requirements

### Requirement: Canonical event and finding schemas are the only schemas
Any module that consumes decoded events or smoke findings SHALL import
`slidko.decode.events.DecodedEvent` and `slidko.measure.smoke.SmokeFinding`
directly rather than defining a local, divergent dataclass with the same
purpose.

#### Scenario: No local re-definitions in narrate modules
- **WHEN** `slidko.narrate.coincidence` and `slidko.narrate.transaction_summary` are inspected
- **THEN** their `DecodedEvent` name (if referenced at all) resolves by identity to `slidko.decode.events.DecodedEvent`, and similarly for `SmokeFinding` against `slidko.measure.smoke.SmokeFinding`

### Requirement: Validation of raw/canned output is representable
Fields that a spec scenario validates as "missing" from canned/raw output SHALL be representable as absent (an `Optional` dataclass field defaulting to `None`) so a dedicated `validate()`-style function can report a named, field-level error, rather than construction itself raising an uncontrolled `TypeError` or `KeyError`.

#### Scenario: Missing receiver_verdict is a named validation error
- **WHEN** a sidecar dict lacking `receiver_verdict` is passed through `Sidecar.from_json` and then `Sidecar.validate`
- **THEN** construction succeeds with `receiver_verdict = None`, and `validate` returns an error naming `receiver_verdict` — no uncaught exception

#### Scenario: Missing expected_outcome_per_hypothesis is a named validation error
- **WHEN** a canned instruction dict lacking `expected_outcome_per_hypothesis` is constructed and passed to `validate_instruction`
- **THEN** construction succeeds with the field `None`, and validation returns a field-level error naming `expected_outcome_per_hypothesis` — no uncaught exception

### Requirement: Full-suite regression gate
After this change, the complete test suite SHALL pass with zero failures,
not merely the tests belonging to the modules this change touches.

#### Scenario: Whole-suite green
- **WHEN** `.venv/bin/python -m pytest -q` runs at the repo root after this change is applied
- **THEN** it reports zero failures
