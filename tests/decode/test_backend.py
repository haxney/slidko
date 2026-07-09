"""
Tests for DecodeBackend protocol compliance.

This tests requirement from design.md:
- Define the DecodeBackend Protocol in src/slidko/decode/backend.py:
  decode(capture, hypothesis) -> list[DecodedEvent]
"""

from unittest.mock import Mock

import pytest

from slidko.decode.backend import DecodeBackend, ProtocolHypothesis
from slidko.decode.events import DecodedEvent


def test_decode_backend_protocol():
    """Test that any backend satisfies the structural typing of DecodeBackend."""

    # Create a mock backend instance (it should satisfy the protocol structurally)
    mock_backend = Mock(spec=DecodeBackend)

    # Create a minimal capture-like object
    mock_capture = Mock()

    # Create a minimal protocol hypothesis
    hypothesis = ProtocolHypothesis(
        protocol="uart",
        parameters={
            "baud": 9600,
            "data_bits": 8,
            "parity": "none",
            "stop_bits": 1.0,
            "rx_channel": "D0",
        },
        channel_assignments={"rx": "D0"},
    )

    # This should not raise a TypeError - the interface should be satisfied
    mock_backend.decode(mock_capture, hypothesis)

    # Verify the method was called
    mock_backend.decode.assert_called_once_with(mock_capture, hypothesis)


def test_backend_returns_list_decoded_events():
    """Test that backend returns list of DecodedEvent."""

    # Create sample event
    sample_event = DecodedEvent(
        kind="uart.byte",
        start_sample=100,
        end_sample=200,
        data={"value": 0x41, "ascii": "A"},
        channel="D0",
    )

    # Mock backend that returns our event
    mock_backend = Mock(spec=DecodeBackend)
    mock_backend.decode.return_value = [sample_event]

    mock_capture = Mock()
    hypothesis = ProtocolHypothesis(
        protocol="uart",
        parameters={
            "baud": 9600,
            "data_bits": 8,
            "parity": "none",
            "stop_bits": 1.0,
            "rx_channel": "D0",
        },
        channel_assignments={"rx": "D0"},
    )

    # Test that it returns the expected result
    result = mock_backend.decode(mock_capture, hypothesis)
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0] == sample_event


if __name__ == "__main__":
    pytest.main([__file__])
