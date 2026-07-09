"""
Decoder pinning + drift detection (design.md § Version pinning). Loads the
committed manifest and asserts the installed uart/i2c/spi decoders match;
skips cleanly when the decoder directory isn't present on this machine.
"""

import json

import pytest

from slidko.decode.decoder_pin import (
    MANIFEST_PATH,
    USED_DECODERS,
    build_manifest,
    check_drift,
    decoder_dir,
    load_manifest,
)

pytestmark = pytest.mark.skipif(
    not decoder_dir().is_dir(), reason="libsigrokdecode decoder directory not present"
)


def test_manifest_matches_installed_decoders():
    manifest = load_manifest()
    assert set(manifest) == set(USED_DECODERS)

    drifted = check_drift(decoder_dir(), manifest)
    assert drifted == [], f"decoder(s) drifted from pinned manifest: {drifted}"


def test_drift_is_detected_and_named(tmp_path):
    manifest = load_manifest()
    perturbed = dict(manifest)
    perturbed["uart"] = "0" * len(perturbed["uart"])

    perturbed_path = tmp_path / "manifest.json"
    perturbed_path.write_text(json.dumps(perturbed))

    drifted = check_drift(decoder_dir(), load_manifest(perturbed_path))
    assert drifted == ["uart"]


def test_build_manifest_reproduces_committed_manifest():
    """The committed manifest is exactly what build_manifest() produces
    against the decoders installed on this machine right now."""
    assert build_manifest(decoder_dir()) == load_manifest(MANIFEST_PATH)


if __name__ == "__main__":
    pytest.main([__file__])
