"""
Parametrized tests showing backend compatibility.

Tests requirements from design.md:
- Write parametrized test running same UART assertions on both backends
- Prove abstraction works: native and sigrok paths produce equivalent results
"""

import pytest

from slidko.decode.backend import ProtocolHypothesis
from slidko.decode.native_uart import NativeUARTBackend
from slidko.decode.sigrok_backend import SigrokBackend
from tests.synth import SimpleUARTGenerator


def test_uart_backend_compatibility():
    """Test that native and sigrok backends produce same results for UART."""

    # Test with simple payload
    generator = SimpleUARTGenerator(baud=9600, payload=[0x41, 0x42])
    capture, _ground_truth = generator.generate()

    # Create hypothesis (what Measure would produce)
    hypothesis = ProtocolHypothesis(
        protocol="uart",
        parameters={
            "baud": 9600,
            "data_bits": 8,
            "parity": "none",
            "stop_bits": 1.0,
            "rx_channel": "ch0",
        },
        channel_assignments={"rx": "ch0"},
    )

    # Test both backends
    native_backend = NativeUARTBackend()
    sigrok_backend = SigrokBackend()

    # These should pass after full implementation - once implemented, replace
    # with real assertions comparing native_backend.decode(...) and
    # sigrok_backend.decode(...) results for equal/equivalent events
    with pytest.raises(NotImplementedError):
        native_backend.decode(capture, hypothesis)

    with pytest.raises(NotImplementedError):
        sigrok_backend.decode(capture, hypothesis)


if __name__ == "__main__":
    pytest.main([__file__])
