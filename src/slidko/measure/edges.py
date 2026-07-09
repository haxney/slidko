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


def active_window(channels: list[np.ndarray]) -> tuple[int, int]:
    """[start, end) sample range spanning the first to last edge across all
    given channels - the region where anything happens, so periodicity
    comparisons aren't diluted by idle padding around a short burst in an
    otherwise much longer simultaneous capture."""
    first: int | None = None
    last: int | None = None
    for channel in channels:
        idxs = [idx for idx, _ in extract_edges(channel)]
        if not idxs:
            continue
        channel_first, channel_last = min(idxs), max(idxs)
        first = channel_first if first is None else min(first, channel_first)
        last = channel_last if last is None else max(last, channel_last)
    if first is None or last is None:
        return 0, len(channels[0]) if channels else 0
    return first, last + 1


def high_pulse_durations_ns(channel: np.ndarray, samplerate_hz: int) -> list[float]:
    """Duration in nanoseconds of every high pulse (rising edge to the next
    falling edge), used by fixed-timing signature-match discriminators
    (WS2812, DShot, PWM)."""
    return [high_ns for high_ns, _period_ns in pulse_cells_ns(channel, samplerate_hz)]


def pulse_cells_ns(
    channel: np.ndarray, samplerate_hz: int
) -> list[tuple[float, float]]:
    """(high_ns, period_ns) for every rising-edge-to-next-rising-edge cell.
    Checking both lets a fixed-timing discriminator (DShot) reject a plain
    constant-duty square wave whose high time alone happens to land in a
    spec window but whose overall bit period doesn't match at all."""
    sample_ns = 1e9 / samplerate_hz
    edges = extract_edges(channel)
    rising_idxs = [idx for idx, rising in edges if rising]
    n = len(channel)
    cells: list[tuple[float, float]] = []
    for i, start in enumerate(rising_idxs):
        end = start
        while end < n and channel[end]:
            end += 1
        high_ns = (end - start) * sample_ns
        if i + 1 < len(rising_idxs):
            period_ns = (rising_idxs[i + 1] - start) * sample_ns
        else:
            period_ns = float("nan")
        cells.append((high_ns, period_ns))
    return cells


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
