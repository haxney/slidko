"""
Deliberately (re)generate the committed golden files from
golden_scenarios.py. Not part of the test suite - run manually:

    .venv/bin/python -m tests.narrate.regenerate_goldens

The committed goldens ARE the contract (design.md § Golden-file harness);
regenerating and hand-verifying is a deliberate act, not something a test
does automatically.
"""

import json
from pathlib import Path

from slidko.narrate.narrate import narrate
from tests.narrate.golden_scenarios import SCENARIOS

GOLDEN_DIR = Path(__file__).parent / "golden"


def main() -> None:
    GOLDEN_DIR.mkdir(exist_ok=True)
    for name, build_scenario in SCENARIOS.items():
        capture, events, findings, sidecar = build_scenario()
        assertions = narrate(capture, events, findings, sidecar=sidecar)
        data = [json.loads(a.to_json()) for a in assertions]
        path = GOLDEN_DIR / f"{name}.json"
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
        print(f"{name}: {len(assertions)} assertion(s) -> {path}")
        for assertion in assertions:
            print(f"  [{assertion.kind}] {assertion.text}")


if __name__ == "__main__":
    main()
