# Proposal: phase-5-diagnose-loop

## Why

Diagnose closes the loop: LLM abductive reasoning over Narrate assertions emits the next instruction ("probe here next"), grounded by the librarian and gated by schema-level citation enforcement — hallucinated pinouts are the product-killing failure mode. This is docs/ROADMAP.md Phase 5, the first internet-required layer (everything below stays offline-capable).

Status note: design.md and tasks.md deferred until pickup; proposal + specs define the contract now. This phase adds the first LLM SDK dependency (none allowed earlier).

## What Changes

- Add `diagnose/`: LLM integration emitting the structured instruction schema (action, target, parameters, expected_outcome_per_hypothesis, hazard_notes, executor, citations) with schema validation.
- Add citation enforcement as architecture: pad-level placement claims REQUIRE a librarian citation or an explicit `"unknown": true` flag; validation rejects uncited pad claims (unit-testable against canned outputs, no LLM needed).
- Add `librarian/`: board ID -> retrieved pinout documentation -> citation-grounded pad claims.
- Add config pull: READ-ONLY DUT interrogation over documented protocols (e.g., Betaflight MSP query) as the probe-free first layer of the fault tree.
- Add the conversational poke loop: symptom -> librarian -> instruction -> measure -> narrate -> diagnose -> next instruction.

## Capabilities

### New Capabilities

- `diagnosis`: schema-validated instruction generation with citation enforcement, hazard notes, and the accessibility filter.
- `librarian`: document retrieval keyed by board identity; citations addressable as doc-id#anchor.
- `config-pull`: read-only configuration interrogation over documented protocols, ordered before probe instructions in the fault tree.

### Modified Capabilities

(none)

## Impact

- New modules under `src/slidko/diagnose/` and `src/slidko/librarian/`; first LLM SDK dependency enters `pyproject.toml`.
- Product-premise boundary is enforced here in code review and spec: config pull is READ-ONLY; no DUT writes of any kind, ever.
- Schema validation and fault-tree ordering are testable without an LLM (canned outputs); end-to-end scripted scenarios are rubric-evaluated.
