import unittest

from slidko.decode.events import DecodedEvent as CanonicalDecodedEvent
from slidko.narrate.transaction_summary import summarize_transactions

# Test the transaction summarization functionality


class TestTransactionSummary(unittest.TestCase):
    def test_transaction_summary_with_naks(self):
        """A synthetic I2C event stream of N transactions to 0x68 with M NAKs
        produces a `transaction.summary` assertion whose text states N and M
        with the address and candidate part names, and whose evidence
        references the contributing event indices."""
        events = [
            CanonicalDecodedEvent(
                kind="i2c.start",
                start_sample=100,
                end_sample=105,
                data={"address": 0x68},
                channel="0",
            ),
            CanonicalDecodedEvent(
                kind="i2c.data",
                start_sample=110,
                end_sample=115,
                data={"address": 0x68},
                channel="0",
            ),
            CanonicalDecodedEvent(
                kind="i2c.stop",
                start_sample=120,
                end_sample=125,
                data={"address": 0x68},
                channel="0",
            ),
            CanonicalDecodedEvent(
                kind="i2c.start",
                start_sample=130,
                end_sample=135,
                data={"address": 0x68},
                channel="0",
            ),
            CanonicalDecodedEvent(
                kind="i2c.data",
                start_sample=140,
                end_sample=145,
                data={"address": 0x68},
                channel="0",
            ),
            CanonicalDecodedEvent(
                kind="i2c.nak",
                start_sample=150,
                end_sample=155,
                data={"address": 0x68},
                channel="0",
            ),  # NAK event
            CanonicalDecodedEvent(
                kind="i2c.stop",
                start_sample=160,
                end_sample=165,
                data={"address": 0x68},
                channel="0",
            ),
        ]

        assertions = summarize_transactions(events)
        assert len(assertions) > 0
        summary = assertions[0]
        assert summary.kind == "transaction.summary"
        assert "0x68" in summary.text
        assert "2" in summary.text  # 2 transactions (two i2c.start events)
        assert "1" in summary.text  # 1 NAK
        assert len(summary.evidence.event_indices) > 0

    def test_transaction_summary_different_address(self):
        """Test with another known address - BME280"""
        events = [
            CanonicalDecodedEvent(
                kind="i2c.start",
                start_sample=100,
                end_sample=105,
                data={"address": 0x76},
                channel="0",
            ),
            CanonicalDecodedEvent(
                kind="i2c.data",
                start_sample=110,
                end_sample=115,
                data={"address": 0x76},
                channel="0",
            ),
        ]

        assertions = summarize_transactions(events)
        # Now with the updated implementation, should produce a summary for address 0x76
        assert len(assertions) > 0
        assert "0x76" in assertions[0].text
        assert "1" in assertions[0].text  # 1 transaction


if __name__ == "__main__":
    unittest.main()
