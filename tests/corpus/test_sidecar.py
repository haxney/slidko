from typing import Any

from slidko.corpus.sidecar import Sidecar

# Test data from docs/CORPUS.md
CORPUS_EXAMPLE: dict[str, Any] = {
    "id": "cell-ws2812-cat6-len/entry-0042",
    "capture_file": "entry-0042.sr",
    "instrument": {
        "model": "fx2lafw-clone",
        "samplerate_hz": 24000000,
        "threshold_v": 1.4,
        "channels": {"0": "DATA", "7": "SYNC"},
    },
    "driver": {"chip": "...", "vdd_v": 3.3, "series_r_ohm": 0},
    "transport": {
        "cable": "cat6-utp",
        "length_m": 10,
        "twisted": True,
        "shielded": False,
        "termination": "none",
    },
    "receiver": {"part": "WS2812B", "vdd_v": 5.0, "vih_v": 3.5},
    "protocol": {"name": "ws2812", "nominal": {"bitrate_hz": 800000}},
    "fault_injected": {"class": "level-mismatch", "params": {}},
    "receiver_verdict": {
        "observed": "flicker",
        "notes": "...",
        "contemporaneous": True,
    },
    "sweep_cell": {"name": "ws2812-cat6-len", "axis": "length_m", "value": 10},
    "referee": None,
}


def test_sidecar_round_trip():
    """Test that the CORPUS.md example JSON round-trips through Sidecar.from_json and to_json"""
    sidecar = Sidecar.from_json(CORPUS_EXAMPLE)
    result_json = sidecar.to_json()

    # Check that all values match (we need to normalize the dict keys for comparison)
    assert result_json["id"] == CORPUS_EXAMPLE["id"]
    assert result_json["capture_file"] == CORPUS_EXAMPLE["capture_file"]
    assert result_json["instrument"] == CORPUS_EXAMPLE["instrument"]
    assert result_json["driver"] == CORPUS_EXAMPLE["driver"]
    assert result_json["transport"] == CORPUS_EXAMPLE["transport"]
    assert result_json["receiver"] == CORPUS_EXAMPLE["receiver"]
    assert result_json["protocol"] == CORPUS_EXAMPLE["protocol"]
    assert (
        result_json["fault_injected"]["class"]
        == CORPUS_EXAMPLE["fault_injected"]["class"]
    )
    assert (
        result_json["fault_injected"]["params"]
        == CORPUS_EXAMPLE["fault_injected"]["params"]
    )
    assert result_json["receiver_verdict"] == CORPUS_EXAMPLE["receiver_verdict"]
    assert result_json["sweep_cell"] == CORPUS_EXAMPLE["sweep_cell"]
    assert result_json["referee"] == CORPUS_EXAMPLE["referee"]


def test_missing_receiver_verdict_validation():
    """Test that a sidecar dict lacking receiver_verdict fails validate with an error naming the missing field"""
    # Create a sidecar without receiver_verdict
    invalid_sidecar_data = CORPUS_EXAMPLE.copy()
    del invalid_sidecar_data["receiver_verdict"]

    sidecar = Sidecar.from_json(invalid_sidecar_data)
    errors = Sidecar.validate(sidecar)

    assert len(errors) > 0
    assert "receiver_verdict" in errors[0]


def test_referee_validation():
    """Test that a sidecar with a populated referee block validates (day-one support); a referee of null also validates"""
    # Test with a populated referee
    sidecar_data_with_referee = CORPUS_EXAMPLE.copy()
    sidecar_data_with_referee["referee"] = {"instrument": "fx2lafw-second"}

    sidecar_with_referee = Sidecar.from_json(sidecar_data_with_referee)
    errors_with_referee = Sidecar.validate(sidecar_with_referee)
    assert len(errors_with_referee) == 0  # Should validate successfully

    # Test with referee = null
    sidecar_data_null_referee = CORPUS_EXAMPLE.copy()
    sidecar_data_null_referee["referee"] = None

    sidecar_null_referee = Sidecar.from_json(sidecar_data_null_referee)
    errors_null_referee = Sidecar.validate(sidecar_null_referee)
    assert len(errors_null_referee) == 0  # Should also validate successfully
