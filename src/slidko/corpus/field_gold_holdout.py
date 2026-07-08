"""Field-gold holdout enforcement.

This module implements a guard that scans source files for references to
field-gold/ outside of an allowlist, failing the build if any are found.
"""

import os

# Allowlist of files that are permitted to reference field-gold/
ALLOWLIST = [
    "corpus/paths.py",  # The loader itself
    "tests/corpus/test_field_gold_holdout.py",  # This guard test
]


def scan_for_field_gold_references() -> list[str]:
    """Scan Python files for literal references to 'field-gold' outside the allowlist.

    Returns:
        List of file paths that contain forbidden references
    """
    forbidden_files = []

    # Get all .py files in src/ and tests/ directories
    source_dirs = ["src", "tests"]

    for source_dir in source_dirs:
        if not os.path.exists(source_dir):
            continue

        for root, _, files in os.walk(source_dir):
            for filename in files:
                if filename.endswith(".py"):
                    filepath = os.path.join(root, filename)

                    # Skip allowlisted files
                    relative_path = os.path.relpath(filepath)
                    if relative_path in ALLOWLIST:
                        continue

                    # Check if the file contains "field-gold"
                    with open(filepath, encoding="utf-8") as f:
                        content = f.read()

                        # Look for literal "field-gold" references
                        if r"field-gold" in content:
                            forbidden_files.append(relative_path)

    return forbidden_files


def check_field_gold_references() -> bool:
    """Check that no unauthorized references to field-gold exist.

    Returns:
        True if all checks pass, False if forbidden references found
    """
    forbidden_files = scan_for_field_gold_references()

    if forbidden_files:
        print("ERROR: Found forbidden references to 'field-gold' in:")
        for filepath in forbidden_files:
            print(f"  {filepath}")
        return False

    return True
