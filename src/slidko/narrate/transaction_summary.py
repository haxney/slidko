from slidko.decode.events import DecodedEvent
from slidko.narrate.address_book import lookup
from slidko.narrate.model import Assertion, Evidence


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
    assertions: list[Assertion] = []

    if not events:
        return assertions

    # Group events by address
    address_events: dict[int, list[DecodedEvent]] = {}
    for event in events:
        addr = event.data.get("address", None)
        if addr is not None:
            if addr not in address_events:
                address_events[addr] = []
            address_events[addr].append(event)

    # Process each address group
    for addr, addr_events in address_events.items():
        # Look for start events to count transactions
        start_events = [i for i, e in enumerate(addr_events) if e.kind == "i2c.start"]

        if start_events:
            transaction_count = len(start_events)

            # Count NAKs for this address
            nak_count = sum(1 for e in addr_events if e.kind == "i2c.nak")

            # Get candidates for this address
            candidates = lookup(addr)

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
            text_parts = [f"{transaction_count} transactions to address 0x{addr:02x}"]
            if nak_count > 0:
                text_parts.append(
                    f"with {nak_count} NAK{'s' if nak_count != 1 else ''}"
                )
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
    pass
