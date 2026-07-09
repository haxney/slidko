"""Thin subprocess wrapper around sigrok-cli for timed capture.

Never binds libsigrok in-process (docs/ARCHITECTURE.md § Sigrok posture).
The subprocess runner is injectable so no test needs a real sigrok-cli binary
or attached hardware.
"""

import subprocess
from collections.abc import Callable

Runner = Callable[[list[str]], "subprocess.CompletedProcess[str]"]


class CaptureError(Exception):
    """Base exception for sigrok-cli capture failures."""


class DeviceNotFound(CaptureError):  # noqa: N818 - name mandated by design.md
    """No matching capture device was found by sigrok-cli."""


class DriverError(CaptureError):
    """sigrok-cli reported a driver-level failure."""


_DEVICE_NOT_FOUND_MARKERS = ("no device", "no supported", "not found")


def build_capture_args(
    driver: str, samplerate_hz: int, duration_ms: int, output_path: str
) -> list[str]:
    """Construct the sigrok-cli argument list for a timed capture."""
    return [
        "sigrok-cli",
        "--driver",
        driver,
        "--config",
        f"samplerate={samplerate_hz}",
        "--time",
        f"{duration_ms}",
        "-O",
        "srzip",
        "-o",
        output_path,
    ]


def _default_runner(args: list[str]) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(args, capture_output=True, text=True, check=False)


def capture(
    driver: str,
    samplerate_hz: int,
    duration_ms: int,
    output_path: str,
    runner: Runner = _default_runner,
) -> None:
    """Run a timed sigrok-cli capture, raising a typed exception on failure."""
    args = build_capture_args(driver, samplerate_hz, duration_ms, output_path)
    result = runner(args)
    if result.returncode != 0:
        stderr = result.stderr or ""
        lowered = stderr.lower()
        if any(marker in lowered for marker in _DEVICE_NOT_FOUND_MARKERS):
            raise DeviceNotFound(stderr)
        raise DriverError(stderr)
