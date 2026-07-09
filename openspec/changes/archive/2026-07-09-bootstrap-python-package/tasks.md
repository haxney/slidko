# Tasks: bootstrap-python-package

## 1. Environment and package skeleton

- [x] 1.1 Create an isolated venv at `.venv`: `python -m venv .venv`. NOTE: `source .venv/bin/activate` does NOT persist across separate tool/command invocations — invoke every tool by explicit path (`.venv/bin/pip`, `.venv/bin/python`, `.venv/bin/ruff`), never bare `pip`/`pytest`/`ruff` (a stray user-level binary can shadow the venv).
- [x] 1.2 Create `pyproject.toml` (hatchling backend; project `slidko`, `requires-python >= 3.11`; deps numpy, scipy; `[project.optional-dependencies] dev = pytest, ruff`; ruff + pytest config sections)
- [x] 1.3 Create `src/slidko/__init__.py` with `__version__ = "0.0.1"` and empty `__init__.py` in subpackages `capture/`, `measure/`, `decode/`, `narrate/`, `diagnose/`, `librarian/`, `corpus/`
- [x] 1.4 Verify: `.venv/bin/pip install -e '.[dev]'` succeeds and `.venv/bin/python -c "import slidko; print(slidko.__version__)"` prints `0.0.1`

## 2. Test wiring

- [x] 2.1 Create `tests/test_package.py`: assert `slidko.__version__` matches `X.Y.Z` pattern; parametrized import test over all seven subpackages
- [x] 2.2 Verify: `.venv/bin/python -m pytest` discovers and passes both tests, exit 0

## 3. Lint and format

- [x] 3.1 Configure ruff in `pyproject.toml` (target py311; enable default lint rules + isort; format settings default)
- [x] 3.2 Verify: `.venv/bin/ruff check .` and `.venv/bin/ruff format --check .` both exit 0

## 4. CI stub

- [x] 4.1 Create `.github/workflows/ci.yml`: on push/PR; ubuntu-latest; Python 3.11; steps = checkout, setup-python, `pip install -e '.[dev]'`, `ruff check .`, `pytest`. (CI runs in a clean runner with no stray user-level tools, so plain commands are correct there — the `.venv/bin/` prefix is only for local agent runs.)
- [x] 4.2 Verify locally (via the `.venv/bin/` equivalents) that each CI step command succeeds
