"""Tests for the I2C discriminator (measure/i2c.py) against synthetic ground truth."""

from slidko.measure.i2c import assign_roles, classify_i2c, detect_start_stop
from tests.synth import SimpleI2CGenerator


def test_detect_start_stop_finds_exactly_one_transaction():
    capture, _ = SimpleI2CGenerator(address=0x33, payload=[0x01, 0x02, 0x03]).generate()
    scl = capture.channels["scl"]
    sda = capture.channels["sda"]

    result = detect_start_stop(scl, sda)

    assert len(result.starts) == 1
    assert len(result.stops) == 1
    assert result.starts[0] < result.stops[0]


def test_detect_start_stop_transitions_land_while_scl_high():
    capture, _ = SimpleI2CGenerator(address=0x10, payload=[0xAB]).generate()
    scl = capture.channels["scl"]
    sda = capture.channels["sda"]

    result = detect_start_stop(scl, sda)

    for idx in result.starts + result.stops:
        assert bool(scl[idx - 1]) is True
        assert bool(scl[idx]) is True


def test_assign_roles_identifies_scl_regardless_of_label_or_order():
    capture, _ = SimpleI2CGenerator(address=0x20, payload=[0x11, 0x22]).generate()
    scl = capture.channels["scl"]
    sda = capture.channels["sda"]

    forward = assign_roles({"line_a": scl, "line_b": sda})
    assert forward.scl_channel == "line_a"
    assert forward.sda_channel == "line_b"
    assert forward.confidence > 0.0

    reversed_order = assign_roles({"line_b": sda, "line_a": scl})
    assert reversed_order.scl_channel == "line_a"
    assert reversed_order.sda_channel == "line_b"


def test_classify_i2c_on_generic_channel_names():
    capture, _ = SimpleI2CGenerator(address=0x55, payload=[0xDE, 0xAD]).generate()
    channels = {"D0": capture.channels["sda"], "D1": capture.channels["scl"]}

    claim = classify_i2c(channels)

    assert claim.protocol == "I2C"
    assert claim.scl_channel == "D1"
    assert claim.sda_channel == "D0"
    assert claim.start_count == 1
    assert claim.stop_count == 1
    assert claim.confidence > 0.5
