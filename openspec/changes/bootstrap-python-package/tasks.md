# Tasks: bootstrap-python-package

## 1. Package skeleton

- [ ] 1.1 Create `pyproject.toml` (hatchling backend; project `slidko`, `requires-python >= 3.11`; deps numpy, scipy; `[project.optional-dependencies] dev = pytest, ruff`; ruff + pytest config sections)
- [ ] 1.2 Create `src/slidko/__init__.py` with `__version__ = "0.0.1"` and empty `__init__.py` in subpackages `capture/`, `measure/`, `decode/`, `narrate/`, `diagnose/`, `librarian/`, `corpus/`
- [ ] 1.3 Verify: `pip install -e .[dev]` succeeds and `python -c "import slidko; print(slidko.__version__)"` prints `0.0.1`

## 2. Test wiring

- [ ] 2.1 Create `tests/test_package.py`: assert `slidko.__version__` matches `X.Y.Z` pattern; parametrized import test over all seven subpackages
- [ ] 2.2 Verify: `pytest` discovers and passes both tests, exit 0

## 3. Lint and format

- [ ] 3.1 Configure ruff in `pyproject.toml` (target py311; enable default lint rules + isort; format settings default)
- [ ] 3.2 Verify: `ruff check .` and `ruff format --check .` both exit 0

## 4. CI stub

- [ ] 4.1 Create `.github/workflows/ci.yml`: on push/PR; ubuntu-latest; Python 3.11; steps = checkout, setup-python, `pip install -e .[dev]`, `ruff check .`, `pytest`
- [ ] 4.2 Verify locally that each CI step command succeeds in a fresh shell at repo root
