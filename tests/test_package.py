import re
from importlib import import_module

import slidko


def test_version():
    """Assert that the version matches the X.Y.Z pattern."""
    # Check that it's a valid version string (X.Y.Z format)
    assert re.match(r"^\d+\.\d+\.\d+$", slidko.__version__), (
        f"Version {slidko.__version__} doesn't match X.Y.Z pattern"
    )


def test_package_imports():
    """Assert all subpackages can be imported."""
    # Test that we can import all subpackages
    subpackages = [
        "capture",
        "measure",
        "decode",
        "narrate",
        "diagnose",
        "librarian",
        "corpus",
    ]

    for pkg in subpackages:
        imported = import_module(f"slidko.{pkg}")
        assert imported is not None, f"Could not import slidko.{pkg}"
