# Proposal: dev-tooling-gate

## Why

The first overnight runs produced lint-dirty history that had to be rewritten
(`lint: apply pre-commit hooks`, `fix imports: stdlib → third-party → local`,
`config: refine ruff settings` — all after the fact). The cause was tooling
that tightened *after* code already existed: rules were added, a formatter
reflowed everything, a type checker was never run at all. This change closes
that hole once, before any further code generation.

**This change is the ordering gate for the whole project.** It MUST be applied
and committed before any code-generating change (`phase-0` onward, plus the
parallel `corpus-tooling` and `exerciser-firmware` tracks). Its job: freeze the
full checker/formatter/type-checker set, wire them into one command that CI and
the overnight runner both call, and pre-install the pre-commit environments so
later offline runs never touch the network. After this lands, every task in
every downstream change ends by running the same `make check`, so code is born
clean and history is never rewritten for style again.

Scope note: the manual bootstrap already created `pyproject.toml`, a ruff
config, a `.pre-commit-config.yaml`, and a CI stub. This change does **not**
re-create them — it hardens them: adds the missing type checker (mypy), pins
every tool to an exact version so a tool update can never silently reformat the
tree, adds a C formatter for the `firmware/` tree, and unifies verification
behind `make check`.

## What Changes

- Pin every dev tool to an exact version in `[project.optional-dependencies]
  dev` (ruff, mypy, pytest, pre-commit, hypothesis) so upgrades are deliberate
  commits, never ambient drift.
- Add **mypy** with a pragmatic-strict config (typed defs required in `src/`,
  relaxed for `tests/`, missing-stub imports ignored for scipy). This is the
  checker that was entirely absent and is the main anti-churn addition.
- Freeze the ruff lint rule set and format settings, and document them as
  closed: rules are not added later (adding a rule reformats existing code —
  exactly the churn we are eliminating).
- Add a `Makefile` (or `noxfile`) exposing `fmt`, `lint`, `typecheck`, `test`,
  and `check` (= all four, no mutation). CI and the overnight runner both call
  `make check`; the commands never diverge.
- Expand pre-commit with a local mypy hook (runs the venv mypy, no network) and
  a few safe repo hygiene hooks; pin all hook `rev`s.
- Add a `clang-format` config for `firmware/` so the C exerciser tree cannot
  accumulate style churn either.
- Pre-install pre-commit hook environments during this change (network
  available now) so overnight runs — which have network denied — can still run
  `pre-commit run` offline.
- Update CI to run `make check` (install → ruff → ruff-format-check → mypy →
  pytest) as the single gate.

## Capabilities

### New Capabilities

- `dev-tooling`: adds type checking, exact tool-version pinning, a unified
  `make check` verification entry point, an offline-capable pre-commit gate,
  and firmware C-formatting — on top of the lint/format/test scaffolding the
  bootstrap already provides.

### Modified Capabilities

(none — additive requirements under the same capability name; the bootstrap
change's `dev-tooling` requirements are unaffected)

## Impact

- Touches `pyproject.toml` (dev deps + `[tool.mypy]`), `.pre-commit-config.yaml`,
  `.github/workflows/ci.yml`, adds `Makefile` and `.clang-format`.
- No `src/` behavior changes; this is pure tooling.
- Downstream changes gain one standing rule: **every task group ends with
  `make check` green** (already the overnight runner's habit; now the command
  is canonical and includes type checking).
