"""Sweep-cell runner.

Reads a `cell.json` (`name, axis, fixture, fix_arms, values`) and sequences
one entry per axis value through `capture_cli.capture_entry`, stamping each
entry's `sweep_cell.axis`/`.value` so downstream evals can extract
degradation curves by grouping on `(cell, axis)` (design.md "Sweep-cell
runner").
"""

from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import Any

from slidko.corpus.capture_cli import capture_entry


def run_sweep(
    cell_config: dict[str, Any],
    sidecar_fields: dict[str, Any],
    instrument_runner: Callable[[float], bytes],
    verdict_provider: Callable[[float], dict[str, Any] | None],
) -> list[tuple[Path, Path]]:
    """Run one entry per value in `cell_config["values"]`.

    `cell_config` is a parsed `cell.json`: `{name, axis, fixture, fix_arms,
    values}`. `sidecar_fields` supplies every sidecar field besides `id`/
    `capture_file`/`receiver_verdict`/`sweep_cell`, which this function
    fills in per entry. `instrument_runner`/`verdict_provider` are called
    once per value (the value itself is passed through, e.g. to select a
    fixture length) -- tests inject mocks, no hardware.

    Returns the `(sr_path, json_path)` pairs written, one per value, in
    `cell_config["values"]` order.
    """
    cell_name = cell_config["name"]
    axis = cell_config["axis"]
    values = cell_config["values"]

    written: list[tuple[Path, Path]] = []
    for index, value in enumerate(values):
        entry_id = f"entry-{index:04d}"
        fields = {
            **sidecar_fields,
            "sweep_cell": {"name": cell_name, "axis": axis, "value": value},
        }
        sr_path, json_path = capture_entry(
            cell=cell_name,
            entry_id=entry_id,
            sidecar_fields=fields,
            instrument_runner=partial(instrument_runner, value),
            verdict_provider=partial(verdict_provider, value),
        )
        written.append((sr_path, json_path))

    return written
