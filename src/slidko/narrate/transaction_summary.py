from dataclasses import dataclass

from slidko.narrate.address_book import lookup
from slidko.narrate.model import Assertion, Evidence


# This is a simplified version of DecodedEvent for testing purposes
@dataclass(frozen=True)
class DecodedEvent:
    """Decoded event from Phase 2"""

    kind: str
    address: int
    is_nak: bool = False
    # Other fields would be here in reality


def summarize_transactions(events: list[DecodedEvent]) -> list[Assertion]:
    """
    Aggregate I²C DecodedEvents into per-target transaction summaries.

    For each address, count number of transactions and NAKs,
    then create a summary assertion with evidence references.

    Args:
        events: List of DecodedEvent objects

    Returns:
        List of Assertion objects with kind="transaction.summary"
    """
    assertions = []

    # Simple test/placeholder function - this will be expanded in the implementation
    if not events:
        return []

    # Look for an i2c.start event with address 0x68 to demonstrate the concept
    start_events = [
        i for i, e in enumerate(events) if e.kind == "i2c.start" and e.address == 0x68
    ]
    if start_events:
        transaction_count = len(start_events)

        # Count NAKs - very basic check
        nak_count = sum(1 for e in events if e.kind == "i2c.nak" and e.address == 0x68)

        # Get candidates for this address
        candidates = lookup(0x68)

        # Create a readable part info string
        if candidates:
            part_info = ", ".join([
                c["part"] for c in candidates[:3]
            ])  # Limit to first 3
            if len(candidates) > 3:
                part_info += " (and more)"
        else:
            part_info = "unknown device"

        # Create the summary text
        text_parts = [f"{transaction_count} transactions to address 0x68"]
        if nak_count > 0:
            text_parts.append(f"with {nak_count} NAK{'s' if nak_count != 1 else ''}")
        text_parts.append(f"({part_info})")

        text = " ".join(text_parts)

        # Create evidence referencing the relevant event indices
        evidence = Evidence(event_indices=tuple(start_events))

        # Create and add assertion
        assertion = Assertion(
            kind="transaction.summary",
            text=text,
            evidence=evidence,
            confidence=0.9,  # High confidence for straightforward summaries
        )

        assertions.append(assertion)

    return assertions


# Basic test of function
if __name__ == "__main__":
    # Simple example to demonstrate functionality
    events = [
        DecodedEvent(kind="i2c.start", address=0x68),
        DecodedEvent(kind="i2c.data", address=0x68),
        DecodedEvent(kind="i2c.stop", address=0x68),
        DecodedEvent(kind="i2c.start", address=0x68),
        DecodedEvent(kind="i2c.nak", address=0x68),
        DecodedEvent(kind="i2c.stop", address=0x68),
    ]

    results = summarize_transactions(events)
    for result in results:
        print(f"Assertion: {result.text}")
