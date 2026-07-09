"""
Real-sigrok integration test (task 4.4): crafts a .sr file in a tmp dir and
decodes it with the actual sigrok-cli subprocess boundary, no mocking.
Skips cleanly when sigrok-cli isn't installed, mirroring Phase 0's
`demo_capture` skip pattern (tests/conftest.py).
"""

import shutil

import pytest

from slidko.decode.backend import ProtocolHypothesis
from slidko.decode.sigrok_backend import SigrokBackend
from tests.synth import SimpleUARTGenerator

pytestmark = pytest.mark.skipif(
    shutil.which("sigrok-cli") is None, reason="sigrok-cli not installed"
)


def test_sigrok_backend_decodes_real_sr_file():
    generator = SimpleUARTGenerator(baud=9600, payload=[0x41, 0x42])
    capture, ground_truth = generator.generate()

    hypothesis = ProtocolHypothesis(
        protocol="uart",
        parameters={
            "baud": ground_truth.parameters["baud"],
            "data_bits": ground_truth.parameters["data_bits"],
            "parity": ground_truth.parameters["parity"],
            "stop_bits": ground_truth.parameters["stop_bits"],
            "rx_channel": "ch0",
        },
        channel_assignments={"rx": "ch0"},
    )

    backend = SigrokBackend()
    events = backend.decode(capture, hypothesis)

    assert [e.kind for e in events] == ["uart.byte", "uart.byte"]
    assert [e.data["value"] for e in events] == ground_truth.payload


if __name__ == "__main__":
    pytest.main([__file__])
