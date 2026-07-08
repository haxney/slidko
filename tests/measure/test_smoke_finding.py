import pytest


# This will fail until we implement the SmokeFinding class
def test_smoke_finding_dataclass():
    # Test that SmokeFinding can be imported and has required fields
    from slidko.measure.smoke import SmokeFinding

    # Test creating a SmokeFinding instance
    finding = SmokeFinding(
        check="edge_chatter",
        channel="channel_A",
        start_sample=100,
        end_sample=200,
        severity="warn",
        summary="Detected edge chatter with 5 instances",
        escalation="smoke → scope: capture this line with an oscilloscope; expect ringing",
        evidence={"instances": 5, "avg_interval": 0.1},
    )

    # Test that all fields are present and correct
    assert finding.check == "edge_chatter"
    assert finding.channel == "channel_A"
    assert finding.start_sample == 100
    assert finding.end_sample == 200
    assert finding.severity == "warn"
    assert finding.summary == "Detected edge chatter with 5 instances"
    assert (
        finding.escalation
        == "smoke → scope: capture this line with an oscilloscope; expect ringing"
    )
    assert finding.evidence == {"instances": 5, "avg_interval": 0.1}


if __name__ == "__main__":
    pytest.main([__file__])
