"""Librarian: board-keyed pinout/connector document retrieval, exposed as
citable units addressable `doc-id#anchor` (design.md § Librarian retrieval).

v1 retrieval is fixture-backed and offline: a local corpus of doc fragments
under a fixtures dir, keyed by board id. Live network retrieval is a thin
real backend behind the same `Librarian` Protocol - not built in v1
(CLAUDE.md guardrail: no new hardware/network dependencies beyond what's
already scoped).
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

# Documentation tiers (docs/GLOSSARY.md): calibrates how much Diagnose can
# trust a pad-level citation for this board.
TIER_OPEN_BOOK = "open-book"
TIER_PINOUT_ONLY = "pinout-only"
TIER_DARK = "dark"


@dataclass(frozen=True)
class Retrieval:
    board_id: str
    tier: str  # "open-book" | "pinout-only" | "dark"
    fragments: dict[str, str]  # "doc-id#anchor" -> content


class Librarian(Protocol):
    def retrieve(self, board_id: str) -> Retrieval: ...


class FixtureLibrarian:
    """Offline Librarian backend: one JSON file per board under
    `fixtures_dir`, named `<board_id>.json` with `{tier, fragments}`.
    A board with no fixture file is `dark` with no fragments - unknown
    documentation is exactly what "dark" means, not an error."""

    def __init__(self, fixtures_dir: Path | str):
        self.fixtures_dir = Path(fixtures_dir)

    def retrieve(self, board_id: str) -> Retrieval:
        path = self.fixtures_dir / f"{board_id}.json"
        if not path.is_file():
            return Retrieval(board_id=board_id, tier=TIER_DARK, fragments={})

        data = json.loads(path.read_text(encoding="utf-8"))
        return Retrieval(
            board_id=board_id,
            tier=data.get("tier", TIER_DARK),
            fragments=data.get("fragments", {}),
        )
