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
