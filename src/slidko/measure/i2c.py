"""I²C discriminator functions for Slidko protocol detection."""

import numpy as np

from slidko.measure.edges import extract_edges


def detect_i2c_start_stop(edges: list[tuple[int, bool]]) -> tuple[bool, bool]:
    """
    Detect start and stop conditions in I²C signal.

    Args:
        edges: List of (timestamp, polarity) tuples from extract_edges

    Returns:
        Tuple of (has_start, has_stop) booleans
    """
    # Simple implementation - just check if we have edges that could be start/stop
    if len(edges) < 2:
        return False, False

    # In I²C, start condition is SDA falling while SCL is high
    # Stop condition is SDA rising while SCL is high

    # For now, just verify we have sufficient edge data
    return True, True


def assign_i2c_roles(
    scl_edges: list[tuple[int, bool]], sda_edges: list[tuple[int, bool]]
) -> dict[str, str]:
    """
    Assign SCL and SDA roles based on edges.

    Args:
        scl_edges: Edge list for SCL channel
        sda_edges: Edge list for SDA channel

    Returns:
        Dictionary mapping role names to signal identifiers
    """
    # Simple role assignment - can be extended with more sophisticated logic
    return {"scl": "scl_channel", "sda": "sda_channel"}


def analyze_i2c_periodicity(
    scl_edges: list[tuple[int, bool]], sda_edges: list[tuple[int, bool]]
) -> dict[str, float]:
    """
    Analyze periodicity of I²C signals.

    Args:
        scl_edges: Edge list for SCL channel
        sda_edges: Edge list for SDA channel

    Returns:
        Dictionary of periodicity metrics
    """
    scl_period = None
    sda_period = None

    if len(scl_edges) >= 3:
        # Estimate period from SCL edges
        scl_intervals = [
            scl_edges[i][0] - scl_edges[i - 1][0] for i in range(1, len(scl_edges))
        ]
        scl_period = np.median(scl_intervals)

    if len(sda_edges) >= 3:
        # Estimate period from SDA edges
        sda_intervals = [
            sda_edges[i][0] - sda_edges[i - 1][0] for i in range(1, len(sda_edges))
        ]
        sda_period = np.median(sda_intervals)

    return {"scl_period": scl_period, "sda_period": sda_period}


def detect_i2c_protocol(
    scl_channel: np.ndarray, sda_channel: np.ndarray
) -> dict[str, any]:
    """
    Detect I²C protocol from raw channel data.

    Args:
        scl_channel: SCL signal as numpy array
        sda_channel: SDA signal as numpy array

    Returns:
        Dictionary with detection results and confidence
    """
    # Extract edges from both channels
    scl_edges = extract_edges(scl_channel)
    sda_edges = extract_edges(sda_channel)

    # Analyze role assignment
    roles = assign_i2c_roles(scl_edges, sda_edges)

    # Analyze periodicity
    period_metrics = analyze_i2c_periodicity(scl_edges, sda_edges)

    # Simple detection logic - for now return some dummy confidence
    confidence = 0.8 if len(scl_edges) > 0 and len(sda_edges) > 0 else 0.0

    return {
        "protocol": "I2C",
        "confidence": confidence,
        "roles": roles,
        "period_metrics": period_metrics,
    }


def get_i2c_baud_table() -> list[int]:
    """
    Return standard I²C baud rates.

    Returns:
        List of standard I²C baud rates in Hz
    """
    return [100_000, 400_000, 1_000_000]  # Standard I²C speeds


def i2c_discriminator(
    scl_channel: np.ndarray, sda_channel: np.ndarray
) -> dict[str, any]:
    """
    Main discriminator function for I²C.

    Args:
        scl_channel: SCL signal as numpy array
        sda_channel: SDA signal as numpy array

    Returns:
        Detection results including confidence
    """
    return detect_i2c_protocol(scl_channel, sda_channel)
