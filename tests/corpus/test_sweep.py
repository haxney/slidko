import json
from collections import defaultdict

from slidko.corpus.sweep import run_sweep
from tests.corpus.test_sidecar import CORPUS_EXAMPLE

SIDECAR_FIELDS = {
    k: v
    for k, v in CORPUS_EXAMPLE.items()
    if k not in ("id", "capture_file", "receiver_verdict", "sweep_cell")
}

VERDICT = {"observed": "flicker", "notes": "sweep", "contemporaneous": True}


def test_sweep_cell_functionality(tmp_path, monkeypatch):
    """A cell.json with axis="length_m", values=[1,5,10] produces three
    entries, each sidecar carrying sweep_cell.axis="length_m" and its own
    value; entries group cleanly by (cell, axis)."""
    monkeypatch.chdir(tmp_path)

    cell_config = {
        "name": "ws2812-cat6-len",
        "axis": "length_m",
        "fixture": "cat6-utp",
        "fix_arms": [],
        "values": [1, 5, 10],
    }

    written = run_sweep(
        cell_config=cell_config,
        sidecar_fields=SIDECAR_FIELDS,
        instrument_runner=lambda value: f"sr-bytes-for-{value}".encode(),
        verdict_provider=lambda value: VERDICT,
    )

    assert len(written) == 3

    groups: dict[tuple[str, str], list[float]] = defaultdict(list)
    for sr_path, json_path in written:
        assert sr_path.exists()
        assert json_path.exists()
        sidecar_data = json.loads(json_path.read_text())
        sweep_cell = sidecar_data["sweep_cell"]
        assert sweep_cell["axis"] == "length_m"
        groups[sweep_cell["name"], sweep_cell["axis"]].append(sweep_cell["value"])

    assert groups == {("ws2812-cat6-len", "length_m"): [1, 5, 10]}


def test_sweep_cell_entries_cross_reference_by_id(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    cell_config = {
        "name": "ws2812-cat6-len",
        "axis": "length_m",
        "fixture": "cat6-utp",
        "fix_arms": [],
        "values": [1, 5],
    }

    written = run_sweep(
        cell_config=cell_config,
        sidecar_fields=SIDECAR_FIELDS,
        instrument_runner=lambda value: b"bytes",
        verdict_provider=lambda value: VERDICT,
    )

    ids = []
    for _sr_path, json_path in written:
        sidecar_data = json.loads(json_path.read_text())
        entry_id = sidecar_data["capture_file"].removesuffix(".sr")
        assert sidecar_data["id"] == f"ws2812-cat6-len/{entry_id}"
        ids.append(sidecar_data["id"])

    assert ids == [
        "ws2812-cat6-len/entry-0000",
        "ws2812-cat6-len/entry-0001",
    ]
