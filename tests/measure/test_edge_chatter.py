import pytest

from slidko.measure.smoke import detect_edge_chatter


def test_edge_chatter_clean_capture():
    """Test that clean captures (with no chatter) yield no chatter findings"""
    # A simple square wave - no chatter
    edges = [0, 100, 200, 300, 400, 500]
    t_bit = 100

    findings = detect_edge_chatter(edges, t_bit, "channel_A")

    # Should produce no findings for clean capture
    assert len(findings) == 0


def test_edge_chatter_with_burst():
    """Test that a capture with injected multi-crossing chatter yields a finding"""
    # Simulate chatter - multiple edges in quick succession to make 3 fast consecutive intervals
    # [0, 40, 50, 60, 70, 100]
    # intervals: [40, 10, 10, 10, 30]
    # 3 consecutive fast intervals (intervals 1,2,3) = edges at indices 1,2,3,4
    # The burst starts at edge[1] = 40 and ends with the last fast edge
    # which is the edge at index 4: edges[4] = 70
    edges = [0, 40, 50, 60, 70, 100]
    t_bit = 100

    findings = detect_edge_chatter(edges, t_bit, "channel_A")

    # Should detect the chatter burst (3 consecutive fast edges < 0.25 * 100)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "edge_chatter"
    assert finding.channel == "channel_A"
    # The window should cover the fast edge burst: from start_edge to end-edge
    assert finding.start_sample == 40
    assert finding.end_sample == 70


if __name__ == "__main__":
    pytest.main([__file__])
