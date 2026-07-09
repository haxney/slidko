"""Sigrok decoder version pinning + drift detection (design.md § Version
pinning).

The sigrok decoder corpus is an asset we wrap, not code we own; pin it and
alarm loudly when the installed decoders drift from what the manifest was
generated against. Only the decoders Decode actually uses are hashed, so
unrelated upstream churn can't trigger a false alarm.
"""

import hashlib
import json
import os
from pathlib import Path

USED_DECODERS = ("uart", "i2c", "spi")
DECODER_SOURCE_FILES = ("pd.py", "__init__.py")

DEFAULT_DECODER_DIR = "/usr/share/libsigrokdecode/decoders/"
DECODER_DIR_ENV_VAR = "SLIDKO_DECODER_DIR"

MANIFEST_PATH = Path(__file__).parent / "decoder_manifest.json"


def decoder_dir() -> Path:
    """Resolve the libsigrokdecode decoder directory: env override, else the
    Debian/Ubuntu default."""
    return Path(os.environ.get(DECODER_DIR_ENV_VAR, DEFAULT_DECODER_DIR))


def hash_decoder(base_dir: Path, name: str) -> str:
    """sha256 over the concatenated contents of a decoder's source files
    (pd.py + __init__.py), in a fixed order so the hash is reproducible."""
    digest = hashlib.sha256()
    for filename in DECODER_SOURCE_FILES:
        digest.update((base_dir / name / filename).read_bytes())
    return digest.hexdigest()


def build_manifest(
    base_dir: Path, decoder_names: tuple[str, ...] = USED_DECODERS
) -> dict[str, str]:
    """Hash each used decoder under `base_dir` into a name -> sha256 manifest."""
    return {name: hash_decoder(base_dir, name) for name in decoder_names}


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, str]:
    manifest: dict[str, str] = json.loads(path.read_text(encoding="utf-8"))
    return manifest


def save_manifest(manifest: dict[str, str], path: Path = MANIFEST_PATH) -> None:
    path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def check_drift(base_dir: Path, manifest: dict[str, str]) -> list[str]:
    """Return the names of decoders whose installed hash no longer matches
    the manifest (including decoders the manifest expects but that are now
    missing)."""
    drifted = []
    for name, expected_hash in manifest.items():
        try:
            actual_hash = hash_decoder(base_dir, name)
        except FileNotFoundError:
            drifted.append(name)
            continue
        if actual_hash != expected_hash:
            drifted.append(name)
    return drifted
