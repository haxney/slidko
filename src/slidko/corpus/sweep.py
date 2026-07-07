"""Sweep-cell runner.

This module reads a cell.json definition and sequences entries along an axis.
"""

from typing import Any


def run_sweep(cell_name: str, values: list[float]) -> list[dict[str, Any]]:
    """Run sweep for specified values along the cell's axis.

    Args:
        cell_name: Name of the sweep cell to run
        values: List of values to sweep through

    Returns:
        List of sidecar dictionaries for each entry in the sweep
    """
    # This is a placeholder implementation - in reality this would:
    # 1. Read the cell.json to get axis information
    # 2. For each value, run capture
    # 3. Create sidecars with appropriate sweep_cell data
    # 4. Return the set of entries

    entries = []

    # For demonstration purposes, we'll just return some mock data
    for i, value in enumerate(values):
        entry = {
            "id": f"{cell_name}/entry-{i:04d}",
            "capture_file": f"entry-{i:04d}.sr",
            "sweep_cell": {
                "name": cell_name,
                "axis": "length_m",  # This would come from the cell.json
                "value": value,
            },
        }
        entries.append(entry)

    return entries


def main():
    """Main sweep entry point."""
    print("Sweep runner not fully implemented in this phase")


if __name__ == "__main__":
    main()
