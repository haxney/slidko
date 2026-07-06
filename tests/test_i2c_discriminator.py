"""Tests for I²C discriminator functions."""

import numpy as np
import pytest

from slidko.measure.i2c import (
    analyze_i2c_periodicity,
    assign_i2c_roles,
    detect_i2c_protocol,
    detect_i2c_start_stop,
    get_i2c_baud_table,
    i2c_discriminator,
)


def test_basic_i2c_functions():
    """Test basic I²C functions."""

    # Test start/stop detection with minimal edges
    edges = [(10, True), (20, False), (30, True)]
    has_start, has_stop = detect_i2c_start_stop(edges)
    assert isinstance(has_start, bool)
    assert isinstance(has_stop, bool)

    # Test role assignment
    roles = assign_i2c_roles(edges, edges)
    assert "scl" in roles
    assert "sda" in roles

    # Test periodicity analysis
    period_metrics = analyze_i2c_periodicity(edges, edges)
    assert isinstance(period_metrics, dict)

    # Test complete protocol detection
    scl_data = np.array([True, True, False, False], dtype=bool)
    sda_data = np.array([True, False, False, True], dtype=bool)
    result = detect_i2c_protocol(scl_data, sda_data)
    assert "protocol" in result
    assert "confidence" in result

    # Test discriminator function
    discriminator_result = i2c_discriminator(scl_data, sda_data)
    assert isinstance(discriminator_result, dict)

    # Test baud table
    bauds = get_i2c_baud_table()
    assert isinstance(bauds, list)
    assert len(bauds) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
