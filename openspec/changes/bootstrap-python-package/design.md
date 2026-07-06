# Design: bootstrap-python-package

## Context

Greenfield repo; docs are canonical (see CLAUDE.md). Language and layout are already ruled: Python 3.11+, src layout under `src/slidko/`, numpy/scipy only. This design records only the scaffolding choices those rulings leave open.

## Goals / Non-Goals

**Goals:**
- Smallest tree where install, import, pytest, ruff, and CI all pass headless.
- Serve as the agent-workflow smoke test: every task verifiable by a single command.

**Non-Goals:**
- Any capture/measure logic (Phase 0+). Any dependency beyond numpy/scipy/pytest/ruff. Packaging for distribution (no PyPI publishing config).

## Decisions

- **Build backend: hatchling.** Modern, zero-config for src layout, no setup.py. Alternative (setuptools) rejected as needless legacy surface for a new package.
- **Single `pyproject.toml`** carries project metadata, ruff config, and pytest config — no `setup.cfg`, no `.ruff.toml`, no `pytest.ini`. One file to read.
- **Dev deps as `[project.optional-dependencies] dev`** (`pip install -e .[dev]`) rather than requirements.txt — keeps the dependency floor declared in one place.
- **CI: GitHub Actions, single job** (install -> ruff -> pytest) on ubuntu-latest, Python 3.11. Matrix builds deferred until there is code worth matrixing.
- **Version: static string in `src/slidko/__init__.py`**, single source of truth; dynamic versioning is not warranted yet.

## Risks / Trade-offs

- [Ruff version drift changes lint verdicts] → pin a minimum ruff version in dev deps; CI uses the same pin as local.
- [Empty subpackages invite import-time cruft later] → spec requires imports be side-effect free; enforced by the import test.
