## Context

The exerciser firmware exists today as ~750 lines of C/pico-sdk
(`firmware/src/`: `protocol/` policy + `hw/` HAL glue + `ws2812.pio`/`dshot.pio`).
It is compile-verified for both `pico`/`pico2` targets but **never run on real
silicon**, so there is no validated behavior to preserve — only design intent.

CLAUDE.md's language ruling pins the exerciser to C/pico-sdk and declares "zero
Rust in v1," justified (in `docs/EXERCISER.md`) partly on toolchain-openness and
partly — in the author's recollection — on drone-critical protocols (DShot,
WS2812, SBUS) having mature C implementations without Rust equivalents. An
`/opsx:explore` session tested that premise and found it does not hold:

- **DShot/WS2812/SBUS are PIO programs, not C libraries.** The timing-critical
  body (`.wrap_target … .wrap`) is PIO assembly, and it ports to Rust verbatim
  via `pio-proc`/`pio-asm`. The C `% c-sdk {}` init helpers (clock divider,
  shift config) are a dozen lines that map onto `rp235x-hal`. There is no
  `libdshot`-class dependency anywhere — the project already hand-writes its
  PIO (the committed `dshot.pio` is MODERATE-confidence, adapted-by-analogy).
- **`rp235x-hal` fully supports the canonical RP2350A** part with I²C/SPI/PWM/
  UART/GPIO/ADC examples; PIO support is mature.
