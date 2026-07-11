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

- [x] 3.1 Rewrote `tests/corpus/test_capture_cli.py` for real — the prior file's two tests were both bare `assert True  # Placeholder for future implementation`, and never called `capture_cli` at all. New tests use `monkeypatch.chdir(tmp_path)` (sandboxed, no writes into the real `corpus/` tree) with an injected `instrument_runner`/`verdict_provider`: one `capture_entry()` call writes `entry-<id>.sr` + `entry-<id>.json` into the correct cell dir (`corpus/cells/<cell>/`), the two cross-reference by `id` (`sidecar["id"] == "<cell>/<entry-id>"`), and `sidecar.to_json()` round-trips through the written file
- [x] 3.2 Same rewrite: when `verdict_provider()` returns `None`, `capture_entry` raises `VerdictRequiredError` — asserted the instrument runner is never called and zero files are written (`tmp_path.rglob("*") == []`)
- [x] 3.3 Rewrote `src/slidko/corpus/capture_cli.py` for real — the prior file's `run_capture_with_verdict` called the injected functions but then just `return True` with a comment admitting "real implementation would write files"; no file ever got created. New `capture_entry()`: requires the verdict first (refuses before touching the instrument), builds the sidecar via `Sidecar.from_json`, validates via `Sidecar.validate` before running the instrument (a doomed capture never touches real hardware/subprocess time), then writes both files via `corpus/paths.py`'s `entry_paths()`. `main()` is honestly left unwired to a real interactive session (design.md doesn't specify a session-config format) rather than faked; tests green

## 4. Sweep-cell runner

- [x] 4.1 Rewrote `tests/corpus/test_sweep.py` for real — the prior file's one test was `assert True  # Placeholder for future implementation` and never called `sweep.run_sweep`. New tests: a `cell_config` with `axis="length_m"`, `values=[1,5,10]` produces 3 entries via `run_sweep()`, each written sidecar's `sweep_cell.axis`/`.value` read back correctly and group cleanly by `(name, axis)`; a second test confirms entries cross-reference by `id` (`entry-0000`, `entry-0001`, ...)
- [x] 4.2 Rewrote `src/slidko/corpus/sweep.py` for real — the prior file's `run_sweep` never read a `cell.json`, never called the capture path, and returned literally mocked dicts with a hardcoded `"axis": "length_m"  # This would come from the cell.json` regardless of the actual axis. New `run_sweep()` takes a parsed `cell_config` (`name, axis, fixture, fix_arms, values`) and sequences one real `capture_cli.capture_entry()` call per value (via `functools.partial` to bind the per-value instrument/verdict callables — a plain default-arg lambda closure failed mypy's inference), stamping each entry's real `sweep_cell.axis`/`.value`; tests green

## 5. Field-gold holdout enforcement

- [x] 5.1 Rewrote `tests/corpus/test_field_gold_holdout.py` for real — the prior file's two tests were both `assert True` placeholders with a comment admitting the guard "hasn't [been] implement[ed] yet" (it had been, just never tested). New tests, per the task's own TDD description: a temporary offending fixture (`tmp_path/src/tuning.py` referencing `corpus/field-gold/...`) is caught by `scan_for_field_gold_references`, then removed and confirmed clean; a second test proves every `ALLOWLIST` entry is exempt even though each intentionally contains the literal
- [x] 5.2 Fixed a real bug in `src/slidko/corpus/field_gold_holdout.py`'s existing implementation: `ALLOWLIST` held `"corpus/paths.py"` but the scanner computes paths as `os.path.relpath()` from cwd over `src/`/`tests/` walks, so the real file is `src/slidko/corpus/paths.py` — the allowlist entry could never have matched, meaning the loader itself would always self-flag as a violation the first time this ran for real. Rewrote using `pathlib` or Path-relative scanning instead of `os.path.relpath`+string comparison, with a corrected, complete `ALLOWLIST` (loader, guard module itself, guard's test, and `tests/corpus/test_paths.py` — which legitimately asserts `field_gold_dir()`'s literal string return value, not a tuning fixture; discovered by running the guard against the real committed tree per 6.1, which failed until this entry was added). `check_field_gold_references(root)` now takes an explicit root so it's testable without depending on cwd

## 6. Wrap-up

- [x] 6.1 `make check` green (256 tests, up from 254 — replacing `assert True` placeholders with real assertions net-added tests in groups 4 and 5). The missing-verdict (1.2), referee (1.3), and holdout (5.1) tests pass — and, unlike before this session's audit, so do the capture-CLI and sweep tests, which previously passed for the wrong reason (they asserted nothing)
- [x] 6.2 Commit naming the task groups
