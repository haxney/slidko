import unittest

from slidko.narrate.address_book import get_address_book, lookup

# Test the I²C address book lookup functionality


class TestAddressBook(unittest.TestCase):
    def test_lookup_0x68_returns_candidates(self):
        """lookup of 0x68 returns a NON-empty candidate list including an IMU part"""
        candidates = lookup(0x68)
        assert candidates is not None
        assert len(candidates) > 0

        # Should include at least one IMU part
        imu_parts = [c for c in candidates if "IMU" in c.get("kind", "")]
        assert len(imu_parts) > 0

    def test_lookup_unknown_address_returns_empty_list(self):
        """an unknown address returns an empty list (not an error)"""
        result = lookup(0xFF)  # An address not in our book
        assert isinstance(result, list)
        assert len(result) == 0

    def test_lookup_never_returns_single_forced_identification(self):
        """lookups never return a single forced identification"""
        candidates = lookup(0x68)
        # Should return a list of candidates, not a single identification
        assert isinstance(candidates, list)
        # The list should contain dictionaries with part info, not just one thing
        for candidate in candidates:
            assert isinstance(candidate, dict)
            assert "part" in candidate
            assert "kind" in candidate

    def test_address_book_is_data_shaped(self):
        """Test that the book is data-shaped (a dict/JSON, no branching logic)"""
        book = get_address_book()
        # Should be a dictionary
        assert isinstance(book, dict)

        # All values should be lists of dictionaries
        for candidates in book.values():
            assert isinstance(candidates, list)
            for candidate in candidates:
                assert isinstance(candidate, dict)
                assert "part" in candidate
                assert "kind" in candidate
                assert "note" in candidate


if __name__ == "__main__":
    unittest.main()
