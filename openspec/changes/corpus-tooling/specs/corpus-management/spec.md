# Delta: corpus-management

## ADDED Requirements

### Requirement: Schema-validated sidecars
Corpus entries SHALL pair a raw .sr capture with a JSON sidecar validated against the docs/CORPUS.md schema (instrument, driver, transport, receiver, protocol, fault_injected, receiver_verdict, sweep_cell, referee). Invalid or missing sidecars fail validation loudly.

#### Scenario: Missing receiver verdict rejected
- **WHEN** a sidecar lacking `receiver_verdict` is validated
- **THEN** validation fails naming the missing field

#### Scenario: Referee field accepted from day one
- **WHEN** a sidecar includes a populated `referee` block (dual-instrument cell)
- **THEN** it validates — the schema supports the analog-hardening era now

### Requirement: One-motion labeled capture
The capture CLI SHALL execute capture, prompt for the contemporaneous receiver verdict, and write `entry-*.sr` + `entry-*.json` into the correct cell directory in a single invocation.

#### Scenario: Single command yields a complete entry
- **WHEN** the CLI runs against a (mocked) instrument and the operator supplies a verdict
- **THEN** both files exist, cross-reference by id, and the sidecar validates

### Requirement: Sweep cells produce curves
The sweep-cell runner SHALL sequence entries along a declared axis (`cell.json`: axis, fixture, fix arms), so downstream evals can extract degradation curves rather than anecdotes.

#### Scenario: Axis recorded per entry
- **WHEN** a sweep runs at lengths 1/5/10 m
- **THEN** each entry's sidecar carries `sweep_cell.axis = "length_m"` and its value

### Requirement: Field gold is held out
`corpus/field-gold/` SHALL be excluded from all threshold tuning and eval-fitting paths, enforced by an automated check (raw samples only; never tuned against — the exam, not the homework).

#### Scenario: Tuning against field gold fails CI
- **WHEN** a test or tuning fixture references files under `field-gold/`
- **THEN** the holdout check fails the build
