"""Read and write sigrok session (.sr) files.

A .sr file is a zip container holding a configparser-format ``metadata``
member and one or more packed binary ``logic-1-<n>`` chunk files. Each sample
is ``unitsize`` bytes wide; within a sample, bit *i* (LSB first) carries the
value of the *(i+1)*-th probe. Chunks are concatenated in numeric order to
reconstruct the full packed sample stream (sigrok splits large captures into
multiple chunk files with no per-chunk framing).

Real sigrok-cli output also interleaves ``analog-1-<ch>-<n>`` chunks in the
same zip; the reader selects strictly by the ``logic-1-`` prefix and ignores
everything else (see tests/fixtures/README.md).
"""

import configparser
import re
import zipfile

import numpy as np

from slidko.capture import Capture

_LOGIC_CHUNK_RE = re.compile(r"^logic-1-(\d+)$")
_SAMPLERATE_RE = re.compile(
    r"^\s*([0-9.]+)\s*([kKmMgG]?)Hz\s*$",
)
_SAMPLERATE_SCALE = {"": 1, "k": 1_000, "m": 1_000_000, "g": 1_000_000_000}


def _parse_samplerate(raw: str) -> int:
    """Parse a metadata samplerate: plain Hz integers or '24 MHz'-style strings."""
    match = _SAMPLERATE_RE.match(raw)
    if match:
        value, prefix = match.groups()
        return int(float(value) * _SAMPLERATE_SCALE[prefix.lower()])
    return int(raw)


def write_sr(capture: Capture, filepath: str, chunk_size: int | None = None) -> None:
    """Write a Capture to a .sr file.

    ``chunk_size`` optionally caps the number of packed sample bytes per
    ``logic-1-<n>`` chunk, splitting the stream across multiple chunks.
    """
    channel_names = list(capture.channels)
    n_channels = len(channel_names)
    n_samples = len(next(iter(capture.channels.values()))) if channel_names else 0

    metadata = configparser.ConfigParser()
    metadata.optionxform = str  # type: ignore[assignment]
    metadata["device 1"] = {
        "capturefile": "logic-1",
        "total probes": str(n_channels),
        "samplerate": str(capture.samplerate_hz),
        "unitsize": "1",
    }
    for i, name in enumerate(channel_names, start=1):
        metadata["device 1"][f"probe{i}"] = name
    instrument = capture.provenance.get("instrument")
    if instrument is not None:
        metadata["device 1"]["instrument"] = str(instrument)
    threshold_v = capture.provenance.get("threshold_v")
    if threshold_v is not None:
        metadata["device 1"]["threshold_v"] = str(threshold_v)

    metadata_str = ""
    for section in metadata.sections():
        metadata_str += f"[{section}]\n"
        for key, value in metadata[section].items():
            metadata_str += f"{key}={value}\n"

    if n_channels == 0 or n_samples == 0:
        packed_bytes = b""
    else:
        bits = np.zeros((n_samples, 8), dtype=np.uint8)
        for col, name in enumerate(channel_names):
            bits[:, col] = np.asarray(capture.channels[name], dtype=bool)
        packed_bytes = np.packbits(bits, axis=1, bitorder="little").tobytes()

    with zipfile.ZipFile(filepath, "w", compression=zipfile.ZIP_STORED) as zf:
        zf.writestr("metadata", metadata_str)
        step = chunk_size if chunk_size else max(len(packed_bytes), 1)
        chunk_index = 1
        offset = 0
        while offset < len(packed_bytes):
            zf.writestr(f"logic-1-{chunk_index}", packed_bytes[offset : offset + step])
            offset += step
            chunk_index += 1
        if not packed_bytes:
            zf.writestr("logic-1-1", b"")


def read_sr(filepath: str) -> Capture:
    """Read a .sr file into a Capture object."""
    with zipfile.ZipFile(filepath, "r") as zf:
        metadata_str = zf.read("metadata").decode("utf-8")
        metadata = configparser.ConfigParser()
        metadata.optionxform = str  # type: ignore[assignment]
        metadata.read_string(metadata_str)
        device = metadata["device 1"]

        samplerate_hz = _parse_samplerate(device["samplerate"])
        n_channels = int(device["total probes"])
        unitsize = int(device.get("unitsize", "1"))
        channel_names = [
            device.get(f"probe{i}", f"ch{i}") for i in range(1, n_channels + 1)
        ]

        chunk_names = sorted(
            (n for n in zf.namelist() if _LOGIC_CHUNK_RE.match(n)),
            key=lambda n: int(_LOGIC_CHUNK_RE.match(n).group(1)),  # type: ignore[union-attr]
        )
        packed_bytes = b"".join(zf.read(name) for name in chunk_names)

        if packed_bytes:
            flat = np.frombuffer(packed_bytes, dtype=np.uint8)
            n_samples = len(flat) // unitsize
            packed = flat[: n_samples * unitsize].reshape(n_samples, unitsize)
            bits = np.unpackbits(packed, axis=1, bitorder="little")
            channels = {
                name: bits[:, i].astype(bool) for i, name in enumerate(channel_names)
            }
        else:
            channels = {name: np.zeros(0, dtype=bool) for name in channel_names}

        provenance = {
            "instrument": device.get("instrument", fallback=None),
            "samplerate_hz": samplerate_hz,
            "threshold_v": (
                float(device["threshold_v"]) if "threshold_v" in device else None
            ),
        }

    return Capture(
        channels=channels, samplerate_hz=samplerate_hz, provenance=provenance
    )
