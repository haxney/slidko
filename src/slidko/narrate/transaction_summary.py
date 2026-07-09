from slidko.decode.events import DecodedEvent
from slidko.narrate.address_book import lookup
from slidko.narrate.model import Assertion, Evidence


def summarize_transactions(events: list[DecodedEvent]) -> list[Assertion]:
    """
    Aggregate I²C DecodedEvents into per-target transaction summaries.

    A transaction is one i2c.start .. i2c.stop span; its address comes from
    the i2c.address event within that span (i2c.start itself carries no
    address - see decode/sigrok_backend.py's event shapes). For each
    address, count transactions and NAKs, then create a summary assertion
    with evidence references.

    Args:
        events: List of DecodedEvent objects

    Returns:
        List of Assertion objects with kind="transaction.summary"
    """
    assertions: list[Assertion] = []

    if not events:
        return assertions

    # Split events into per-transaction spans (i2c.start .. i2c.stop, or
    # start .. next start if a stop is missing), tracking each span's
    # address (from its i2c.address event, if any) and event indices.
    transactions: list[dict] = []
    current: dict | None = None
    for i, event in enumerate(events):
        if event.kind == "i2c.start":
            if current is not None:
                transactions.append(current)
            current = {"address": None, "indices": [i]}
            continue
        if current is None:
            continue
        current["indices"].append(i)
        if event.kind == "i2c.address":
            current["address"] = event.data.get("address")
        if event.kind == "i2c.stop":
            transactions.append(current)
            current = None
    if current is not None:
        transactions.append(current)

    # Group transactions by address.
    by_address: dict[int, list[dict]] = {}
    for transaction in transactions:
        addr = transaction["address"]
        if addr is not None:
            by_address.setdefault(addr, []).append(transaction)

    for addr, addr_transactions in by_address.items():
        transaction_count = len(addr_transactions)
        contributing_indices = [i for t in addr_transactions for i in t["indices"]]
        nak_count = sum(1 for i in contributing_indices if events[i].kind == "i2c.nak")

        candidates = lookup(addr)

        # Create a readable part info string
        if candidates:
            part_info = ", ".join([c["part"] for c in candidates[:3]])  # first 3
            if len(candidates) > 3:
                part_info += " (and more)"
        else:
            part_info = "unknown device"

        # Create the summary text
        txn_word = "transaction" if transaction_count == 1 else "transactions"
        text_parts = [f"{transaction_count} {txn_word} to address 0x{addr:02x}"]
        if nak_count > 0:
            text_parts.append(f"with {nak_count} NAK{'s' if nak_count != 1 else ''}")
        text_parts.append(f"({part_info})")

        text = " ".join(text_parts)

        # Evidence references every event contributing to this address's
        # transactions - they all back the N/M counts in the text.
        evidence = Evidence(event_indices=tuple(sorted(contributing_indices)))

        assertions.append(
            Assertion(
                kind="transaction.summary",
                text=text,
                evidence=evidence,
                confidence=0.9,  # High confidence for straightforward summaries
            )
        )

    return assertions