- **The only genuine "more mature in C" component is the USB device stack**
  (TinyUSB vs `embassy-usb`) — and the exerciser's use is the trivial corner:
  one CDC-ACM interface at trickle rate (the design's own characterization),
  which is the single most-run path in embedded Rust.

So the remembered rationale mislocated the risk. Going to Rust now costs no
validated work, keeps the toolchain open/headless (Rust embedded clears the
CLAUDE.md bar), and lets the exerciser share a substrate with the deferred Rust
pod control plane — collapsing the three-toolchain wire story (nanopb-C /
prost-Rust-pod / Python) toward two.

This design records the technical choices; motivation is in proposal.md,
normative behavior in specs/exerciser-firmware/spec.md.

## Goals / Non-Goals

**Goals:**
- An all-Rust exerciser for RP2350A (ARM Cortex-M33) that preserves the v1
  command set, the `id`-echo/`ok|err` contract, the E9 guard, the hazard
  envelope, and clock-parameterized timing — behavior-identical to the C intent.
- Preserve the load-bearing **policy (no-HAL, host-testable) ↔ hw (HAL-bound)**
  split as Rust modules, so the protocol/policy suite runs on the CI host.
- Carry the protobuf wire contract (from the superseded `exerciser-protobuf-wire`)
  onto a no-std Rust device codec, with a cross-language golden round-trip.
- Keep the toolchain open, headless, and account-wall-free.

**Non-Goals:**
- **No pod code** (guardrail 1). Sharing a Rust substrate is a *future benefit*,
  not built here.
- **No DUT write/control** (guardrail 4). Unchanged — read-only interrogation.
- No real-silicon validation in this change (author away from the bench); it is
  an explicit unmet gate, identical to the C version's status.
- No wire-efficiency work; the control channel is a trickle.

## Decisions

### D1: Rust over C — and treat the C tree as disposable
The C firmware is deleted, not ported line-by-line. It has no hardware miles to
protect, and debugging it to production (hardware loops we cannot run now) only
to discard it for Rust is pure waste. Rollback is `git revert` — the C tree
stays in history. **Alternative considered:** keep C, add Rust only for the pod
later — rejected because it perpetuates a rationale shown to be wrong and keeps
two systems languages (C + Rust) instead of consolidating on one.

### D2: `embassy-rp` + `embassy-usb`, ARM Cortex-M33 core
Use `embassy-rp` (async HAL) with `embassy-usb` for CDC-ACM. Target the **ARM**
core (`thumbv8m.main-none-eabi`), not RISC-V: `rp235x-hal`/HAL interrupt
dispatch on the RP2350 RISC-V core is still incomplete, and there is no reason
to take that risk. **Alternative:** bare `rp235x-hal` + a sync USB stack —
viable, but `embassy-usb` is the better-trodden CDC path and async suits the
one-command-at-a-time loop. Either satisfies the spec; `embassy-rp` is the lean.

### D3: PIO via `pio-proc`, timing constants verbatim from EXERCISER.md
WS2812 and DShot are inline PIO assembly (`pio_proc::pio_asm!`). The DShot
constants (T1:T2:T3 = 3:3:2, T1H = 2×T0H) and the per-rate clock divider are the
same numbers as `docs/EXERCISER.md` and the retired `dshot.pio`. One DShot
program serves 150/300/600 via divider only. This is a straight transliteration,
not a redesign — the risk was always hardware validation, which is unchanged.

### D4: No-std Rust protobuf codec (device side) — carry the wire contract
The wire format decisions from `exerciser-protobuf-wire` are adopted wholesale
and **not relitigated**: length-delimited protobuf, `Command`/`Response`
`oneof` envelopes, `bytes` payloads, typed `ErrorReason` enum, fixed 2-byte LE
length prefix, and **no application-layer CRC** (USB bulk transfer already
carries a per-packet CRC with retransmit and in-order delivery). Only the device
codec changes: nanopb(C) → a **no-std Rust** codec with static/`heapless`
buffers. Candidate crates: `micropb`, `femtopb` (both no-std, no-alloc), or
`prost` + `heapless` (prost wants `alloc`). The choice is an open question (Q1);
the decision that matters here is *no-std, no heap growth on the command path,
oneof + bytes support*. **Alternative:** cast bytes into `repr(C)` structs —
rejected (endianness/versioning footgun, no schema enforcement), same as the
protobuf-wire design concluded.

### D5: Preserve the policy ↔ hw split as Rust modules
Command decode, dispatch, E9 policy, hazard checks, and timing math live in a
host-buildable module set with **no HAL/target dependency**; PIO/I²C/SPI/PWM/
UART/GPIO/ADC/USB live behind that boundary. Enforce with a CI gate: the policy
crate builds and tests on the host (no `thumbv8m` toolchain, no HAL crates), and
a lint/grep check that it imports no `embassy-rp`/`rp235x-hal`. This preserves
the "tests never require hardware" discipline and mirrors the C `protocol/` ↔
`hw/` separation the design docs call load-bearing.

### D6: RP2350 boot IMAGE_DEF via `embassy-rp` feature
The RP2350 bootrom rejects images without a valid IMAGE_DEF block. Use
`embassy-rp`'s `imagedef-secure-exe` feature (or a hand-placed `.start_block`
`ImageDef` if a custom posture is needed later). Flash via UF2/BOOTSEL or
`picotool` — no dependence on probe-rs RP2350 Arm-debug support (which was
lagging). This keeps CI and the flash path headless.

### D7: RP2040 kept as a development target via feature flags
`docs/EXERCISER.md` allows RP2040 for development. `embassy-rp` selects
RP2040 vs RP2350 by Cargo feature, so the clock-parameterized-timing requirement
("migration is a config change") holds at the feature/target level. Lean: keep
RP2040 buildable; do not invest in RP2040-specific validation.

### D8: Supersede `exerciser-protobuf-wire`
That change (0/18 tasks, unimplemented) swaps JSON→nanopb *on the C firmware* —
obsolete once the firmware is Rust. Its wire contract survives here (D4); the
change itself is archived as **superseded-by `rust-exerciser-firmware`**. Its
design.md's deferred pod data-plane rationale (the `bytes samples` / in-place
DMA reasoning) is unaffected and should be preserved when archiving.

## Risks / Trade-offs

