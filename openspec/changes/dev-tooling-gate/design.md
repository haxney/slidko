# Design: dev-tooling-gate

## Context

History was rewritten twice for style. The fix is not "be more careful" — it is
to make the tooling incapable of drifting: pin exact versions, run the same
checks everywhere, and add the one class of checker (static typing) that was
missing. This design fixes the exact configuration so the overnight runner
(qwen3-coder:30b) can implement it verbatim without judgment calls.

Anti-churn is the whole point, so the design errs toward *freezing* decisions,
not leaving them open.

## Decisions

### Exact-version pinning (not floors)

Dev dependencies use `==`, not `>=`. A `>=` floor lets a fresh `pip install`
pull a newer ruff/mypy that reformats or newly-flags the tree — the drift we are
killing. Verified current versions on PyPI as of 2026-07-06 (use these exact
pins unless a newer one is deliberately chosen):

```toml
[project.optional-dependencies]
dev = [
    "pytest==9.1.1",
    "ruff==0.15.20",
    "mypy==1.20.2",
    "pre-commit==4.6.0",
    "hypothesis==6.156.1",
]
```

Rationale for each: `pytest` is the runner (already used). `ruff` is
lint+format (already used; pin the version already in `.pre-commit-config.yaml`
so hook and venv agree — a mismatch there is itself a churn source).
`mypy` is the new type checker. `pre-commit` runs the hook set. `hypothesis`
is property-based testing, which the phase-0/phase-1 specs already call for
("property tests: synthetic square waves round-trip exactly") but which is not
yet declared as a dependency — declare it here so no later change edits deps
just to add it.

### mypy config — pragmatic-strict, numpy-aware

numpy ships inline types; scipy's are partial. Full `--strict` on numpy-heavy
DSP code produces noise that qwen will "fix" by scattering `# type: ignore`,
which is worse than no typing. The considered middle:

```toml
[tool.mypy]
python_version = "3.11"
files = ["src", "tests"]
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_return_any = true
no_implicit_optional = true
warn_unused_configs = true

[[tool.mypy.overrides]]
module = ["scipy", "scipy.*"]
ignore_missing_imports = true

[[tool.mypy.overrides]]
module = ["tests.*"]
disallow_untyped_defs = false
disallow_incomplete_defs = false
```

`warn_return_any = true` is the rule that would have caught the real bug already
in the tree: `src/slidko/measure/i2c.py` annotates returns as `dict[str, any]`
(lowercase builtin `any`, not `typing.Any`) — mypy flags this. Do not "fix" it
by loosening the config; fix the annotation (`dict[str, Any]`) when the type
checker is turned on. That single correction is expected and in-scope for the
verification task below.

### One command, everywhere: `make check`

CI and the overnight runner drifted because each spelled the checks
differently. Canonicalize in a `Makefile`:

```make
.PHONY: fmt lint typecheck test check
PY := .venv/bin/python
fmt:
	.venv/bin/ruff format .
	.venv/bin/ruff check --fix .
lint:
	.venv/bin/ruff check .
	.venv/bin/ruff format --check .
typecheck:
	.venv/bin/mypy
test:
	$(PY) -m pytest
check: lint typecheck test
```

`check` mutates nothing (it is the gate); `fmt` is the only mutating target.
CI runs `make check`; the overnight runner runs `make check` after every task
group. They cannot diverge because it is literally the same target. (The
`.venv/bin/` prefix is correct for local/overnight runs; in the CI runner the
tools are on `PATH` after `pip install -e .[dev]`, so CI may call the tools
directly OR create the same venv — the tasks below pick the venv path so CI and
overnight are byte-identical.)

### Ruff rule set is closed

The current selection (`I,E,W,F,UP,B,A,C4,DTZ,ISC,G,PGH,PIE,PL,PT,RUF,SIM,TID,
TCH`, ignoring `PLR`) is comprehensive and stays. Add `N` (pep8-naming) now —
it is high value and cheap while the tree is small; adding it later would be
churn. After this change, **the rule set is frozen**: a downstream change that
wants a new rule must accept it will reformat/re-flag existing code and do so as
its own explicit, reviewed commit — never as a drive-by. State this in the
`pyproject.toml` as a comment so the next agent does not "helpfully" expand it.

### Offline pre-commit

The overnight runner has `websearch`/`webfetch` denied and a bash allowlist.
pre-commit downloads each hook's environment from GitHub on first run. If that
first run happens overnight, it fails and can read as a red gate. Mitigation:
this change runs `pre-commit install-hooks` (or `pre-commit run --all-files`)
now, while network is available, populating `~/.cache/pre-commit`. The mypy
hook is declared as a **local** hook that calls the venv mypy, so it needs no
download at all — the most robust option for the checker most likely to run in
a denied-network context.

### firmware/ C formatting

`exerciser-firmware` is C. Without a pinned formatter it will churn exactly like
the Python tree did. Add a `.clang-format` (LLVM base, 4-space indent, 100-col)
at repo root now, so the firmware change inherits it from task one. clang-format
is a system tool (not pip); CI installs it via apt in the firmware job, and the
firmware tasks call `clang-format --dry-run --Werror` as their style gate.

## Risks / Trade-offs

- [mypy on numpy DSP is noisy] → config is pragmatic-strict, not `--strict`;
  scipy stubs ignored; the one real pre-existing type bug is fixed, not
  suppressed. If a specific numpy expression genuinely cannot be typed, a
  single narrowly-scoped `# type: ignore[code]` with the error code is allowed
  (and `warn_unused_ignores` keeps them honest).
- [Pinning goes stale] → acceptable and intended: updates become visible,
  reviewed commits. A dependabot-style bump is a future nicety, not v1 scope.
- [pre-commit still needs network the very first time] → run it during this
  change (network available); the local mypy hook needs none regardless.
