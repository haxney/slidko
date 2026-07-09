# Delta: dev-tooling

## ADDED Requirements

### Requirement: Installable package skeleton
The project SHALL provide an installable Python package `slidko` (Python >= 3.11) using the src layout, with subpackages `capture`, `measure`, `decode`, `narrate`, `diagnose`, `librarian`, and `corpus`, and a `slidko.__version__` string. Runtime dependencies SHALL be limited to numpy and scipy; no LLM SDK may be added before Phase 5.

#### Scenario: Editable install on a clean checkout
- **WHEN** `pip install -e .[dev]` runs on a clean checkout with Python 3.11+
- **THEN** the install succeeds and `python -c "import slidko; print(slidko.__version__)"` prints a version string

#### Scenario: All subpackages importable
- **WHEN** each of `slidko.capture`, `slidko.measure`, `slidko.decode`, `slidko.narrate`, `slidko.diagnose`, `slidko.librarian`, `slidko.corpus` is imported
- **THEN** every import succeeds without side effects or hardware access

### Requirement: Test runner wiring
The project SHALL run its test suite with `pytest` discovered from `tests/`, requiring no hardware and no network.

#### Scenario: Pytest passes on the skeleton
- **WHEN** `pytest` runs after an editable install
- **THEN** at least one test (import/version check) runs and the suite exits 0

### Requirement: Lint and format configuration
The project SHALL configure ruff (lint + format) in `pyproject.toml` so that `ruff check .` and `ruff format --check .` pass on the committed tree.

#### Scenario: Clean lint on committed tree
- **WHEN** `ruff check .` and `ruff format --check .` run at the repo root
- **THEN** both exit 0

### Requirement: Headless CI entry point
The project SHALL provide a CI workflow that installs the package and runs ruff and pytest headless on push, with no hardware-dependent steps.

#### Scenario: CI steps mirror local verification
- **WHEN** the CI workflow file is inspected
- **THEN** it contains install, `ruff check`, and `pytest` steps and references no capture hardware or devices
