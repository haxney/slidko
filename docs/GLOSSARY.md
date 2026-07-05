# Glossary — canonical vocabulary

Descriptive names are canonical. Letter/number shorthands were tried and
failed (zero error-correction when misremembered). Use these terms exactly;
do not coin synonyms.

## Data principles

- **Fidelity gate** — hard pass/fail: did the encoding preserve the mutual
  information between raw signal and answer? Post-processing can only destroy
  mutual information (data-processing inequality). A screenshot of a scope
  screen fails the fidelity gate.
- **Legibility** — are the preserved features presented as tokens an LLM
  reasons over fluently? Passing the fidelity gate ≠ legible (50,000 raw
  floats pass the gate and are illegible).
- **Logical depth** (Bennett, 1988) — how much serial computation/reasoning is
  needed to derive the answer. A property of the task. Its practical
  provision: **thinking room** (chain-of-thought space plus the loop).
- Ordering slogan: **fidelity, then legibility, then depth** — preserve it,
  make it readable, give it room.

## Pipeline (five verbs, execution order)

- **Capture** — raw acquisition. The fidelity gate is enforced in hardware
  here; undersampling or a wrong threshold is unrecoverable downstream.
- **Measure** — deterministic DSP feature extraction: what the signal
  physically is (levels, edges, periods, roles). No ML.
- **Decode** — protocol hypothesis ranking + decoder invocation with
  parameters that Measure inferred.
- **Narrate** — decoded events → diagnostically salient English assertions.
  Named for its output (sentences). The highest-leverage layer.
- **Diagnose** — LLM abductive reasoning + next-instruction generation, over
  Narrate assertions only; never raw sample crunching.
- **The librarian** — board ID → retrieved pinout documentation →
  citation-grounded pad claims. (Deliberately not "grounding layer": in an
  electronics product, "grounding" collides with the electrical meaning.)

## Difficulty tiers

- **Edge math** — discrete algorithmics on edge timestamps. Weeks-scale;
  requires no DSP background.
- **Analog hardening** — robustness engineering for marginal real-world
  captures. Months-scale; ships incrementally.
- **PhD territory** — expert analog fingerprinting, eye diagrams, blind
  protocol reverse-engineering. Deferred, possibly forever.

## Documentation tiers (of target boards)

- **Open-book boards** — schematics published.
- **Pinout-only boards** — pinout diagram but no schematic (SpeedyBee-class
  flight controllers are the type specimen).
- **Dark boards** — undocumented: no-name imports, field-improvised stacks.
  The hardest tier; "measure, don't ask" is the only ground truth there.

## Loop & behavior

- **The poke loop** — symptom → librarian → placement instruction → measure →
  narrate → diagnose → next instruction. Anchored to the user's real question:
  "where should I start poking?"
- **Watch** — passive capture, no stimulus.
- **Twiddle** — human-executed, Slidko-instructed action on the system under
  test (press the button, power-cycle, reseat the connector, move a probe).
- **Exercise** — Slidko-executed stimulus via **the exerciser** (Slidko's own
  known-firmware harness device). The executor is always Slidko's hardware,
  never the DUT's.
- **Config pull** — read-only DUT interrogation over documented standard
  protocols (e.g. Betaflight MSP query, CLI dump). Automates the probe-free
  first layer of the fault tree. READ-ONLY is the boundary; writes are
  permanently excluded.
- **The smoke detector** — edge-math anomaly checks (edge chatter, runt
  pulses, timing violations, protocol incoherence) that DETECT but do not
  diagnose digital-abstraction contract breaches. Escalation move:
  **smoke → scope**.
- **The receiver rule** — every signal is judged at the RECEIVER's threshold,
  never the instrument's. The cheap DLA's characteristic failure mode is a
  receiver-rule violation.
- **Logic-first** — v1 sequencing: logic analyzer before oscilloscope; edge
  math before analog hardening.

## Corpus

- **The bench corpus** — labeled capture set generated on controlled bench
  fixtures.
- **Receiver verdicts** — the gold labels: per-entry record of what the far
  end actually did (servo glitched / device NAKed / strip flickered), observed
  contemporaneously with capture. Enforces the receiver rule at dataset level.
- **Field gold** — real field captures. Held out; never tuned against.
- **Sweep cells** — parameterized fault generators (cable-length sweeps,
  fix-arm variants) producing degradation curves, not anecdotes.

## Hardware

- **The exerciser** — RP2350-class harness device running project-authored
  firmware; generates known bus traffic, scans, and stimulus on command.
- **The pod** — hypothetical future single device in which capture and
  exercise share one silicon and one clock domain, streaming over USB
  High-Speed. Defining property: shared timebase makes stimulus-to-response
  correlation cycle-accurate by construction. DEFERRED; not a v1 component.
  See `ARCHITECTURE.md § Deferred`.
