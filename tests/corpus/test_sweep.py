def test_sweep_cell_functionality():
    """Test that a cell.json with axis="length_m", values=[1,5,10] produces
    three entries, each sidecar carrying sweep_cell.axis="length_m" and its
    own value; entries group cleanly by (cell, axis)"""

    # This is a placeholder test - implementation would involve:
    # 1. Reading a cell.json file
    # 2. Sequencing entries per value via capture path
    # 3. Each entry's sidecar having sweep_cell.axis="length_m" and correct value

    assert True  # Placeholder for future implementation
