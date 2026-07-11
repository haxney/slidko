"""Field-gold holdout enforcement.

`corpus/field-gold/` is held out and never tuned against (docs/CORPUS.md:
"the exam, not the homework"). This guard scans `.py` files under `src/`
and `tests/` for the literal held-out directory name outside an explicit
allowlist, so a tuning/eval fixture that references it fails the build
instead of quietly corrupting the holdout (design.md "Field-gold holdout
enforcement").
"""

from pathlib import Path

HELD_OUT_DIR_NAME = "field-gold"

# Files permitted to reference the held-out directory name: the loader
# (corpus/paths.py) and its own test (which asserts the loader's literal
# return value, not a tuning/eval fixture), this guard module itself (its
# own docstring/constant above necessarily contain the literal), and the
# guard's test.
ALLOWLIST = frozenset({
    "src/slidko/corpus/paths.py",
    "tests/corpus/test_paths.py",
    "src/slidko/corpus/field_gold_holdout.py",
    "tests/corpus/test_field_gold_holdout.py",
})


def scan_for_field_gold_references(root: Path) -> list[str]:
    """Scan `.py` files under `root/src` and `root/tests` for the literal
    held-out directory name outside ALLOWLIST.

    Returns the offending files' paths, relative to `root` (posix-style),
    sorted. Empty means clean.
    """
    forbidden: list[str] = []
    for source_dir in ("src", "tests"):
        base = root / source_dir
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            rel = path.relative_to(root).as_posix()
            if rel in ALLOWLIST:
                continue
            if HELD_OUT_DIR_NAME in path.read_text(encoding="utf-8"):
                forbidden.append(rel)
    return sorted(forbidden)


def check_field_gold_references(root: Path) -> bool:
    """True if no unauthorized references to the held-out directory exist."""
    return not scan_for_field_gold_references(root)
