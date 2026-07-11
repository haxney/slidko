## Context

Today the build is two worlds glued by CI convention:

```
  PYTHON WORLD                         FIRMWARE WORLD
  hatchling + pip (pyproject.toml)     CMake + pico-sdk (vendored)
  ruff / mypy / pytest                 arm-none-eabi-gcc, ctest, clang-format
  orchestrated by a 20-line Makefile   cross-compiles pico + pico2
  → CI job "test": `make check`        → CI job "firmware": cmake ×3 + ctest
```

The pending `rust-exerciser-firmware` change reshapes the surface this decision
sits on. After it lands, the state is:

```
  PYTHON (host)  ──depends on──►  ┌─────────┐  ◄──depends on──  RUST firmware crate
  hatchling/pip                   │ .proto  │                   Cargo, embassy-rp, no_std
  (unchanged)                     └─────────┘                   thumbv8m cross-compile
                                (the ONE shared artifact)        no-std proto codec
```

Two native toolchains (hatchling/pip, Cargo) plus a transient CMake, and the
cross-language integration collapses to a **single shared node: the `.proto`**.
Everything else is single-language. This is the fact that governs the decision.

**Governance framing.** The `dev-tooling-gate` discipline (archived) established
that tooling changes are their own reviewed commits, never drive-bys — a rule
set is frozen and only changed deliberately. A build-system swap is the maximal
instance of that class, so it gets its own evaluation and an explicit, recorded
decision with a revisit trigger, so it is not relitigated ad hoc.

## Goals / Non-Goals

**Goals:**
- Decide the build/orchestration posture for the post-Rust, post-protobuf state,
  with a recorded rationale and an explicit Bazel-revisit trigger.
- Honestly re-price Bazel against its *2026* open-source state (not 2018 lore),
  because the owner's intuition that "some Blaze magic was Google infra" is
  correct but the gap has narrowed — find where it is genuinely cheaper than
  expected.
- Introduce `mise`/`just` accurately for a reader who has not used them, and say
  precisely which slice of the Bazel value they do and do not deliver.
- Preserve the load-bearing `dev-tooling` properties: one canonical verification
  command, exact tool pinning, local == CI == overnight.

**Non-Goals:**
- Not adopting Bazel now, and not building any Bazel scaffolding in this change.
- Not re-deciding the firmware language or the wire format — those are the
  `rust-exerciser-firmware` change; this only *couples* the codec choice to
  future Bazel cost.
- No product/pipeline behavior change. No remote-execution / RBE infrastructure.

## Decisions

### D1 — The choice is between three coherent stances, not a spectrum

Because the firmware is *simultaneously* the weakest Bazel case (embedded,
Cargo-native ecosystem) **and** a consumer of the strongest Bazel case (the
`.proto`), you cannot cleanly split "Bazel for shared stuff, Cargo for
firmware" — the firmware is a shared-stuff consumer. That leaves:

- **(A) Full Bazel now.** Birth the Rust firmware Bazel-native; `pip`+`cargo` →
  `bzlmod`. Highest payoff on the proto node and single-invocation; you eat the
  embedded-Rust-under-Bazel cost + no-remote-cache tax at the least-justified
  moment; cheapest tree you'll ever have to convert.
- **(C) Native toolchains, unified invocation + provisioning** (mise/just). ~80%
  of the "one command" appeal + toolchain reproducibility, zero ecosystem
  friction, ~1 day. No airtight proto graph, no content-addressed caching.
- **(D) Defer Bazel to the pod boundary.** Land Rust-on-Cargo now; adopt Bazel
  when a genuine third language + streaming daemon + CI fleet arrive.

**(B) Bazel-for-proto-only is rejected.** Bazel owning codegen while Cargo and
hatchling consume its outputs creates a two-build-system handshake at the proto
line — more moving parts than either pure choice, and it forfeits Bazel's whole
point (one graph). Not pursued.

**Decision: adopt (C) now with mise; treat (A) as the real Bazel decision,
gated on the (D) trigger.** These are not in tension — (C) is what you run until
the (A) trigger fires.

