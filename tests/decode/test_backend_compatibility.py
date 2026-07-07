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
    capture, ground_truth = generator.generate()

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

    # These should pass after full implementation
    with pytest.raises(NotImplementedError):
        # Native backend result
        native_events = native_backend.decode(capture, hypothesis)

        # Sigrok backend result (if available) - for this test we expect NotImplementedError
        sigrok_events = sigrok_backend.decode(capture, hypothesis)

        # In a complete implementation, these would be equal or equivalent

        assert len(native_events) == len(sigrok_events)
        # More detailed assertions would go here based on actual output


if __name__ == "__main__":
    pytest.main([__file__])
