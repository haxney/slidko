import re
import sys

import slidko
import slidko.capture
import slidko.corpus
import slidko.decode
import slidko.diagnose
import slidko.librarian
import slidko.measure
import slidko.narrate


def test_version_format():
    """Test that version matches X.Y.Z pattern."""
    assert re.match(r"^\d+\.\d+\.\d+$", slidko.__version__)


def test_subpackages_importable():
    """Test that all subpackages can be imported without side effects."""
    # This test just verifies that we can import all the modules
    # No actual functionality is being tested here
    assert sys.modules["slidko"] is slidko
    assert sys.modules["slidko.capture"] is slidko.capture
    assert sys.modules["slidko.measure"] is slidko.measure
    assert sys.modules["slidko.decode"] is slidko.decode
    assert sys.modules["slidko.narrate"] is slidko.narrate
    assert sys.modules["slidko.diagnose"] is slidko.diagnose
    assert sys.modules["slidko.librarian"] is slidko.librarian
    assert sys.modules["slidko.corpus"] is slidko.corpus
