## Why

The project's cross-language surface is about to change materially. The pending
`rust-exerciser-firmware` change rewrites the firmware C→Rust and the wire
JSON→protobuf, which (a) collapses the genuinely *shared* build artifact to a
single `.proto`, and (b) adds a second native toolchain — Cargo alongside
hatchling/pip, with CMake living on only until the C tree is deleted. The owner
is drawn to Bazel (deep Blaze familiarity from Google) for the "one way to
invoke any build or test" property and Blaze's seamless cross-language
integration. Per the project's own `dev-tooling-gate` discipline, a build-system
choice is the single largest possible tooling change and deserves its own
reviewed evaluation with an explicit decision — not to be defaulted into a
per-language toolchain mix by inertia, nor smuggled into the Rust rewrite.

This is cross-cutting tooling governance (like the archived `dev-tooling-gate`
before it); it maps to no single docs/ROADMAP.md phase or docs/TASKS.md item.
It is coupled to the "Parallel track — bench corpus & exerciser firmware" work
and specifically to the `rust-exerciser-firmware` change (proto-codec choice).

## What Changes

- Evaluate three coherent postures — **(A)** full Bazel now, **(C)** keep native
  toolchains unified by a task runner + toolchain manager, **(D)** defer Bazel to
  the pod boundary — against this project's *actual* shape (2 languages, 1 shared
  `.proto`, 1 developer, tiny build volume). A fourth, Bazel-for-proto-only, is
  evaluated and rejected in design.md.
- **Decision (recorded, not yet implemented):** adopt a **mise**-based unified
  task + toolchain layer over the native tools **now**; **defer Bazel** behind an
  explicit revisit trigger. Rationale, including a deliberate "is Bazel cheaper
  than it looks in 2026?" pass, is in design.md.
- Introduce a `mise.toml` that (i) pins the *polyglot* toolchain — Python, Rust +
  `thumbv8m.main-none-eabi` target, the proto codec generator, `picotool` — and
  (ii) defines tasks (`check`, `test`, `build`, `fmt`, `gen-proto`, firmware
  `build`/`flash`) that fan out to the native tools. `just` is evaluated as an
  optional companion for recipe ergonomics; mise-only vs mise+just is decided in
  design.md.
- **Modify `dev-tooling`:** generalize the "unified verification entry point"
  requirement so the canonical command is the mise task (CI invokes the same),
  and **extend** "exact tool-version pinning" from Python-only (`pyproject.toml`)
  to the whole toolchain (`mise.toml`). Retire the root `Makefile` in favor of
  mise tasks (or keep it as a thin alias).
- Record a **Bazel adoption trigger** and the finding that the firmware
  **proto-codec choice (`prost` vs `micropb`/`femtopb`) is coupled to future
  Bazel cost** — surfaced as a note to `rust-exerciser-firmware`.

## Capabilities

### New Capabilities
<!-- none — this modifies the existing dev-tooling capability -->

### Modified Capabilities

- `dev-tooling`: the "unified verification entry point" requirement's canonical
  command generalizes from `make check` to a mise task (CI still invokes the one
  canonical command); the "exact tool-version pinning" requirement extends from
  Python dev tools in `pyproject.toml` to the full polyglot toolchain declared in
  `mise.toml`; the "headless CI entry point" requirement's steps invoke the mise
  task. Behavior of the type-check, lint/format, pre-commit, and firmware-format
  requirements is unchanged — only the invocation and provisioning layer moves.

## Impact

- **New dev dependency:** `mise` (single static Rust binary, no runtime,
  self-installs pinned tools; open, headless, account-wall-free — clears the
  CLAUDE.md toolchain bar). Optionally `just` (also a single static Rust binary).
- `Makefile` → mise tasks; `.github/workflows/ci.yml` verification steps call the
  mise task; `.pre-commit-config.yaml` aligned but functionally unchanged.
- **No product/pipeline code changes; no guardrail impact.** This is tooling
  governance, not a scope or capability change to the debugging pipeline.
- **Couples to `rust-exerciser-firmware`:** the codec decision there (`prost`
  gets a first-class Bazel proto rule but needs `alloc`; `micropb`/`femtopb` are
  alloc-free but have no Bazel proto rule) changes the cost of a *future* Bazel
  migration and should be chosen with that in view. Supersedes nothing.
- **Decision is reversible:** deleting `mise.toml` and restoring the `Makefile`
  is trivial; nothing downstream hard-depends on mise internals.