### D2 — Re-pricing Bazel: where it is cheaper than expected (and where it isn't)

The owner asked specifically to hunt for this. The honest finding: the
2024–2026 Bazel is materially cheaper than the WORKSPACE-era memory, on several
axes verified against current rules_rust / rules_python docs and community
reports.

**Cheaper than expected:**

1. **Third-party is now automated from the *native* manifests.** With bzlmod the
   default (Bazel 7+/8), `crate.from_cargo` ingests your real `Cargo.toml` +
   `Cargo.lock` and generates all Rust dep targets — you keep editing Cargo
   manifests normally. `rules_python`'s `pip.parse` does the same from a
   requirements lock. The "you hand-maintain a `third_party/` translation
   layer" cost — the thing that was *staffed* at Google — is largely gone.
2. **`no_std` embedded cross-compile is supported, not exotic.** rules_rust
   "fully supports platforms"; a `thumbv8m.main-none-eabi` target is
   `rust.toolchain(extra_target_triples = [...])` + a `platform()`. Working
   community write-ups exist (e.g. Asnaghi, "Bazel for Rust embedded"). The one
   real wrinkle the docs flag is supplying a **linker outside the standard Rust
   toolchain** — bounded, one-time config, not a research project.
3. **`rust_prost_library` is a first-class proto rule.** *If* the firmware codec
   is `prost` (one of the three candidates in `rust-exerciser-firmware`), the
   entire proto graph — Python (`py_proto_library`), firmware, future pod — is
   native Bazel rules. This directly softens the "inverted ROI" worry.
4. **The "Bazel feels slow on a laptop" problem has a one-line fix.**
   `--disk_cache=<dir>` in `.bazelrc` gives free, zero-infra local content-
   addressed caching; GitHub Actions cache can back a shared cache in CI. You do
   not need to stand up RBE to stop paying the cold-analysis tax repeatedly.
5. **Toolchain hermeticity is download-on-demand.** `bazelisk` + `.bazelversion`
   pins Bazel like rustup; `rules_python` fetches a hermetic CPython; rules_rust
   fetches the Rust toolchain. The "it just works because the machine was set
   up" property is now largely built in.

**Still genuinely costly (the residue):**

- **The alloc-free codecs have no Bazel proto rule.** `micropb`/`femtopb` are
  `build.rs`/generator-driven; under Bazel you disable build scripts and run
  their codegen as a hand-rolled `genrule`. So the *clean* proto story (point 3)
  holds only if you pick `prost` — which needs `alloc` on the device. This is a
  real coupling, captured in D6.
- **ruff/mypy/pytest are source-tree tools.** Fine-grained Bazel-ification
  (per-module `py_test`, mypy-as-aspect) is high-effort and low-reward here; in
  practice you'd wrap them coarsely — which leads directly to D3.
- **No free RBE.** Disk cache removes most of the pain, but the *distinctive*
  Blaze-at-scale experience (shared remote cache across a fleet) is still infra
  you would own.

Net: Bazel's floor cost dropped a lot; its *distinctive* value still needs
scale to justify. The migration is cheaper than feared, but the thing it buys is
not yet worth much here.

### D3 — The convergence insight (why cheap-Bazel and mise/just meet in the middle)

The cheap way to adopt Bazel for the Python side is coarse `sh_test`/`genrule`
wrappers around `pytest`/`ruff`/`mypy`/`cargo`. But a coarse wrapper that shells
out to the native tool is *exactly what a task runner does natively* — with far
less conceptual overhead and no analysis phase. So:

```
   cheap Bazel (coarse wrappers)  ──────►  converges toward  ◄────── mise/just
                                                                      (native shell-out)

   Bazel's DISTINCTIVE value  ──requires──►  fine-grained targets + content cache
                                             + shared remote cache (= "expensive Bazel")
```

If you are going coarse-grained anyway (correct for a small tree), mise/just is
the lighter tool for that exact job. Bazel only pulls decisively ahead when you
commit to fine granularity + a shared cache — which is the scale case (D) waits
for. This is why (C) and "cheap Bazel" are near-substitutes today, and (C) wins
on simplicity.

