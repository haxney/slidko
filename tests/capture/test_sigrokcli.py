import subprocess
from unittest.mock import MagicMock

import pytest

from slidko.capture.sigrokcli import (
    DeviceNotFound,
    DriverError,
    build_capture_args,
    capture,
)


def test_build_capture_args_contains_driver_samplerate_time_output():
    """Argument-list construction from parameters, verified without executing
    sigrok-cli."""
    args = build_capture_args(
        driver="fx2lafw",
        samplerate_hz=24_000_000,
        duration_ms=500,
        output_path="/tmp/out.sr",
    )

    assert "sigrok-cli" in args
    assert "--driver" in args
    assert args[args.index("--driver") + 1] == "fx2lafw"
    assert "--config" in args
    assert args[args.index("--config") + 1] == "samplerate=24000000"
    assert "--time" in args
    assert args[args.index("--time") + 1] == "500"
    assert "-o" in args
    assert args[args.index("-o") + 1] == "/tmp/out.sr"


def _mock_result(returncode: int, stderr: str = "") -> MagicMock:
    result = MagicMock(spec=subprocess.CompletedProcess)
    result.returncode = returncode
    result.stderr = stderr
    return result


def test_capture_success_does_not_raise():
    runner = MagicMock(return_value=_mock_result(0))
    capture(
        driver="fx2lafw",
        samplerate_hz=24_000_000,
        duration_ms=500,
        output_path="/tmp/out.sr",
        runner=runner,
    )
    runner.assert_called_once()


def test_capture_no_device_raises_device_not_found_with_stderr():
    stderr = "sigrok-cli: No device found."
    runner = MagicMock(return_value=_mock_result(1, stderr))

    with pytest.raises(DeviceNotFound) as exc_info:
        capture(
            driver="fx2lafw",
            samplerate_hz=24_000_000,
            duration_ms=500,
            output_path="/tmp/out.sr",
            runner=runner,
        )
    assert stderr in str(exc_info.value)


def test_capture_generic_driver_failure_raises_driver_error_with_stderr():
    stderr = "sigrok-cli: Failed to configure device."
    runner = MagicMock(return_value=_mock_result(1, stderr))

    with pytest.raises(DriverError) as exc_info:
        capture(
            driver="fx2lafw",
            samplerate_hz=24_000_000,
            duration_ms=500,
            output_path="/tmp/out.sr",
            runner=runner,
        )
    assert stderr in str(exc_info.value)
