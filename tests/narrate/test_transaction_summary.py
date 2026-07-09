import unittest

from slidko.decode.events import DecodedEvent as CanonicalDecodedEvent
from slidko.narrate.transaction_summary import summarize_transactions

# Test the transaction summarization functionality


class TestTransactionSummary(unittest.TestCase):
    def test_transaction_summary_with_naks(self):
        """A synthetic I2C event stream of N transactions to 0x68 with M NAKs
        produces a `transaction.summary` assertion whose text states N and M
        with the address and candidate part names, and whose evidence
        references the contributing event indices.

        Event shapes match real Decode output (decode/sigrok_backend.py):
        i2c.start carries no address; i2c.address carries it.
        """
        events = [
            CanonicalDecodedEvent(
                kind="i2c.start", start_sample=100, end_sample=100, data={}
            ),
            CanonicalDecodedEvent(
                kind="i2c.address",
                start_sample=105,
                end_sample=108,
                data={"address": 0x68, "rw": "write"},
            ),
            CanonicalDecodedEvent(
                kind="i2c.ack", start_sample=109, end_sample=109, data={}
            ),
            CanonicalDecodedEvent(
                kind="i2c.data", start_sample=110, end_sample=115, data={"value": 0x3B}
            ),
            CanonicalDecodedEvent(
                kind="i2c.ack", start_sample=116, end_sample=116, data={}
            ),
            CanonicalDecodedEvent(
                kind="i2c.stop", start_sample=120, end_sample=125, data={}
            ),
            CanonicalDecodedEvent(
                kind="i2c.start", start_sample=130, end_sample=130, data={}
            ),
            CanonicalDecodedEvent(
                kind="i2c.address",
                start_sample=135,
                end_sample=138,
                data={"address": 0x68, "rw": "write"},
            ),
            CanonicalDecodedEvent(
                kind="i2c.nak", start_sample=150, end_sample=155, data={}
            ),  # NAK event
            CanonicalDecodedEvent(
                kind="i2c.stop", start_sample=160, end_sample=165, data={}
            ),
        ]

        assertions = summarize_transactions(events)
        assert len(assertions) > 0
        summary = assertions[0]
        assert summary.kind == "transaction.summary"
        assert "0x68" in summary.text
        assert "2" in summary.text  # 2 transactions (two i2c.start events)
        assert "1" in summary.text  # 1 NAK

        # Evidence must reference the CONTRIBUTING events by their index
        # into the original events list - every event in both transaction
        # spans (indices 0-5, 6-9).
        assert summary.evidence.event_indices == tuple(range(10))
        for i in summary.evidence.event_indices:
            assert events[i].kind.startswith("i2c.")

    def test_transaction_summary_different_address(self):
        """Test with another known address - BME280"""
        events = [
            CanonicalDecodedEvent(
                kind="i2c.start", start_sample=100, end_sample=100, data={}
            ),
            CanonicalDecodedEvent(
                kind="i2c.address",
                start_sample=105,
                end_sample=108,
                data={"address": 0x76, "rw": "write"},
            ),
            CanonicalDecodedEvent(
                kind="i2c.ack", start_sample=109, end_sample=109, data={}
            ),
            CanonicalDecodedEvent(
                kind="i2c.data", start_sample=110, end_sample=115, data={"value": 0xF7}
            ),
            CanonicalDecodedEvent(
                kind="i2c.stop", start_sample=120, end_sample=125, data={}
            ),
        ]

        assertions = summarize_transactions(events)
        assert len(assertions) > 0
        assert "0x76" in assertions[0].text
        assert "1" in assertions[0].text  # 1 transaction


if __name__ == "__main__":
    unittest.main()