### D4 — What `mise` and `just` actually are (primer + choice)

The owner has not used either; both are single static Rust binaries, no runtime,
CI-friendly — they "reinvent no wheels," they *shell out to the native tools on
their native paved roads* (`cargo build --target …`, `cargo run` with a flash
runner, `pytest`, `protoc`/codec generators). That property is the whole reason
they fit here: the embedded-Rust-under-Bazel dirt track simply does not exist
for them, because they use Cargo directly.

- **`just`** — a *command runner*: the modern `make` with only the task half
  (no build graph, no timestamp deps, no incremental builds). A `justfile` has
  named, parameterized recipes with inter-recipe dependencies
  (`build: gen-proto`), self-documenting (`just --list`). It does **not** manage
  tool versions, environments, or caching.
- **`mise`** — a *superset for this purpose*: tool-version manager **+**
  per-project env **+** task runner in one `mise.toml`. It pins and installs the
  polyglot toolchain (Python, Rust + target, protoc, picotool), so `mise install`
  provisions the whole cross-language toolchain reproducibly; tasks then run with
  the right versions automatically. mise runs independent tasks **in parallel**,
  honors task dependencies, and can **skip unchanged work** via declared
  `sources`/`outputs` — a coarse, make-like incrementalism `just` lacks.

Feature map against the stated goal ("Bazel's unified build/test without
reinventing the wheel for poor-Bazel-support cases"):

| Capability                                   | Bazel        | mise (+just)              | current (Makefile+CMake) |
|----------------------------------------------|--------------|---------------------------|--------------------------|
| One command for everything                   | ✓            | ✓                         | partial (fw job separate)|
| Tool-version pinning / provisioning          | ✓ (hermetic) | ✓ (mise installs & pins)  | ✗ (apt + .venv)          |
| Cross-language proto node (correct-by-constr)| ✓ airtight   | ✗ (task *ordering* only)  | ✗                        |
| Incremental / caching                        | ✓ CAS        | ~ (mise sources/outputs;  | make: timestamps; cmake ✓|
|                                              |              |   tools self-cache)       |                          |
| Hermeticity / reproducible builds            | ✓✓           | ~ (pins versions, no sbox)| ✗                        |
| Remote cache / RBE                            | ✓ (infra)    | ✗                         | ✗                        |
| Reinvents wheels for weak-support cases      | yes (no_std, | **no — shells out to      | n/a (native)             |
|                                              | flashing)    | cargo/picotool natively** |                          |
| Adoption cost                                | high         | ~1 day                    | none (present)           |

**Decision: mise as the spine, `just` optional.** mise alone covers tasks; its
distinctive win here is that it *also* solves polyglot toolchain provisioning —
half of why one reaches for Bazel — which `just` does not. Whether to add `just`
purely for nicer recipe syntax is a low-stakes ergonomics call left open (O1).
The honest limitation vs Bazel: mise task deps give **ordering**
(`build-firmware: gen-proto`), not **correctness-by-construction** — nothing
stops a stale generated file if a task is skipped. That gap is covered exactly as
today: the CI cross-language golden round-trip test the protobuf design already
mandates. We trade a build-graph guarantee for a test-suite guarantee — the same
posture the project already runs on.

### D5 — Decision and Bazel revisit trigger

**Now:** implement (C) with mise. **Revisit Bazel (evaluate A) when any fires:**

- The **pod** work starts (ARCHITECTURE.md § Deferred) — a genuine *third*
  language surface (Rust streaming daemon) + non-trivial build volume, i.e. the
  point the curve turns; **or**
- contributors > 1 or a CI fleet appears (shared remote cache becomes worth
  owning); **or**
- the proto-divergence-by-convention actually bites (a Python↔device schema skew
  ships despite the golden test) — evidence the ordering-not-guarantee gap is
  real, not theoretical.

Until then, mise is the posture; Bazel is a documented option with a trip-wire,
not a backlog item.

### D6 — Coupling to `rust-exerciser-firmware`: the codec choice pre-pays or forecloses cheap Bazel

The three codec candidates differ in *future* build-system cost, not just device
footprint:

- **`prost` (+ `heapless`)** → first-class `rust_prost_library`; a later Bazel
  migration keeps the whole proto graph native. Cost: needs `alloc` on-device.
- **`micropb` / `femtopb`** → alloc-free (better embedded fit), but **no Bazel
  proto rule** → codegen becomes a `genrule` in any future Bazel world.

This does not force the codec decision, but it should be *made in view of it*.
Recommendation to record on `rust-exerciser-firmware`: if `alloc` is acceptable
on the RP2350A (embassy supports a global allocator), `prost` keeps the cheap-
Bazel door open at low cost; if alloc-free is a hard requirement, accept that a
future Bazel adoption pays a genrule tax on device codegen (still bounded). Either
way, the mise posture (C) is unaffected — it shells out to whichever generator.

## Risks / Trade-offs

- **[mise gives ordering, not a correctness-guaranteed proto graph]** → a stale
  generated codec could pass locally. Mitigation: the mandated CI C/Rust↔Python
  golden round-trip is the guarantee layer (same as today); make `gen-proto` a
  declared dependency of both `build` tasks with `sources`/`outputs` so mise
  re-runs it when the `.proto` changes.
- **[Yet another tool to learn / a second config file]** → mise + `mise.toml`
  atop `pyproject.toml`. Mitigation: mise replaces the `Makefile` and the ad-hoc
  "install these system packages" README lore, so net tool count is roughly flat;
  reversible (delete `mise.toml`, restore `Makefile`).
- **[mise not preinstalled on CI / contributor machines]** → one bootstrap step.
  Mitigation: mise has an official GitHub Action and a one-line installer; pin its
  version like every other tool (extends the existing pinning requirement).
- **[Choosing mise now forecloses Bazel later]** → it does not. (C) and (A) are
  sequential, not exclusive; mise tasks are a thin façade a future Bazel adoption
  can call or replace target-by-target.
- **[Underpricing Bazel and regretting the deferral]** → mitigated by the D5
  trip-wire: the decision is *time-boxed to a trigger*, not "never."

## Migration Plan

Implementation is out of scope for this evaluation change (explore-mode capture);
this is the intended shape for the follow-on apply, plus rollback.

1. Add `mise.toml`: `[tools]` pinning Python 3.11, Rust stable +
   `thumbv8m.main-none-eabi`, the proto codec generator, `picotool`; `[tasks]`
   for `fmt`, `lint`, `typecheck`, `test`, `gen-proto`, `check`
   (= lint+typecheck+test, the current `make check` set), `fw-build`,
   `fw-flash`, and an all-up `ci`.
2. Wire `gen-proto` as a dependency of the Python and firmware build/test tasks
   with `sources = ["proto/*.proto"]` / `outputs` so it re-runs on schema change.
3. Repoint `.github/workflows/ci.yml` verification steps to `mise run ci` (mise
   provisions the toolchain), preserving the two logical jobs; keep the
   cross-language golden round-trip as the proto-graph guarantee.
4. Retire the root `Makefile` (or reduce it to `check: ; mise run check` aliases
   for muscle memory). Update the `dev-tooling` spec's "unified verification
   entry point" + "exact tool-version pinning" requirements accordingly.
5. **Rollback:** delete `mise.toml`, restore the `Makefile`, revert the CI
   step. No downstream artifact hard-depends on mise internals.

## Open Questions

- **O1 — mise-only vs mise + just?** mise tasks are TOML/file-based; `just`'s
  recipe syntax is nicer for multi-line shell. Low stakes; decide at apply time.
- **O2 — Where does proto codegen output live** so both Cargo and hatchling
  consume it cleanly (checked-in generated code vs task-generated into a
  build dir)? Interacts with `rust-exerciser-firmware` layout; resolve there.
- **O3 — Does the RP2350A firmware accept `alloc`?** Gates whether `prost`
  (cheap-Bazel-later) is viable vs an alloc-free codec (D6). Owned by
  `rust-exerciser-firmware`; recorded here as the coupling point.
