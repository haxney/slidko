from slidko.corpus.paths import cell_dir, entry_paths, field_gold_dir


def test_cell_dir():
    """Test that cell_dir returns the CORPUS.md layout path"""
    result = cell_dir("test-cell")
    expected = "corpus/cells/test-cell"
    assert result == expected


def test_entry_paths():
    """Test that entry_paths returns the .sr + .json file paths for given cell and id"""
    cell = "test-cell"
    entry_id = "entry-001"

    sr_path, json_path = entry_paths(cell, entry_id)

    assert sr_path == "corpus/cells/test-cell/entry-001.sr"
    assert json_path == "corpus/cells/test-cell/entry-001.json"


def test_field_gold_dir():
    """Test that field_gold_dir returns the CORPUS.md layout path"""
    result = field_gold_dir()
    expected = "corpus/field-gold"
    assert result == expected
