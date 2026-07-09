"""Tests for PWM/servo signature recognition (measure/pwm.py)."""

from slidko.measure import pwm
from tests.synth import SimplePWMGenerator, SimpleUARTGenerator


def test_recognizes_clean_servo_pwm():
    capture, _ = SimplePWMGenerator(freq_hz=50, pulse_us=1500, num_pulses=5).generate()
    recognized, confidence = pwm.recognize(
        capture.channels["pwm"], capture.samplerate_hz
    )
    assert recognized is True
    assert confidence >= 0.9


def test_recognizes_fast_esc_pwm():
    capture, _ = SimplePWMGenerator(freq_hz=400, pulse_us=1200, num_pulses=5).generate()
    recognized, _confidence = pwm.recognize(
        capture.channels["pwm"], capture.samplerate_hz
    )
    assert recognized is True


def test_does_not_recognize_uart_as_pwm():
    capture, _ = SimpleUARTGenerator(baud=9600, payload=[0x55, 0xAA, 0x3C]).generate()
    recognized, _confidence = pwm.recognize(
        capture.channels["ch0"], capture.samplerate_hz
    )
    assert recognized is False
