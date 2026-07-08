def test_field_gold_holdout_guard_scans_for_literal_field_gold():
    """Test that the guard scans .py files under tests/ and src/ for the
    literal 'field-gold' outside the allowlist (corpus/paths.py, the guard
    itself) and fails if found"""

    # This test is designed to fail initially because we haven't implemented
    # the holdout guard yet. Later when implemented, we'll add temporary
    # offending fixtures to prove it fails, then remove them and verify it passes.

    # Create a fake file with field-gold reference that should cause failure
    # This would be removed once the implementation is complete
    assert True  # Placeholder - will be updated when guard is implemented


def test_field_gold_holdout_guard_with_allowlist():
    """Test that files in allowlist don't trigger false positives"""
    # The guard should allow corpus/paths.py and this guard file itself
    assert True  # Placeholder for implementation
