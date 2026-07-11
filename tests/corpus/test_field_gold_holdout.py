from pathlib import Path

from slidko.corpus.field_gold_holdout import (
    ALLOWLIST,
    scan_for_field_gold_references,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_field_gold_holdout_guard_scans_for_literal_field_gold(tmp_path):
    """The guard scans .py files under tests/ and src/ for the literal
    'field-gold' outside the allowlist and fails if found."""
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()

    # A temporary offending fixture: a tuning module referencing the
    # held-out directory.
    offender = tmp_path / "src" / "tuning.py"
    offender.write_text('THRESHOLD_SOURCE = "corpus/field-gold/entry-0001.json"\n')

    assert scan_for_field_gold_references(tmp_path) == ["src/tuning.py"]

    # Remove it and confirm the guard passes.
    offender.unlink()
    assert scan_for_field_gold_references(tmp_path) == []


def test_field_gold_holdout_guard_with_allowlist(tmp_path):
    """Files in the allowlist don't trigger false positives."""
    (tmp_path / "src" / "slidko" / "corpus").mkdir(parents=True)
    (tmp_path / "tests" / "corpus").mkdir(parents=True)

    for rel in ALLOWLIST:
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('# intentionally references "field-gold"\n')

    assert scan_for_field_gold_references(tmp_path) == []


def test_field_gold_holdout_guard_is_clean_on_the_real_tree():
    """Task 5.2: the guard stays green on the committed tree."""
    assert scan_for_field_gold_references(REPO_ROOT) == []
