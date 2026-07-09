# Tasks: phase-4-narrate

> Prerequisite: `dev-tooling-gate` applied. Consumes Phase 2 `DecodedEvent`s,
> Phase 3 `SmokeFinding`s, and capture/corpus metadata. Deterministic — NO LLM
> here. TDD from the spec scenario. End every group with `make check`.

## 1. Assertion + Evidence schema

- [x] 1.1 Write failing tests in `tests/narrate/test_assertion.py`: `Assertion` (kind, text, evidence, confidence∈[0,1]) and `Evidence` (event_indices, sample_ranges, finding_refs) are frozen dataclasses comparing by value; `Assertion`↔JSON round-trips with evidence intact
- [x] 1.2 Implement `src/slidko/narrate/model.py` with `Assertion` and `Evidence` per design.md + `to_json`/`from_json`; tests green

## 2. I²C address book

- [x] 2.1 Write failing tests in `tests/narrate/test_address_book.py`: lookup of 0x68 returns a NON-empty candidate list including an IMU part; an unknown address returns an empty list (not an error); lookups never return a single forced identification
- [x] 2.2 Implement `src/slidko/narrate/address_book.py` as committed data (dict addr→list of `{part, kind, note}`) seeded from the table in design.md, plus `lookup(addr) -> list[dict]`; tests green
- [x] 2.3 Add a test asserting the book is data-shaped (a dict/JSON, no branching logic) so future parts are added by editing data

## 3. Transaction summarization

- [x] 3.1 Write failing test: a synthetic I²C event stream of N transactions to 0x68 with M NAKs produces a `transaction.summary` assertion whose text states N and M with the address and candidate part names, and whose evidence references the contributing event indices
- [x] 3.2 Implement `summarize_transactions(events) -> list[Assertion]`; tests green

## 4. Cross-channel coincidence

- [x] 4.1 Write failing test: a NAK event on one channel and a `SmokeFinding` on another within the coincidence window yield a single `coincidence` assertion naming both channels and the time delta in real units; events outside the window do NOT coincide
- [x] 4.2 Implement `detect_coincidences(events, findings, samplerate_hz)` with `COINCIDENCE_WINDOW_SAMPLES` derived from a named time window; tests green

## 5. Receiver-rule caveat (the killer case)

- [x] 5.1 Write the killer-case failing test: a capture that decodes cleanly at 1.4 V instrument threshold, with sidecar `receiver.vih_v = 3.5`, `receiver_verdict.observed = "flicker"` (5 V WS2812), produces a `receiver_rule.caveat` assertion naming BOTH thresholds AND the assertion set contains NO "bus healthy" claim
- [x] 5.2 Write the complementary test: when instrument threshold ≈ receiver V_IH (within `RECEIVER_THRESHOLD_MARGIN_V`) and verdict is clean, NO caveat is emitted
- [x] 5.3 Write the bare-capture test: with no receiver metadata, Narrate emits no receiver health claim and no fabricated verdict (may state the instrument-threshold limitation)
- [x] 5.4 Implement `receiver_rule_caveat(capture, sidecar, decoded_ok) -> list[Assertion]` and the suppression of health claims per design.md; tests green

## 6. Narrate orchestrator

- [x] 6.1 Implement `narrate(capture, events, findings, sidecar=None) -> list[Assertion]` composing groups 3–5; ensure every emitted assertion carries non-empty evidence
- [x] 6.2 Write the traceability test: serialize the assertion set, reload, and confirm each assertion's evidence references still index valid events / sample ranges in the source capture

## 7. Golden-file evaluation

- [x] 7.1 Write a golden-file test harness in `tests/narrate/test_golden.py`: load `tests/narrate/golden/<entry>.json`, run `narrate` on the corresponding synthetic entry, compare assertion sets ORDER-INSENSITIVELY (missing/extra fail; reorder passes)
- [x] 7.2 Create at least three committed goldens: (a) healthy I²C IMU bus, (b) I²C bus with a NAK coincident with a smoke finding, (c) the WS2812 receiver-rule killer case; generate them deliberately and hand-verify their contents
- [x] 7.3 Add a negative test: a golden with an extra expected assertion fails; a reordered golden passes — proving the comparator is order-insensitive but not lax

## 8. Wrap-up

- [x] 8.1 `make check` green; the killer-case test (5.1) and golden tests pass
- [x] 8.2 Commit naming the task groups
