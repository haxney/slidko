# Design: phase-5-diagnose-loop

## Context

Diagnose closes the poke loop: LLM abductive reasoning over Narrate assertions
emits the next instruction ("probe here next"), grounded by the librarian and
gated by schema-level citation enforcement. Hallucinated pinouts are the
product-killing failure mode — a confabulated "clip here" on a powered board
causes shorts (docs/DESIGN.md, ARCHITECTURE.md). This is the first
internet-required layer and the first LLM SDK dependency (none allowed earlier).

The decisive design move (ARCHITECTURE.md): **citation enforcement is
architectural, not prompt text.** The validator — not the model's good behavior —
rejects uncited pad claims. Everything gate-worthy in this phase is therefore
testable WITHOUT an LLM, by validating canned outputs. The LLM is mockable at
the boundary; the whole safety envelope is deterministic Python.

## Goals / Non-Goals

**Goals:**
- Structured instruction schema; free text is invalid.
- Citation enforcement, accessibility filter, hazard notes — all validator-side,
  all LLM-free testable.
- Librarian retrieval keyed by board identity, citations as `doc-id#anchor`.
- Config pull: READ-ONLY interrogation, structurally incapable of writes.
- Fault-tree ordering: config-first before probes.

**Non-Goals:**
- No DUT writes of ANY kind, ever (product-premise boundary, CLAUDE.md
  guardrail 4). No exerciser dispatch execution (schema carries `executor` but
  v1 renders to human prose). No vision/photo intake (guardrail 5). No real LLM
  in the test suite — mock it.

## Decisions

### Instruction schema (validator is the contract)

```python
@dataclass(frozen=True)
class Instruction:
    action: str
    target: str
    parameters: dict
    expected_outcome_per_hypothesis: dict[str, str]  # one entry per live hyp
    hazard_notes: str
    executor: str                 # "human" | "exerciser"
    citations: list[str]          # ["doc-id#anchor", ...]
    unknown: bool = False         # explicit "I don't know where" flag
```

Validation (`diagnose/validate.py`, pure functions, no LLM) rejects, with a
field-level error, any instruction that:
1. is missing any required field (e.g. `expected_outcome_per_hypothesis` empty);
2. makes a **pad-level placement claim** without either a citation or
   `unknown=True` (see below);
3. cites a `doc-id#anchor` absent from the current retrieval set (dangling);
4. targets a fine-pitch IC pad on a live board (accessibility filter);
5. has an empty `hazard_notes` on an exercise/placement instruction;
6. has `executor` not in {human, exerciser}.

### What counts as a "pad-level placement claim"

Any instruction whose `action` places a probe/clip on a specific physical point
identified by pad/pin/test-point (e.g. `action="clip"`, `target="TP7"` or
`target="U3 pin 4"`). These REQUIRE grounding: a citation resolving to a
librarian document, or an explicit `unknown=True` (which forces a measure-first
/ "identify by signal" instruction instead of a confident placement). A generic
instruction ("connect to the 3.3 V rail at the labeled JST connector") that
names a documented connector still needs its source cited if it asserts a
specific pad; a pure twiddle ("power-cycle the board") does not. Encode this as
a predicate `is_pad_level_claim(instruction) -> bool` with the rule above, unit
tested against canned instructions.

### Accessibility filter

Prefer connectors, test points, passive-component bodies over IC pins; never
instruct needle-probing fine-pitch (≤ 0.5 mm) IC pads on a live board
(ARCHITECTURE.md, UX-loop finding). Encode as: an instruction is rejected when
`target` is an IC pin AND `parameters` indicate fine pitch (≤
`MIN_PROBE_PITCH_MM = 0.5`) AND the board is powered (`parameters.power_state`
== "on"). Provide a small classifier for "target is an IC pin" (pattern like
`U<n> pin <m>` / `QFN`/`TQFP` package hints in parameters). Named constant
doc-commented.

### Hazard envelope (mirrors the firmware)

Every exercise/placement instruction carries non-empty `hazard_notes`. Push-pull
stimulus onto a possibly-driven line is the one way the tool breaks a board;
Diagnose-emitted exercise instructions targeting output stimulus MUST include
the "believed-undriven + series resistor" framing in `hazard_notes` (validator
checks non-empty; the content discipline is asserted for the exercise path).

### Librarian retrieval

