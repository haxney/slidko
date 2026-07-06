# OpenSpec change apply order

The overnight runner is handed ONE change at a time (`/opsx-apply <name>`). This
is the recommended order. The rule that matters most: **`dev-tooling-gate` is
applied and committed before any code-generating change** — it installs the
checkers/linters/type-checker and freezes the tool config so history never needs
a style-only rewrite again.

## Critical-path (sequential)

1. **`dev-tooling-gate`** — GATE. Pin tools, add mypy, `make check`, clang-format,
   offline pre-commit. Run first; commit before anything else.
2. `bootstrap-python-package` — package skeleton (may already be satisfied on
   disk; run to sync the checkboxes and confirm `make check`).
3. `phase-0-capture-ingest` — `.sr` reader/writer, edge extraction, sigrok-cli
   wrapper.
4. `phase-1-measure-discriminators` — discriminator tree (in progress: 9/22).
5. `phase-2-decode-backend` — normalized event schema + sigrok/native backends.
6. `phase-3-smoke-detector` — edge-math anomaly checks (needs Phase 2 events).
7. `phase-4-narrate` — assertions, address book, receiver-rule caveat.
8. `phase-5-diagnose-loop` — instruction schema, citation enforcement, librarian,
   config pull. First (and only) change permitted to add the LLM SDK dependency.

## Parallel track (any time after the gate; before hardware corpus runs)

- `corpus-tooling` — sidecar schema, one-motion capture CLI, sweep runner,
  field-gold holdout. Consumes Phase 0.
- `exerciser-firmware` — pico-sdk C firmware. **Different toolchain:** uses
  `cmake`/`ctest`/`arm-none-eabi-gcc`/`clang-format`, not the Python `make
  check`. The overnight runner is allowlisted for these and for cloning the
  pinned pico-sdk (`.opencode/agents/overnight.md`), so it provisions the SDK
  itself into the gitignored `firmware/vendor/pico-sdk` (idempotent; needs
  network only on the first run). CI and humans verify it too.

Every change's `tasks.md` ends its groups with the appropriate verification
(`make check` for Python; the C toolchain for firmware). Never proceed past a
red gate.
