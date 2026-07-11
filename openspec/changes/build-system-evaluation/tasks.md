# Tasks: build-system-evaluation

> **This change adopts posture (C)** from design.md: a `mise`-based unified task
> + toolchain layer over the native tools. It does **not** adopt Bazel — that is
> gated on the design.md D5 trigger.
> **Sequencing.** Groups 1–2 + 4–5 (the Python/orchestration spine) can land on
> the *current* tree immediately and are low-risk. Group 3 (firmware + proto
> tasks) is **gated on `rust-exerciser-firmware` + the protobuf wire** landing —
> until then the firmware builds via its existing CMake path and there is no
> `.proto`. Do not wrap a toolchain that is about to be deleted.
> **Reversibility.** Every step is reversible: delete `mise.toml`, restore the
> `Makefile`, revert the CI step. Nothing downstream hard-depends on mise
> internals. No product/pipeline code changes; no attached hardware; flashing and
> on-silicon validation stay explicit human steps.

## 1. Companion decision + mise provisioning

- [ ] 1.1 Resolve O1 (design.md): mise-tasks-only vs mise + `just` for recipe ergonomics. Record the one-line decision in design.md Open Questions. Default to mise-only unless a multi-line recipe need is already evident.
- [ ] 1.2 Pin `mise` itself and document bootstrap: the official `jdx/mise-action` for CI and the one-line installer for local, with a pinned mise version (extends the "exact tool-version pinning" requirement to the orchestrator too). Add any mise state/cache dirs to `.gitignore`. Verify `mise --version` is reproducible on a clean checkout.

## 2. mise.toml — tools + tasks (Python/orchestration spine, current tree)

- [ ] 2.1 `[tools]`: pin the Python interpreter to the `pyproject.toml` floor (3.11) and any current-gate tool that has a mise backend. Verify `mise install` on a clean checkout provisions them with no system `apt`/manual step for the Python side.
- [ ] 2.2 `[tasks]`: define `fmt`, `lint`, `typecheck`, `test`, and `check` (= lint + format-check + typecheck + test — byte-for-byte the current `make check` set) shelling out to ruff/mypy/pytest. Verify `mise run check` reproduces `make check` exactly: identical pass/fail on the committed tree, same tools, same flags.
- [ ] 2.3 Define an all-up `ci` task that is the full gate; confirm mise parallelizes independent subtasks and honors declared task dependencies, and that `mise run ci` is the single canonical command CI will call.

## 3. Firmware + proto tasks — GATED on rust-exerciser-firmware + protobuf wire

- [ ] 3.1 Extend `[tools]`: pin Rust stable + the `thumbv8m.main-none-eabi` target, the chosen no-std proto codec generator, and `picotool`/`elf2uf2`. Verify `mise install` provisions the **full polyglot toolchain** from a clean checkout with no manual toolchain steps.
- [ ] 3.2 Define a `gen-proto` task that runs the device + host generators from the canonical `.proto`; declare `sources = ["**/*.proto"]` and `outputs` so mise skips it when unchanged and re-runs it when the schema changes. Make it a declared dependency of the Python and firmware build/test tasks. NB: this buys *ordering*, not correctness-by-construction — the CI cross-language golden round-trip remains the guarantee layer (design.md D4).
- [ ] 3.3 Define `fw-build` (`cargo build --target thumbv8m.main-none-eabi …`) and `fw-flash` (`cargo run` with the `picotool`/`elf2uf2` runner). Flashing and on-silicon validation are explicit human steps; no hardware in CI. Verify `mise run fw-build` produces the `.elf`/`.uf2` reproducibly.

## 4. Retire the Makefile + wire CI

- [ ] 4.1 Reduce the root `Makefile` to thin aliases delegating to the mise tasks (or remove it), so the canonical command and the aliases cannot drift — satisfies the modified "Unified verification entry point" scenario in the dev-tooling delta.
- [ ] 4.2 Repoint `.github/workflows/ci.yml` verification to `mise run ci` (mise provisions the toolchain via `jdx/mise-action`). Keep the two logical jobs and keep the cross-language golden round-trip as a gate. Verify CI stays headless, open-toolchain, account-wall-free, no attached hardware.

## 5. Spec, docs, validate, commit

- [ ] 5.1 Reconcile the `dev-tooling` delta (this change) at apply/archive: canonical verification command is the mise task; exact-pinning extends from `pyproject.toml` to `mise.toml`. `mypy`, lint/format, pre-commit, and firmware-format requirements are unchanged in behavior.
- [ ] 5.2 Record the **Bazel revisit trigger** (design.md D5) somewhere durable a future contributor will see it — a short pointer in CLAUDE.md or docs — so the deferral is a trip-wire, not a forgotten decision. Note mise as the toolchain/task spine and the one-command entry point in the relevant doc.
- [ ] 5.3 `openspec validate build-system-evaluation --strict` clean; commit naming the task groups.
