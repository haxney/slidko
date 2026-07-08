# Delta: dev-tooling

## ADDED Requirements

### Requirement: Static type checking
The project SHALL run `mypy` over `src/` and `tests/` with typed function
definitions required in `src/` (relaxed in `tests/`) and missing third-party
stubs ignored only for scipy. Type checking SHALL be part of the standard
verification gate.

#### Scenario: Type check passes on the committed tree
- **WHEN** `mypy` runs from the repo root with the configured settings
- **THEN** it exits 0 with no reported errors on the committed source

#### Scenario: Untyped public function is rejected
- **WHEN** a function without parameter/return annotations is added under `src/slidko/`
- **THEN** `mypy` reports a missing-annotation error and the verification gate fails

### Requirement: Exact tool-version pinning
Every development tool SHALL be pinned to an exact version (`==`) in
`pyproject.toml` — the test runner, linter/formatter, type checker, pre-commit,
and property-testing library — so a fresh install cannot silently introduce a
tool that reformats or newly-flags the existing tree.

#### Scenario: Dev dependencies are exact
- **WHEN** the `[project.optional-dependencies] dev` list is inspected
- **THEN** each entry uses `==` with a concrete version, none use `>=` or an unbounded name

#### Scenario: Ruff version matches between venv and pre-commit
- **WHEN** the ruff version pinned in `pyproject.toml` is compared to the `rev` of the ruff hook in `.pre-commit-config.yaml`
- **THEN** they are the same version

### Requirement: Unified verification entry point
The project SHALL expose a single non-mutating verification command (`make
check`) that runs lint, format-check, type-check, and tests, and CI SHALL invoke
that same command so local, overnight, and CI verification cannot diverge.

#### Scenario: One command runs the full gate
- **WHEN** `make check` runs on a clean checkout after `pip install -e .[dev]`
- **THEN** it runs ruff lint, ruff format-check, mypy, and pytest, and exits 0 only if all pass

#### Scenario: CI calls the canonical command
- **WHEN** the CI workflow is inspected
- **THEN** its verification step invokes `make check` (not an ad-hoc re-listing of the individual tools)

### Requirement: Offline-capable pre-commit gate
The pre-commit configuration SHALL include a type-check hook implemented as a
local hook (invoking the project venv, requiring no network), and all remote
hook `rev`s SHALL be pinned. Pre-commit environments SHALL be installable while
network is available so later network-denied runs succeed.

#### Scenario: Type-check hook needs no download
- **WHEN** `pre-commit run mypy --all-files` is invoked with no network access
- **THEN** the hook runs against the local venv and produces a pass/fail result without attempting a download

#### Scenario: All hooks are version-pinned
- **WHEN** `.pre-commit-config.yaml` is inspected
- **THEN** every remote repo entry has an explicit pinned `rev` (no floating refs)

### Requirement: Firmware C formatting is pinned
The repository SHALL provide a `.clang-format` style file at its root so the
`firmware/` C tree is style-checked from its first commit, preventing the
formatting churn that the Python tree suffered.

#### Scenario: Clang-format config exists and is valid
- **WHEN** `clang-format --dry-run --Werror` runs against a conformant C source file using the repo `.clang-format`
- **THEN** it exits 0, confirming the style file parses and is enforceable
