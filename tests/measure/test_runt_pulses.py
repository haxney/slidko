import pytest

from src.slidko.measure.smoke import detect_runt_pulses


def test_runt_pulses_clean_capture():
    """Test that clean captures (with no runt pulses) yield no findings"""
    # A simple square wave - no runt pulses
    edges = [0, 100, 200, 300, 400, 500]

    findings = detect_runt_pulses(edges, "channel_A")

    # Should produce no findings for clean capture
    assert len(findings) == 0


def test_runt_pulses_with_glitch():
    """Test that a capture with an injected 1-2 sample glitch yields a finding"""
    # Create edges where there's a 1-sample pulse
    # [0, 99, 100, 200, 300] - 1-sample pulse from edge 1 to 2
    # This is an illegal runt pulse
    edges = [0, 99, 100, 200, 300]

    findings = detect_runt_pulses(edges, "channel_A")

    # Should detect the runt pulse
    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "runt_pulse"
    assert finding.channel == "channel_A"
    # Window should cover the 1-sample pulse
    assert finding.start_sample == 99
    assert finding.end_sample == 100


def test_runt_pulses_with_two_samples():
    """Test that a capture with a 2-sample glitch yields a finding"""
    # Create edges where there's a 2-sample pulse
    # [0, 98, 100, 200, 300] - 2-sample pulse from edge 1 to 2
    edges = [0, 98, 100, 200, 300]

    findings = detect_runt_pulses(edges, "channel_A")

    # Should detect the runt pulse
    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "runt_pulse"
    assert finding.channel == "channel_A"
    # Window should cover the 2-sample pulse
    assert finding.start_sample == 98
    assert finding.end_sample == 100


if __name__ == "__main__":
    pytest.main([__file__])
