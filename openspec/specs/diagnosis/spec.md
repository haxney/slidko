# diagnosis

## Purpose

Closes the diagnostic loop by emitting structured, schema-validated probe
instructions ("probe here next"). Citation enforcement and the accessibility
filter are architectural — enforced in the validator, not by prompt text —
and config-pull results are always checked before a physical probe is
suggested.

## Requirements

### Requirement: Structured instruction schema
Diagnose SHALL emit instructions only in the structured schema: `action`, `target`, `parameters`, `expected_outcome_per_hypothesis` (one entry per live hypothesis), `hazard_notes`, `executor` ("human" | "exerciser"), `citations`. Free-text instructions are invalid.

#### Scenario: Schema-invalid output rejected
- **WHEN** a canned LLM output missing `expected_outcome_per_hypothesis` is validated
- **THEN** validation fails with a field-level error; the instruction is not surfaced

### Requirement: Citation enforcement is architectural
Any pad-level placement claim SHALL carry a citation to a librarian-retrieved document (doc-id#anchor) or an explicit `"unknown": true` flag; validation SHALL reject uncited pad claims. This is enforced in the validator, not by prompt text.

#### Scenario: Uncited pad claim rejected without an LLM
- **WHEN** a canned output claims "clip TP7" with no citation and no unknown flag
- **THEN** schema validation rejects it (test runs offline, no LLM call)

### Requirement: Hazard notes and the accessibility filter
Every exercise instruction SHALL carry hazard notes, and instruction generation SHALL prefer connectors, test points, and passive bodies over IC pins; instructions to needle-probe fine-pitch (≤ 0.5 mm) IC pads on a live board are invalid.

#### Scenario: Fine-pitch probe instruction blocked
- **WHEN** a canned output instructs probing a 0.4 mm-pitch IC pad on a powered board
- **THEN** validation rejects it with an accessibility-filter error

### Requirement: Fault-tree ordering respects config-first
For symptoms with known configuration causes, config-pull suggestions SHALL precede probe instructions.

#### Scenario: Config cause checked before soldering
- **WHEN** a scripted scenario's symptom has a known config cause and a config-pull path exists
- **THEN** the first emitted instruction is a config pull, not a probe placement
