"""Storage layout helpers for the corpus."""


def cell_dir(name: str) -> str:
    """Return the path to a cell directory."""
    return f"corpus/cells/{name}"


def entry_paths(cell: str, entry_id: str) -> tuple[str, str]:
    """Return the .sr and .json file paths for a given cell and entry id."""
    sr_path = f"{cell_dir(cell)}/{entry_id}.sr"
    json_path = f"{cell_dir(cell)}/{entry_id}.json"
    return (sr_path, json_path)


def field_gold_dir() -> str:
    """Return the path to the field-gold directory."""
    return "corpus/field-gold"
