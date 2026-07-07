#!/usr/bin/env python3

"""
Test script to verify DecodedEvent import and basic functionality.
"""

import os
import sys

sys.path.insert(0, os.path.abspath("."))

from slidko.decode.events import DecodedEvent

# Test creating an event
event = DecodedEvent(
    kind="uart.byte",
    start_sample=100,
    end_sample=200,
    data={"value": 0x41, "ascii": "A"},
    channel="D0",
)

print("DecodedEvent import successful!")
print(f"kind: {event.kind}")
print(f"start_sample: {event.start_sample}")
print(f"end_sample: {event.end_sample}")
print(f"data: {event.data}")
print(f"channel: {event.channel}")

print(f"seconds (24MHz): {event.seconds(24_000_000)}")

# Test equality
event2 = DecodedEvent(
    kind="uart.byte",
    start_sample=100,
    end_sample=200,
    data={"value": 0x41, "ascii": "A"},
    channel="D0",
)

print(f"Events equal: {event == event2}")

# Test immutability
try:
    event.kind = "new.kind"
    print("ERROR: Event should be immutable")
except AttributeError:
    print("SUCCESS: Event is properly immutable")

print("All tests passed!")
