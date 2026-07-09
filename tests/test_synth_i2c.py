"""Tests for the synthetic I2C generator (tests/synth.py)."""

import numpy as np

from tests.synth import SimpleI2CGenerator


def _decode_i2c(scl: np.ndarray, sda: np.ndarray) -> tuple[list[int], bool, bool]:
    """Minimal reference I2C decoder used only to verify generator correctness."""
    scl_diff = np.diff(scl.astype(int))
    rising = sorted(np.flatnonzero(scl_diff == 1) + 1)

    sda_diff = np.diff(sda.astype(int))
    saw_start = False
    saw_stop = False
    for idx in np.flatnonzero(sda_diff):
        if scl[idx] and scl[idx + 1]:
            if sda_diff[idx] < 0:
                saw_start = True
            else:
                saw_stop = True

    bits = [bool(sda[idx]) for idx in rising]
    bytes_out = []
    i = 0
    while i + 9 <= len(bits):
        value = 0
        for b in bits[i : i + 8]:
            value = (value << 1) | int(b)
        bytes_out.append(value)
        i += 9  # 8 data bits + 1 ack/nak bit
    return bytes_out, saw_start, saw_stop


def test_i2c_start_stop_and_payload_roundtrip():
    address = 0x42
    payload = [0xDE, 0xAD, 0xBE]
    capture, ground_truth = SimpleI2CGenerator(
        address=address, payload=payload, rw=0
    ).generate()

    scl = capture.channels["scl"]
    sda = capture.channels["sda"]
    assert len(scl) == len(sda)

    decoded_bytes, saw_start, saw_stop = _decode_i2c(scl, sda)

    assert saw_start
    assert saw_stop
    expected_addr_rw = (address << 1) | 0
    assert decoded_bytes[0] == expected_addr_rw
    assert decoded_bytes[1:] == payload
    assert ground_truth.parameters["address"] == address


def test_i2c_sda_transitions_only_while_scl_low_except_start_stop():
    capture, _ = SimpleI2CGenerator(address=0x10, payload=[0x01, 0x02]).generate()
    scl = capture.channels["scl"]
    sda = capture.channels["sda"]

    sda_diff = np.diff(sda.astype(int))
    transition_idx = np.flatnonzero(sda_diff)

    start_stop_count = 0
    for idx in transition_idx:
        if scl[idx] and scl[idx + 1]:
            start_stop_count += 1
        else:
            assert not scl[idx]
            assert not scl[idx + 1]

    assert start_stop_count == 2  # exactly one start + one stop


def test_i2c_single_byte_payload_roundtrip():
    capture, _ground_truth = SimpleI2CGenerator(address=0x50, payload=[0x99]).generate()
    scl = capture.channels["scl"]
    sda = capture.channels["sda"]
    decoded_bytes, _, _ = _decode_i2c(scl, sda)
    assert decoded_bytes == [(0x50 << 1) | 0, 0x99]
