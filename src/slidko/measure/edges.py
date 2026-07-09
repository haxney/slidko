import numpy as np


def extract_edges(channel_data: np.ndarray) -> list[tuple[int, bool]]:
    """
    Extract rising and falling edge timestamps from a channel's bit array.

    Args:
        channel_data: Boolean array representing logic signal

    Returns:
        List of (sample_index, polarity) tuples. Polarity is True for rising
        edges and False for falling edges.
    """
    if len(channel_data) < 2:
        return []

    # Get difference between consecutive samples
    diff = np.diff(channel_data.astype(int))

    # Find indices where transitions occur (non-zero differences)
    edge_indices = np.flatnonzero(diff)

    # Convert to list of (sample_index, polarity) tuples
    edges: list[tuple[int, bool]] = []
    for idx in edge_indices:
        # idx points to the position before the transition (in original array)
        # The actual edge occurs at idx + 1
        if diff[idx] > 0:
            # Rising edge: 0 -> 1
            edges.append((int(idx) + 1, True))
        elif diff[idx] < 0:
            # Falling edge: 1 -> 0
            edges.append((int(idx) + 1, False))

    return edges


def inter_edge_intervals(edges: list[tuple[int, bool]]) -> np.ndarray:
    """Sample-index deltas between every consecutive pair of edges."""
    if len(edges) < 2:
        return np.array([], dtype=np.int64)
    indices = np.array([idx for idx, _ in edges], dtype=np.int64)
    return np.diff(indices)


def same_polarity_intervals(edges: list[tuple[int, bool]]) -> np.ndarray:
    """Sample-index deltas between consecutive edges of the same polarity
    (e.g. rising-to-rising), i.e. the full period between repeats of a level."""
    if len(edges) < 2:
        return np.array([], dtype=np.int64)
    rising = np.array([idx for idx, polarity in edges if polarity], dtype=np.int64)
    falling = np.array([idx for idx, polarity in edges if not polarity], dtype=np.int64)
    rising_intervals = (
        np.diff(rising) if len(rising) >= 2 else np.array([], dtype=np.int64)
    )
    falling_intervals = (
        np.diff(falling) if len(falling) >= 2 else np.array([], dtype=np.int64)
    )
    return np.sort(np.concatenate([rising_intervals, falling_intervals]))
