# Design: corpus-tooling

## Context

The bench corpus IS the test suite (docs/CORPUS.md): one corpus, three consumers
(eval harness now, few-shot exemplars at inference, training option preserved).
Labeling discipline survives only if it is the path of least resistance — so the
capture CLI must write raw capture + receiver verdict + sidecar in one motion,
making skipping the verdict harder than recording it. This is the parallel track
in docs/ROADMAP.md; it starts early and Phase 1+ consumes it. Real hardware is
NOT required — the capture path is tested against a mocked instrument, and the
schema/layout work is pure data plumbing.

## Goals / Non-Goals

**Goals:**
- Sidecar schema (docs/CORPUS.md) as validated Python; invalid/missing sidecars
  fail loudly; the `referee` field supported from day one.
- One-motion labeled capture CLI.
- Sweep-cell runner producing per-entry axis-tagged sidecars (degradation
  curves, not anecdotes).
- Field-gold holdout enforced by an automated check.

**Non-Goals:**
- No dual-instrument referee *capture* (schema supports it; the capture path is
  analog-hardening-era work). No ML/training (guardrail 2). No threshold tuning
  here — corpus tooling produces the data the detectors tune against elsewhere.

## Decisions

### Sidecar schema — dataclasses, not a new dependency

Model the docs/CORPUS.md sidecar as nested frozen dataclasses with explicit
validation returning field-level errors, rather than adding a `jsonschema`
runtime dependency (CLAUDE.md: keep deps minimal). The exact schema (copy field
names verbatim from CORPUS.md — they are canonical):

```python
@dataclass(frozen=True)
class Instrument:      # model, samplerate_hz, threshold_v, channels: dict[str,str]
@dataclass(frozen=True)
class Driver:          # chip, vdd_v, series_r_ohm
@dataclass(frozen=True)
class Transport:       # cable, length_m, twisted, shielded, termination
@dataclass(frozen=True)
class Receiver:        # part, vdd_v, vih_v
@dataclass(frozen=True)
class Protocol:        # name, nominal: dict  (e.g. {"bitrate_hz": 800000})
@dataclass(frozen=True)
class FaultInjected:   # class_ (JSON key "class"), params: dict   ("none" when clean)
@dataclass(frozen=True)
class ReceiverVerdict: # observed, notes, contemporaneous: bool
@dataclass(frozen=True)
class SweepCell:       # name, axis, value
@dataclass(frozen=True)
class Sidecar:
    id: str
    capture_file: str
    instrument: Instrument
    driver: Driver
    transport: Transport
    receiver: Receiver
    protocol: Protocol
    fault_injected: FaultInjected
    receiver_verdict: ReceiverVerdict
    sweep_cell: SweepCell | None
    referee: dict | None            # reserved; validates when present
```

Note the JSON key collisions with Python keywords: the sidecar JSON uses
`"class"` (inside `fault_injected`) — map it to a field `class_` /
`{"class": ...}` on (de)serialization. `receiver_verdict` is REQUIRED and its
absence is the canonical validation failure to test (the gold label must never
be skipped). `referee` is `None` normally but validates as a populated block
when present (dual-instrument cells, day-one support).

Provide `Sidecar.from_json`/`to_json` and `validate(sidecar) -> list[str]`
(empty = valid). Round-trip against the exact example JSON in CORPUS.md as a
fixture.

### Storage layout helpers

Encode the CORPUS.md layout as path helpers (no magic strings scattered):
```
corpus/
  cells/<cell-name>/
    cell.json            # sweep-cell definition: axis, fixture, fix arms
    entry-*.sr           # raw captures
    entry-*.json         # sidecars
  field-gold/            # held out; never tuned against
  synthetic/             # generated fixtures used by unit tests
```
`corpus/synthetic/` is the SAME source of truth as `tests/synth.py` (Phase 1
generators serialize their captures + ground truth here — single source; do not
fork the generators). Provide `cell_dir(name)`, `entry_paths(cell, id)`,
`field_gold_dir()`.

### One-motion capture CLI

`corpus/capture_cli.py` (also a console entry point). One invocation:
1. runs the instrument via the Phase 0 `capture/sigrokcli.py` wrapper (injected
   for tests — a mocked instrument returns a synthetic `.sr`);
2. prompts for the contemporaneous receiver verdict (stdin; in tests, an
   injected input provider) — the prompt is REQUIRED and the CLI refuses to
   write an entry without a verdict (labeling discipline: skipping is harder than
   recording);
3. writes `entry-<id>.sr` and `entry-<id>.json` into the correct cell dir,
   cross-referenced by `id`, sidecar validated before write.

Tested by driving the CLI with a mocked instrument + injected verdict and
asserting both files exist, cross-reference, and validate.

### Sweep-cell runner

`corpus/sweep.py` reads a `cell.json` (`{name, axis, fixture, fix_arms: [...],
values: [...]}`) and sequences one entry per axis value, stamping each entry's
`sweep_cell.axis` and `.value`. Downstream evals extract degradation curves by
grouping entries on `(cell, axis)`. Tested: a sweep at values [1,5,10] produces
three entries each carrying `sweep_cell.axis="length_m"` and its value.

### Field-gold holdout enforcement

An automated guard (`tests/corpus/test_field_gold_holdout.py`): scan `tests/`
and `src/` for references to the `field-gold/` path outside an explicit
allowlist (the loader and this guard itself). If any threshold-tuning or eval
fixture references `field-gold/`, the build fails. This encodes "field gold is
the exam, not the homework" as CI, not etiquette. Implement the scan with a
simple recursive text search over `.py` files for the literal `field-gold`,
allowlisting `corpus/paths.py` (the loader) and the guard test.

## Risks / Trade-offs

- [Verdict prompt is skippable] → the CLI refuses to write without a verdict;
  the "missing receiver_verdict rejected" test locks this in.
- [Schema drift from CORPUS.md] → the round-trip fixture is the exact CORPUS.md
  example; a schema change must update both, surfacing drift.
- [Holdout guard is coarse] → a literal-path scan is intentionally simple and
  conservative; false positives are fixed by using the loader, which is the
  desired behavior anyway.
