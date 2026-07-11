import json

import pytest

from slidko.corpus.capture_cli import VerdictRequiredError, capture_entry
from tests.corpus.test_sidecar import CORPUS_EXAMPLE

# Fields Sidecar.from_json needs besides id/capture_file/receiver_verdict,
# which capture_entry fills in itself.
SIDECAR_FIELDS = {
    k: v
    for k, v in CORPUS_EXAMPLE.items()
    if k not in ("id", "capture_file", "receiver_verdict")
}

VERDICT = {"observed": "flicker", "notes": "hand test", "contemporaneous": True}


def test_capture_cli_with_mocked_instrument_and_verdict(tmp_path, monkeypatch):
    """One CLI invocation writes entry-*.sr + entry-*.json into the correct
    cell dir, the two cross-reference by id, and the sidecar validates."""
    monkeypatch.chdir(tmp_path)

    sr_path, json_path = capture_entry(
        cell="ws2812-cat6-len",
        entry_id="entry-0001",
        sidecar_fields=SIDECAR_FIELDS,
        instrument_runner=lambda: b"fake .sr bytes",
        verdict_provider=lambda: VERDICT,
    )

    cell_dir = tmp_path / "corpus/cells/ws2812-cat6-len"
    assert sr_path.resolve() == cell_dir / "entry-0001.sr"
    assert json_path.resolve() == cell_dir / "entry-0001.json"
    assert sr_path.exists()
    assert json_path.exists()
    assert sr_path.read_bytes() == b"fake .sr bytes"

    sidecar_data = json.loads(json_path.read_text())
    assert sidecar_data["id"] == "ws2812-cat6-len/entry-0001"
    assert sidecar_data["capture_file"] == "entry-0001.sr"
    assert sidecar_data["receiver_verdict"] == VERDICT


def test_capture_cli_refuses_to_write_without_verdict(tmp_path, monkeypatch):
    """When NO receiver verdict is supplied, the CLI refuses to write an
    entry (labeling discipline) and creates no files."""
    monkeypatch.chdir(tmp_path)
    instrument_called = False

    def instrument_runner() -> bytes:
        nonlocal instrument_called
        instrument_called = True
        return b"should never be captured"

    with pytest.raises(VerdictRequiredError):
        capture_entry(
            cell="ws2812-cat6-len",
            entry_id="entry-0002",
            sidecar_fields=SIDECAR_FIELDS,
            instrument_runner=instrument_runner,
            verdict_provider=lambda: None,
        )

    assert instrument_called is False
    assert list(tmp_path.rglob("*")) == []
