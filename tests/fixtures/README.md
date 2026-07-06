# Fixtures

`sigrok-demo-capture.sr` — a real sigrok session file, generated locally with
no hardware attached:

```
sigrok-cli --driver demo --config samplerate=24000000 --time 10 -O srzip -o sigrok-demo-capture.sr
```

Confirmed contents (sigrok-cli 0.7.2 / libsigrok 0.5.2): 8 logic probes
(D0-D7), 5 analog channels (A0-A4), `unitsize=1`, multi-chunk (`logic-1-1`,
`logic-1-2`, ...). Chunk files are interleaved with `analog-1-<ch>-<n>`
entries in the same zip — the reader MUST select by `logic-1-` prefix and
ignore `analog-*` chunks; do not assume every binary chunk is logic data.

This resolves the "MODERATE confidence" flag in
openspec/changes/phase-0-capture-ingest/design.md for chunk naming and
unitsize — both now confirmed against a real file rather than assumed.