- **[`embassy-usb` CDC-ACM has fewer field-miles than TinyUSB, and the entire
  command channel rides on it]** → CDC-ACM is the most-run embedded-Rust path
  and the exerciser's use is trivial (one interface, one bulk pipe, trickle).
  Mitigation: the **first** real-silicon task is a CDC-ACM enumeration spike on
  an actual RP2350A A4; and a TinyUSB **C-FFI shim** is a documented fallback
  (this is the one place the earlier "small C shim for the mature library" idea
  genuinely earns its keep — the shim is USB, not a drone protocol). Do not
  pre-build the shim; reach for it only on a demonstrated failure. Confidence:
  MODERATE-HIGH that stock `embassy-usb` suffices.
- **[No-std Rust protobuf crate maturity / oneof+bytes support]** → codec is
  isolated behind the host-testable boundary (D5) and locked by a cross-language
  (Rust ↔ Python) golden round-trip in CI, so divergence can't hide. Crate
  selection is Q1. Confidence: MODERATE.
- **[RP2350 won't boot without IMAGE_DEF]** → D6 (`embassy-rp` feature); a known,
  solved wrinkle, documented so it isn't rediscovered painfully.
- **[Second systems toolchain]** → net-neutral: C/pico-sdk *and* the separate
  pioasm assembler both leave; Rust + `pio-proc` replace them. Project toolchain
  count (Python + one systems lang) is unchanged.
- **[Reversing a "final — do not relitigate" ruling]** → done deliberately by the
  ruling's owner, on recorded merits; CLAUDE.md and docs/EXERCISER.md are updated
  in the same change so the record does not silently diverge.
- **[Hardware validation still unmet]** → unchanged from C; called out as an
  explicit open acceptance gate in the spec and below.

## Migration Plan

1. Update CLAUDE.md (language ruling) and docs/EXERCISER.md (Platform/Toolchain)
   C→Rust; keep guardrails 1 and 4 intact.
2. Stand up the Cargo firmware workspace: host-testable policy crate + a
   `thumbv8m` binary crate (HAL/USB/PIO). Pin toolchain + target in
   `rust-toolchain.toml`, crates in `Cargo.lock`.
3. Port PIO (WS2812, DShot) to `pio-proc`; unit-test the divider/timing math on
   the host against the EXERCISER.md table.
4. Port policy (decode/dispatch/E9/hazard/timing) to the policy crate; port the
   no-std protobuf codec (D4/Q1); land the cross-language golden round-trip.
5. Wire `embassy-usb` CDC-ACM transport + framing; implement the HAL command
   handlers (i2c/spi/pwm/uart/pio/adc/gpio).
6. Delete the C tree (`firmware/src`, `firmware/test`, `CMakeLists.txt`,
   `pico_sdk_import.cmake`, vendored pico-sdk, `build-pico*`).
7. Replace the CI firmware job with a `cargo build --target thumbv8m.main-none-eabi`
   gate + host policy suite.
8. Archive `exerciser-protobuf-wire` as superseded (preserve its pod data-plane
   design note).
9. **Deferred (human gate):** flash to RP2350A A4 and validate — CDC-ACM
   enumeration first, then per-protocol scope checks against the corpus
   ground-truth requirement.

Rollback: `git revert` the change; the C firmware remains recoverable from
history.

## Open Questions

- **Q1 — No-std protobuf crate:** `micropb` vs `femtopb` vs `prost`+`heapless`.
  Lean: a no-alloc crate (`micropb`/`femtopb`) to keep the command path
  heap-free; confirm oneof + bytes ergonomics and codegen fit the shared
  `.proto`. Resolve before task group "codec."
- **Q2 — `embassy-rp` vs bare `rp235x-hal`:** lean `embassy-rp` (D2); revisit
  only if async pulls in weight the trickle loop doesn't need.
- **Q3 — Pre-build the TinyUSB FFI fallback?** Lean: no — defer until/unless a
  real CDC-ACM failure appears on silicon.
- **Q4 — RP2040 dev target depth:** buildable now (D7); decide later whether it
  earns any validation effort or is build-only.
