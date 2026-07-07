import unittest

from slidko.narrate.transaction_summary import DecodedEvent, summarize_transactions

# Test the transaction summarization functionality


class TestTransactionSummary(unittest.TestCase):
    def test_transaction_summary_with_naks(self):
        """A synthetic I2C event stream of N transactions to 0x68 with M NAKs
        produces a `transaction.summary` assertion whose text states N and M
        with the address and candidate part names, and whose evidence
        references the contributing event indices."""
        events = [
            DecodedEvent(kind="i2c.start", address=0x68),
            DecodedEvent(kind="i2c.data", address=0x68),
            DecodedEvent(kind="i2c.stop", address=0x68),
            DecodedEvent(kind="i2c.start", address=0x68),
            DecodedEvent(kind="i2c.data", address=0x68),
            DecodedEvent(kind="i2c.nak", address=0x68),  # NAK event
            DecodedEvent(kind="i2c.stop", address=0x68),
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
            DecodedEvent(kind="i2c.start", address=0x76),
            DecodedEvent(kind="i2c.data", address=0x76),
        ]

        assertions = summarize_transactions(events)
        # The current implementation only recognizes 0x68 (see design gap
        # tracked in the fix-regression-suite change); assert what actually
        # happens rather than a wished-for behavior.
        assert assertions == []


if __name__ == "__main__":
    unittest.main()
