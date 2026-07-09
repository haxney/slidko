"""Tests for the SPI discriminator (measure/spi.py) against synthetic ground truth."""

import pytest

from slidko.measure.spi import assign_roles, classify_spi
from tests.synth import SimpleSPIGenerator

# Printable payload so the coherent-double-decode CPHA heuristic has signal.
PAYLOAD = [0x41, 0x42, 0x43]  # "ABC"


@pytest.mark.parametrize(("cpol", "cpha"), [(0, 0), (0, 1), (1, 0), (1, 1)])
def test_classify_spi_recovers_mode_on_generic_channel_names(cpol, cpha):
    capture, ground_truth = SimpleSPIGenerator(
        cpol=cpol, cpha=cpha, payload=PAYLOAD
    ).generate()
    channels = {
        "D2": capture.channels["cs"],
        "D0": capture.channels["sck"],
        "D1": capture.channels["mosi"],
    }

    claim = classify_spi(channels)

    assert claim.protocol == "SPI"
    assert claim.clock_channel == "D0"
    assert claim.cs_channel == "D2"
    assert claim.data_channel == "D1"
    assert claim.cpol == ground_truth.parameters["cpol"]
    assert claim.cpha == ground_truth.parameters["cpha"]
    assert claim.confidence > 0.0


def test_assign_roles_is_order_independent():
    capture, _ = SimpleSPIGenerator(cpol=0, cpha=0, payload=PAYLOAD).generate()
    a = assign_roles({
        "cs": capture.channels["cs"],
        "sck": capture.channels["sck"],
        "mosi": capture.channels["mosi"],
    })
    b = assign_roles({
        "mosi": capture.channels["mosi"],
        "cs": capture.channels["cs"],
        "sck": capture.channels["sck"],
    })
    assert a == b
    assert a.clock_channel == "sck"
    assert a.cs_channel == "cs"
    assert a.data_channel == "mosi"
