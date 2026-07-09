# Tasks: corpus-tooling

> Prerequisite: `dev-tooling-gate` applied. Parallel track — consumes Phase 0
> `capture/sigrokcli.py` (mocked in tests). No hardware. TDD from the spec
> scenario. End every group with `make check`.

## 1. Sidecar schema

- [x] 1.1 Write failing tests in `tests/corpus/test_sidecar.py`: round-trip the EXACT example JSON from docs/CORPUS.md (copy it verbatim as a fixture) through `Sidecar.from_json`→`to_json` with byte-for-byte-equivalent fields, including the `"class"` key inside `fault_injected` mapping to `class_`
- [x] 1.2 Write failing test: a sidecar dict lacking `receiver_verdict` fails `validate` with an error naming the missing field
- [x] 1.3 Write failing test: a sidecar with a populated `referee` block validates (day-one support); a `referee` of `null` also validates
- [x] 1.4 Implement `src/slidko/corpus/sidecar.py` with the nested frozen dataclasses, `from_json`/`to_json` (handling the `class` key), and `validate(sidecar) -> list[str]` per design.md; tests green

## 2. Storage-layout helpers

- [x] 2.1 Write failing tests in `tests/corpus/test_paths.py`: `cell_dir(name)`, `entry_paths(cell, id)` (returns the `.sr` + `.json` pair), and `field_gold_dir()` return the CORPUS.md layout paths
- [x] 2.2 Implement `src/slidko/corpus/paths.py`; tests green

## 3. One-motion capture CLI

- [x] 3.1 Write failing tests in `tests/corpus/test_capture_cli.py` with a MOCKED instrument (injected `sigrokcli` boundary returning a synthetic `.sr`) and an injected verdict provider: one CLI invocation writes `entry-<id>.sr` + `entry-<id>.json` into the correct cell dir, the two cross-reference by `id`, and the sidecar validates
- [x] 3.2 Write failing test: when NO receiver verdict is supplied, the CLI refuses to write an entry (labeling discipline) and exits non-zero without creating files
- [x] 3.3 Implement `src/slidko/corpus/capture_cli.py` (capture → require verdict → validate → write both files) with the instrument and input providers injected; tests green

## 4. Sweep-cell runner

- [x] 4.1 Write failing tests in `tests/corpus/test_sweep.py`: a `cell.json` with `axis="length_m"`, `values=[1,5,10]` produces three entries, each sidecar carrying `sweep_cell.axis="length_m"` and its own value; entries group cleanly by `(cell, axis)`
- [x] 4.2 Implement `src/slidko/corpus/sweep.py` reading `cell.json` (`name, axis, fixture, fix_arms, values`) and sequencing one entry per value via the capture path (mocked instrument in tests); tests green

## 5. Field-gold holdout enforcement

- [x] 5.1 Write failing test in `tests/corpus/test_field_gold_holdout.py`: the guard scans `.py` files under `tests/` and `src/` for the literal `field-gold` outside the allowlist (`corpus/paths.py`, the guard itself) and fails if found; add a temporary offending fixture to prove it fails, then remove it and confirm it passes
- [x] 5.2 Implement the guard (recursive text scan with the allowlist) as the test body; keep it green on the committed tree

## 6. Wrap-up

- [ ] 6.1 `make check` green; the missing-verdict (1.2), referee (1.3), and holdout (5.1) tests pass
- [ ] 6.2 Commit naming the task groups
