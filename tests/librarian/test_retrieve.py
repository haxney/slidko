"""
Librarian retrieval (design.md § Librarian retrieval, task group 4):
fixture-backed, offline. Retrieving a known board id returns a Retrieval
with tier and fragments mapping stable doc-id#anchor keys to content; a
citation present in fragments resolves, an absent one does not.
"""

from pathlib import Path

import pytest

from slidko.librarian import FixtureLibrarian, Retrieval

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_retrieve_known_board_returns_tier_and_fragments():
    librarian = FixtureLibrarian(FIXTURES_DIR)

    retrieval = librarian.retrieve("matek-f405-wing")

    assert isinstance(retrieval, Retrieval)
    assert retrieval.board_id == "matek-f405-wing"
    assert retrieval.tier == "open-book"
    assert retrieval.fragments  # non-empty


def test_citation_present_in_fragments_resolves():
    librarian = FixtureLibrarian(FIXTURES_DIR)
    retrieval = librarian.retrieve("matek-f405-wing")

    assert "pinout.md#uart1" in retrieval.fragments
    assert "PA9" in retrieval.fragments["pinout.md#uart1"]


def test_citation_absent_from_fragments_does_not_resolve():
    librarian = FixtureLibrarian(FIXTURES_DIR)
    retrieval = librarian.retrieve("matek-f405-wing")

    assert "pinout.md#nonexistent-anchor" not in retrieval.fragments


def test_fragment_keys_are_stable_doc_id_anchor_format():
    """Every fragment key is a stable "doc-id#anchor" citation unit."""
    librarian = FixtureLibrarian(FIXTURES_DIR)
    retrieval = librarian.retrieve("matek-f405-wing")

    for key in retrieval.fragments:
        assert "#" in key
        doc_id, anchor = key.split("#", 1)
        assert doc_id
        assert anchor


def test_pinout_only_tier_board():
    librarian = FixtureLibrarian(FIXTURES_DIR)

    retrieval = librarian.retrieve("generic-fc")

    assert retrieval.tier == "pinout-only"
    assert retrieval.fragments


def test_explicit_dark_tier_fixture():
    librarian = FixtureLibrarian(FIXTURES_DIR)

    retrieval = librarian.retrieve("unknown-clone-board")

    assert retrieval.tier == "dark"
    assert retrieval.fragments == {}


def test_unknown_board_id_defaults_to_dark_not_an_error():
    """A board with no fixture file at all is dark with no fragments -
    unknown documentation, not an exception."""
    librarian = FixtureLibrarian(FIXTURES_DIR)

    retrieval = librarian.retrieve("some-board-nobody-documented")

    assert retrieval.tier == "dark"
    assert retrieval.fragments == {}


if __name__ == "__main__":
    pytest.main([__file__])
