# CLAUDE.md — Slidko

Slidko is an AI-assisted hardware integration debugging tool. It transduces raw
logic-analyzer captures into compact, LLM-legible symbolic descriptions, then
closes a diagnostic loop: measure → narrate → diagnose → "probe here next."
The name derives from the Ukrainian слід ("trace/track") — a pun on PCB trace
and captured waveform.

**Read `docs/GLOSSARY.md` before discussing or naming anything in the design.**
The vocabulary is canonical; do not invent synonyms for existing terms.

## Language ruling (final — do not relitigate)

- **Python 3.11+** for the entire v1 laptop pipeline. Rationale: v1 is batch
  analysis of recorded captures (not real-time streaming); the sigrok decoder
  ecosystem is Python-adjacent; numpy/scipy cover all edge math; LLM SDKs are
  Python-first.
- **C via pico-sdk (CMake)** for exerciser firmware. Open toolchain only:
  headless Linux builds, CI-friendly, no account-walled or Windows-only tools.
- **Rust** is the designated language for the *future* pod streaming daemon and
  performance-critical capture paths. There is **zero Rust in v1**. If a hot
  path appears, profile first; a Rust insertion is earned by measurement, not
  anticipation.

## Directory layout

```
slidko/
  CLAUDE.md
  docs/            design record (read the one relevant to your task)
  src/slidko/      Python package: capture/, measure/, decode/, narrate/,
                   diagnose/, librarian/, corpus/
  firmware/        exerciser (pico-sdk C, CMake) — separate build tree
  corpus/          bench corpus: .sr captures + JSON sidecars (see docs/CORPUS.md)
  tests/           pytest; synthetic captures first, real .sr fixtures second
```

## Engineering discipline

- **The bench corpus IS the test suite.** Every Measure/Decode/smoke-detector
  behavior is asserted against corpus entries or synthetic captures. TDD-style:
  write the eval before the discriminator.
- **Tests never require hardware.** Synthetic edge-stream generators (in-memory
  UART/I²C/SPI/WS2812 captures with known ground truth) come first; real .sr
  files are fixtures, not dependencies.
- **Fidelity gate applies to our own data:** raw samples always; never persist
  screenshots or decoded output as primary artifacts.
- **Deterministic DSP first.** No ML training on the v1 critical path. If a
  task seems to need a model, check `docs/DESIGN.md` — it almost certainly has
  a closed-form solution (autocorrelation, interval histograms, edge math).
- Explicit confidence levels in doc comments where a claim is empirical and
  untested.

## Guardrails — do NOT build in v1

1. **No pod code.** The bridge pod (RP2350 PIO → FT232H) is deferred, gated on
   a hardware throughput benchmark. See `docs/ARCHITECTURE.md § Deferred`.
2. **No ML training pipelines.** Corpus labeling discipline preserves the
   option; building it now is scope creep.
3. **No oscilloscope integration.** Scope escalation is a human-relayed
   instruction in v1 ("smoke → scope"). SCPI integration is future work.
4. **No DUT write/control capability, ever.** Config pull is READ-ONLY
   interrogation over documented protocols. No flashing, no MSP writes, no
   commanding user firmware. This is a product-premise boundary, not a
   milestone.
5. **No vision/photo pipeline yet.** Board-photo intake is a later phase.
6. **No new hardware dependencies.** v1 capture is an fx2lafw-class 24 MHz
   8-channel DLA via sigrok; the exerciser is an RP2350 (RP2040 acceptable for
   development — parameterize all timing constants by system clock so the
   133→150 MHz migration is a config change).

## Pointers

| Task | Read first |
|---|---|
| Any design discussion | `docs/GLOSSARY.md`, `docs/DESIGN.md` |
| Pipeline stages, dataflow, sigrok posture | `docs/ARCHITECTURE.md` |
| What to build next, acceptance criteria | `docs/ROADMAP.md`, `docs/TASKS.md` |
| Capture storage, labels, metadata schema | `docs/CORPUS.md` |
| Firmware | `docs/EXERCISER.md` |