`librarian/` retrieves pinout/connector docs keyed by board identity and exposes
retrieved content as citable units addressable `doc-id#anchor`. For v1 + tests,
retrieval is **fixture-backed and offline**: a local corpus of doc fragments
(JSON/markdown under a fixtures dir) keyed by board id, each fragment carrying a
stable anchor. Interface:
```python
class Librarian(Protocol):
    def retrieve(self, board_id: str) -> Retrieval: ...

@dataclass(frozen=True)
class Retrieval:
    board_id: str
    tier: str                       # "open-book" | "pinout-only" | "dark"
    fragments: dict[str, str]       # "doc-id#anchor" -> content
```
A citation resolves iff its key is in `fragments`. **Documentation tier**
(GLOSSARY.md) calibrates Diagnose: a `dark` board yields no pad-level citations,
so any pad-level placement claim on a dark board MUST carry `unknown=True` or it
fails validation. Live doc retrieval (network) is a thin real backend added
behind the same Protocol; tests use the fixture backend only.

### Config pull — READ-ONLY by construction (allowlist, not blocklist)

`diagnose/config_pull.py` interrogates DUT configuration via documented,
read-only protocol ops. The product-premise boundary (CLAUDE.md guardrail 4) is
enforced structurally: the module builds requests ONLY for an allowlist of
read-only command IDs and has NO code path that constructs a write/set/flash
frame. Any request for a command outside the allowlist raises a
`ProductBoundaryError`.

Reference protocol: Betaflight/iNav **MSP v1** (verified command IDs; MSP
request frame `$M<` = to-FC, `$M>` = from-FC). Read-only allowlist (from
`betaflight/src/main/msp/msp_protocol.h`):

| Command | ID |
|---|---|
| MSP_API_VERSION | 1 |
| MSP_FC_VARIANT | 2 |
| MSP_FC_VERSION | 3 |
| MSP_BOARD_INFO | 4 |
| MSP_BUILD_INFO | 5 |
| MSP_CF_SERIAL_CONFIG | 54 |
| MSP_FEATURE_CONFIG | 36 |
| MSP_RX_CONFIG | 44 |
| MSP_RX_MAP | 64 |
| MSP_OSD_CONFIG | 84 |
| MSP_VTX_CONFIG | 88 |
| MSP_STATUS | 101 |
| MSP_ANALOG | 110 |
| MSP_BATTERY_STATE | 130 |
| MSP_UID | 160 |

Explicitly excluded (writes — the module must never be able to send these):
MSP_SET_* family, e.g. MSP_SET_PID (202), MSP_RESET_CONF (208), and every other
`MSP_SET_*`/`MSP_EEPROM_WRITE`. The allowlist is the guard: the request builder
takes a command from the allowlist enum or raises. MSP v1 request framing:
`$` `M` `<` `<size>` `<cmd>` `<payload…>` `<checksum>` where checksum = XOR of
size, cmd, and payload bytes; read requests have size 0 and empty payload.
**Actual serial I/O is out of scope for the v1 test suite** — config pull is
tested by (a) asserting the built frames for allowlisted reads and (b) asserting
`ProductBoundaryError` on any write-shaped request. No DUT is contacted in tests.

### Fault-tree ordering — config-first

For symptoms with known configuration causes, config-pull suggestions precede
probe instructions (DESIGN.md: the fault tree's first layer is often probe-free).
Encode a small symptom→fault-tree map: each symptom lists ordered branches;
branches with a config-pull path sort before probe branches. The planner emits
the config-pull branch first; only if it fails to explain the symptom does a
probe instruction get generated. Testable with a scripted scenario and a mocked
LLM: assert the FIRST emitted instruction for a config-caused symptom is a
config pull, and that a fully-explained symptom short-circuits with no probe.

### LLM boundary

`diagnose/llm.py` wraps the Anthropic SDK behind a narrow Protocol
(`propose_instruction(context) -> dict`). The default model id is the latest
Claude (see the project's model guidance; do NOT hardcode a deprecated id).
Tests inject a fake that returns canned dicts; the real client is never called
in CI. The SDK (`anthropic`) is the first LLM dependency added to
`pyproject.toml` (pinned per the dev-tooling-gate discipline).

## Risks / Trade-offs

- [A clever LLM emits a confident uncited placement] → the validator, not the
  prompt, rejects it; tested offline against canned malicious outputs.
- [Config pull drifts toward writes] → allowlist architecture makes writes
  unrepresentable; the "no write paths" test inspects the public API and a
  write-shaped request is refused with `ProductBoundaryError`.
- [Dark boards tempt confident pinouts] → tier awareness forces `unknown=True`
  on dark boards; validation enforces it.
- [LLM nondeterminism in CI] → the LLM is mocked; only the deterministic
  envelope is asserted. End-to-end scripted scenarios are rubric-checked, not
  exact-matched.
