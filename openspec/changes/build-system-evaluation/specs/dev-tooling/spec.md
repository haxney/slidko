# Delta: dev-tooling

## MODIFIED Requirements

### Requirement: Unified verification entry point
The project SHALL expose a single non-mutating verification command — the
canonical task `mise run check` — that runs lint, format-check, type-check, and
tests, and CI SHALL invoke that same task so local, overnight, and CI
verification cannot diverge. The task MAY fan out to the native per-language
tools (ruff, mypy, pytest, and any firmware checks), but there SHALL remain
exactly one canonical command that callers invoke.

#### Scenario: One command runs the full gate
- **WHEN** `mise run check` runs on a clean checkout after `mise install`
- **THEN** it runs ruff lint, ruff format-check, mypy, and pytest, and exits 0 only if all pass

#### Scenario: CI calls the canonical command
- **WHEN** the CI workflow is inspected
- **THEN** its verification step invokes the canonical mise task (not an ad-hoc re-listing of the individual tools)

#### Scenario: A thin Makefile alias, if kept, delegates
- **WHEN** a root `Makefile` is retained for muscle memory
- **THEN** its `check` target delegates to the mise task rather than re-listing the tools, so the two cannot drift

### Requirement: Exact tool-version pinning
Every development tool SHALL be pinned to an exact version — the Python dev
tools (test runner, linter/formatter, type checker, pre-commit, property-testing
library) via `==` in `pyproject.toml`, and the polyglot toolchain (the Python
interpreter, the Rust toolchain and its cross-compile target, the proto codec
generator, and `picotool`) via exact versions in `mise.toml` — so a fresh
install cannot silently introduce a tool that reformats, newly-flags, or changes
the codegen output of the existing tree.

#### Scenario: Python dev dependencies are exact
- **WHEN** the `[project.optional-dependencies] dev` list is inspected
- **THEN** each entry uses `==` with a concrete version, none use `>=` or an unbounded name

#### Scenario: Polyglot toolchain is pinned in mise
- **WHEN** the `[tools]` table in `mise.toml` is inspected
- **THEN** each declared tool (Python, Rust, the cross-compile target, the proto codec generator, picotool) carries an exact version, none floating

#### Scenario: Ruff version matches between venv and pre-commit
- **WHEN** the ruff version pinned in `pyproject.toml` is compared to the `rev` of the ruff hook in `.pre-commit-config.yaml`
- **THEN** they are the same version

### Requirement: Headless CI entry point
The project SHALL provide a CI workflow that runs the full verification gate
headless on push by invoking the canonical `mise run ci` task — which provisions
the pinned toolchain (via the mise action) and runs ruff, mypy, and pytest — with
no hardware-dependent steps and no per-tool re-listing that could drift from
local verification.

#### Scenario: CI steps mirror local verification
- **WHEN** the CI workflow file is inspected
- **THEN** its verification step invokes `mise run ci` (the same canonical task a developer runs locally, not an ad-hoc re-listing of ruff/mypy/pytest) and references no capture hardware or devices
