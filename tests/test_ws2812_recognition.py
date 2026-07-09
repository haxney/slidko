"""Tests for WS2812 signature recognition (measure/ws2812.py)."""

from slidko.measure import ws2812
from tests.synth import SimpleUARTGenerator, SimpleWS2812Generator


def test_recognizes_clean_ws2812_capture():
    capture, _ = SimpleWS2812Generator(payload=[0x5A, 0xC3, 0x11]).generate()
    recognized, confidence = ws2812.recognize(
        capture.channels["din"], capture.samplerate_hz
    )
    assert recognized is True
    assert confidence >= 0.9


def test_does_not_recognize_uart_as_ws2812():
    capture, _ = SimpleUARTGenerator(baud=9600, payload=[0x55, 0xAA]).generate()
    recognized, confidence = ws2812.recognize(
        capture.channels["ch0"], capture.samplerate_hz
    )
    assert recognized is False
    assert confidence < 0.9
