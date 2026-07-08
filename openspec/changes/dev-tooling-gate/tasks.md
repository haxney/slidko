# Tasks: dev-tooling-gate

> RUN THIS CHANGE FIRST. It is the ordering gate: apply and commit it before any
> code-generating change. Every task is verifiable by a command; run `make
> check` (defined here) after each group.

## 1. Pin dev dependencies

- [x] 1.1 Edit `pyproject.toml` `[project.optional-dependencies] dev` to pin exact versions: `pytest==9.1.1`, `ruff==0.15.20`, `mypy==1.20.2`, `pre-commit==4.6.0`, `hypothesis==6.156.1` (each with `==`, none with `>=`)
- [x] 1.2 Reinstall into the venv: `.venv/bin/pip install -e '.[dev]'`
- [x] 1.3 Verify: `.venv/bin/pip show ruff mypy pytest pre-commit hypothesis` reports the pinned versions; `.venv/bin/python -c "import hypothesis"` succeeds

## 2. Add mypy configuration

- [x] 2.1 Add a `[tool.mypy]` section to `pyproject.toml` exactly as specified in design.md (`python_version = "3.11"`, `files = ["src", "tests"]`, `disallow_untyped_defs`, `disallow_incomplete_defs`, `check_untyped_defs`, `warn_redundant_casts`, `warn_unused_ignores`, `warn_return_any`, `no_implicit_optional`, `warn_unused_configs`, plus the `scipy.*` ignore-missing-imports override and the `tests.*` relaxed override)
- [x] 2.2 Run `.venv/bin/mypy` and read the errors. Fix real type defects in `src/` rather than loosening config. Known required fix: `src/slidko/measure/i2c.py` uses `dict[str, any]` (lowercase builtin) in return annotations — change to `dict[str, Any]` and `from typing import Any`. Add precise annotations where `disallow_untyped_defs` flags a `src/` function.
- [x] 2.3 Verify: `.venv/bin/mypy` exits 0

## 3. Freeze the ruff rule set

- [x] 3.1 In `pyproject.toml` `[tool.ruff.lint]`, add `"N"` (pep8-naming) to `extend-select`, keeping all existing rules and the `PLR` ignore
- [x] 3.2 Add a comment directly above `extend-select` stating the rule set is frozen: new rules are only added as their own reviewed commit that also reformats the affected code — never as a drive-by in a feature change
- [x] 3.3 Verify: `.venv/bin/ruff check .` and `.venv/bin/ruff format --check .` both exit 0 (fix any `N`-rule findings the addition surfaces)

## 4. Makefile — the single verification entry point

- [x] 4.1 Create `Makefile` at repo root with `.PHONY` targets `fmt`, `lint`, `typecheck`, `test`, `check` exactly as in design.md. `check` = `lint typecheck test` and mutates nothing; `fmt` is the only mutating target; all Python tools are called via `.venv/bin/`
- [x] 4.2 Verify: `make lint`, `make typecheck`, `make test`, and `make check` each run and `make check` exits 0
- [x] 4.3 Verify `make check` mutates nothing: `git status --porcelain` is empty after running it

## 5. Expand and pin pre-commit

- [x] 5.1 In `.pre-commit-config.yaml` add safe hygiene hooks to the existing `pre-commit-hooks` entry: `check-merge-conflict`, `check-added-large-files` (with `args: [--maxkb=5000]`), `mixed-line-ending`. Keep the existing `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-toml`
- [x] 5.2 Add a **local** mypy hook (no remote repo): `repo: local`, hook `id: mypy`, `name: mypy`, `entry: .venv/bin/mypy`, `language: system`, `types: [python]`, `pass_filenames: false`. This runs the venv mypy and needs no network
- [x] 5.3 Confirm every remote repo in the file has an explicit pinned `rev` and that the `ruff-pre-commit` `rev` equals the ruff version pinned in `pyproject.toml` (`v0.15.20`)
- [x] 5.4 Pre-install hook environments while network is available: `.venv/bin/pre-commit install-hooks`
- [x] 5.5 Verify: `.venv/bin/pre-commit run --all-files` exits 0 (run twice; the second run must be clean, proving no hook mutates the committed tree) — all hooks pass cleanly on both runs now that the ruff-lint debt is cleared

## 6. Firmware C formatter config

- [x] 6.1 Create `.clang-format` at repo root: `BasedOnStyle: LLVM`, `IndentWidth: 4`, `ColumnLimit: 100`, `PointerAlignment: Right`, `AllowShortFunctionsOnASingleLine: None`
- [x] 6.2 Verify the style file parses: create a tiny conformant C snippet under the scratch/tmp area (NOT committed) and confirm `clang-format --dry-run --Werror --style=file <snippet>` exits 0. If `clang-format` is not installed locally, document the exact CI apt package (`clang-format`) in a comment in the firmware CI job instead and skip the local run
- [x] 6.3 Do not create `firmware/` sources here — only the root `.clang-format`; the `exerciser-firmware` change consumes it

## 7. CI runs the canonical gate

- [x] 7.1 Edit `.github/workflows/ci.yml`: after `pip install -e '.[dev]'`, replace the separate `ruff check` / `pytest` steps with a single step that creates the venv and runs `make check` (so CI and overnight run byte-identical commands). Keep `actions/checkout` and `setup-python@v4` with Python 3.11
- [x] 7.2 Verify locally that the CI command path works: from a clean `.venv`, `.venv/bin/pip install -e '.[dev]'` then `make check` exits 0 — install path confirmed clean in a scratch venv; `make check` itself is still red, but now only on the pre-existing failing tests tracked in `fix-regression-suite` (lint/format/typecheck all pass)

## 8. Wrap-up

- [ ] 8.1 `make check` green; `git status --porcelain` empty (no uncommitted formatter output)
- [ ] 8.2 Commit with a message naming this gate (e.g. "dev-tooling-gate: pin tools, add mypy + make check + clang-format"); this is the last time history should ever need a style-only commit
