# Proposal: bootstrap-python-package

## Why

Slidko has design docs but zero code — nothing can be built, tested, or CI-checked until the Python package skeleton exists. This change is deliberately small: it is the smoke test for the spec-driven agent workflow (OpenSpec change -> agent applies tasks -> pytest/ruff verify) before larger phases are handed off unattended.

Covers docs/TASKS.md item 1 (repo scaffolding). Prerequisite for docs/ROADMAP.md Phase 0.

## What Changes

- Add `pyproject.toml`: Python 3.11+, runtime deps numpy + scipy only, dev deps pytest + ruff. No LLM SDK (deferred to Phase 5 per TASKS.md).
- Add package skeleton `src/slidko/` with subpackages `capture/`, `measure/`, `decode/`, `narrate/`, `diagnose/`, `librarian/`, `corpus/` (empty `__init__.py` each; version string in top-level `__init__.py`).
- Add `tests/` wired for pytest with one trivial import/version test.
- Add ruff lint + format configuration (in `pyproject.toml`).
- Add CI stub (GitHub Actions) that runs ruff + pytest headless.

## Capabilities

### New Capabilities

- `dev-tooling`: installable package skeleton, test runner wiring, lint/format config, headless CI entry point.

### Modified Capabilities

(none — greenfield)

## Impact

- New files only; no existing code affected (there is none).
- Establishes the dependency floor (numpy/scipy) every later phase builds on.
- After this change, `pip install -e .[dev] && pytest && ruff check .` must succeed on a clean checkout with no hardware attached.
