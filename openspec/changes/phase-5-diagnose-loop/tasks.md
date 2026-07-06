# Tasks: phase-5-diagnose-loop

> Prerequisite: `dev-tooling-gate` applied; Phase 4 Narrate available. This is
> the FIRST change permitted to add an LLM SDK dependency. The LLM is mocked in
> every test — the whole safety envelope (schema, citations, accessibility,
> config-pull read-only) is deterministic and LLM-free. TDD from the spec
> scenario. End every group with `make check`.

## 1. Instruction schema

- [ ] 1.1 Write failing tests in `tests/diagnose/test_instruction.py`: `Instruction` frozen dataclass with all fields in design.md; `Instruction`↔JSON round-trips; `expected_outcome_per_hypothesis` is a dict
- [ ] 1.2 Implement `src/slidko/diagnose/instruction.py`; tests green

## 2. Schema + citation validator (LLM-free)

- [ ] 2.1 Write failing tests in `tests/diagnose/test_validate.py` using CANNED instruction dicts (no LLM): (a) missing `expected_outcome_per_hypothesis` → field-level error; (b) pad-level claim ("clip TP7") with no citation and no unknown flag → rejected; (c) dangling citation (`doc-id#anchor` not in retrieval set) → rejected; (d) empty `hazard_notes` on a placement instruction → rejected; (e) valid instruction → accepted
- [ ] 2.2 Implement `is_pad_level_claim(instruction) -> bool` per design.md predicate; unit-test it against canned placement vs twiddle instructions
- [ ] 2.3 Implement `validate_instruction(instruction, retrieval) -> list[ValidationError]` covering rules 1–6 in design.md; tests green (all run offline)

## 3. Accessibility filter

- [ ] 3.1 Write failing test: a canned instruction to needle-probe a 0.4 mm-pitch IC pad on a powered board (`power_state="on"`) → rejected with an accessibility-filter error; the same probe on an unpowered board or on a connector/test-point → accepted
- [ ] 3.2 Implement the IC-pin classifier + `MIN_PROBE_PITCH_MM = 0.5` named constant and wire it into the validator; tests green

## 4. Librarian retrieval (fixture-backed, offline)

- [ ] 4.1 Write failing tests in `tests/librarian/test_retrieve.py`: retrieving a known board id (fixture) returns a `Retrieval` with tier and `fragments` mapping stable `doc-id#anchor` keys to content; a citation present in `fragments` resolves; an absent one does not
- [ ] 4.2 Implement `src/slidko/librarian/__init__.py` (or `retrieve.py`): `Librarian` Protocol + a fixture backend reading doc fragments from a fixtures dir keyed by board id; tests green
- [ ] 4.3 Write failing test for tier awareness: a `dark`-tier board makes any pad-level placement claim without `unknown=True` fail validation (wire tier into the validator via the retrieval)
- [ ] 4.4 Implement dark-board enforcement; tests green

## 5. Config pull — READ-ONLY by construction

- [ ] 5.1 Write failing tests in `tests/diagnose/test_config_pull.py`: (a) building an allowlisted read (e.g. MSP_STATUS id 101) produces the correct MSP v1 `$M<` frame with size 0 and correct XOR checksum; (b) requesting ANY command outside the read allowlist (e.g. MSP_SET_PID 202) raises `ProductBoundaryError`; (c) the public API exposes no write/flash/set function (inspect the module's callables)
- [ ] 5.2 Implement `src/slidko/diagnose/config_pull.py`: a read-only command allowlist enum (the 15 IDs in design.md), an MSP v1 request-frame builder (`$` `M` `<` size cmd payload xor-checksum), and `ProductBoundaryError`. No serial I/O — frame construction only. Tests green
- [ ] 5.3 Add a test asserting the allowlist contains exactly the design.md read IDs and none from the MSP_SET_* range

## 6. LLM boundary (mocked)

- [ ] 6.1 Add the `anthropic` SDK to `pyproject.toml` (pinned, per dev-tooling-gate); reinstall the venv; `make check` still green
- [ ] 6.2 Write failing tests in `tests/diagnose/test_llm.py` with a FAKE client implementing the `propose_instruction` Protocol returning canned dicts; assert Diagnose consumes them and never calls a real network client in tests
- [ ] 6.3 Implement `src/slidko/diagnose/llm.py`: narrow Protocol + a real Anthropic-backed impl using the latest Claude model id (per the project's model guidance — do NOT hardcode a deprecated id); a fake impl for tests; tests green

## 7. Fault-tree ordering (config-first) + the loop

- [ ] 7.1 Write failing test: a scripted scenario whose symptom has a known config cause AND a config-pull path emits a config-pull instruction FIRST (before any probe placement), using the fake LLM
- [ ] 7.2 Write failing test: a symptom fully explained by a retrieved config value (e.g. a disabled UART port) short-circuits — diagnosis cites the config evidence, emits a config-fix suggestion, and issues NO probe instruction
- [ ] 7.3 Implement the symptom→fault-tree map (config branches sort before probe branches) and the loop orchestrator `diagnose(assertions, librarian, llm, board_id) -> Instruction`; tests green
- [ ] 7.4 Write an end-to-end scripted scenario test (seeded symptom + synthetic corpus capture → plausible next-poke instruction) evaluated against a RUBRIC (structural checks: valid schema, grounded citation or unknown flag, hazard notes present), not an exact string match

## 8. Wrap-up

- [ ] 8.1 `make check` green; confirm the ENTIRE suite passes with NO network and NO real LLM (all LLM tests use the fake) — the safety envelope is fully offline-testable
- [ ] 8.2 Commit naming the task groups
