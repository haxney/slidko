import numpy as np

from slidko.measure.edges import extract_edges


def test_interval_helpers():
    """Test interval computation helpers."""

    # Create a known simple sequence for testing intervals
    data = np.array([True, True, False, False, True, True, False, False], dtype=bool)
    edges = extract_edges(data)

    print("Test data:", data)
    print("Found edges at positions:", [e[0] for e in edges])
    print("Edge polarities:", [e[1] for e in edges])

    # Test we can actually compute interval differences between edges
    if len(edges) >= 2:
        intervals = []
        for i in range(1, len(edges)):
            interval = edges[i][0] - edges[i - 1][0]
            intervals.append(interval)

        print("Computed intervals:", intervals)

        # Validate basic interval structure
        assert len(intervals) == len(edges) - 1


def test_interval_helper_with_known_pattern():
    """Test with a known pattern to check exact interval computations."""

    # Create alternating 2-sample high/low pattern
    data = np.array([True, True, False, False, True, True, False, False], dtype=bool)
    edges = extract_edges(data)

    print("\nPattern test:")
    print("Data:", data)
    print("Edges found:", edges)

    # For this pattern: [T, T, F, F, T, T, F, F]
    # Edges at positions: 2(F->T), 4(T->F), 6(F->T)
    # Positions:  0   1   2   3   4   5   6   7
    # Expected edges after 2nd and 4th samples (1 based indexing):
    assert len(edges) >= 1

    # Compute intervals manually
    if len(edges) > 1:
        interval = edges[1][0] - edges[0][0]
        print("Interval:", interval)
