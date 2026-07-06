# Fixtures

Two kinds of `.sr` live under `tests/fixtures/`, and they are versioned
differently on purpose:

- **Real hardware captures** (committed). Manually captured evidence of actual
  boards/faults — irreplaceable, so they go in git. Place them directly in
  `tests/fixtures/` (or, for corpus entries, under `corpus/`). Never gitignored.
- **Regenerable fixtures** (not committed). Deterministic tool output that can be
  recreated on demand lives under `tests/fixtures/generated/`, which is
  gitignored.

## `generated/sigrok-demo-capture.sr`

Regenerated on demand by the `demo_capture` pytest fixture (`tests/conftest.py`,
built in phase-0), which runs:

```
sigrok-cli --driver demo --config samplerate=24000000 --time 10 -O srzip -o tests/fixtures/generated/sigrok-demo-capture.sr
```

and skips the real-file tests cleanly when sigrok-cli is not installed (e.g. in
CI), so the suite never hard-depends on the tool. You can also run that command
by hand to inspect the file.

Confirmed contents (sigrok-cli 0.7.2 / libsigrok 0.5.2): 8 logic probes
(D0-D7), 5 analog channels (A0-A4), `unitsize=1`, multi-chunk (`logic-1-1`,
`logic-1-2`, ...). Chunk files are interleaved with `analog-1-<ch>-<n>`
entries in the same zip — the reader MUST select by `logic-1-` prefix and
ignore `analog-*` chunks; do not assume every binary chunk is logic data.

This is what resolved the original "MODERATE confidence" flag for chunk naming
and unitsize in `openspec/changes/phase-0-capture-ingest/design.md` — both
confirmed against a real file rather than assumed.
