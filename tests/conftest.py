import shutil
import subprocess
from pathlib import Path

import pytest

_DEMO_FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "generated" / "sigrok-demo-capture.sr"
)


@pytest.fixture
def demo_capture() -> Path:
    """Path to a real sigrok-cli demo-driver .sr capture, generated on demand.

    Regenerable and gitignored (tests/fixtures/generated/). Skips cleanly when
    sigrok-cli is not installed rather than failing the suite.
    """
    if not _DEMO_FIXTURE_PATH.exists():
        if shutil.which("sigrok-cli") is None:
            pytest.skip("sigrok-cli is not installed; skipping real-file validation")
        _DEMO_FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [
                "sigrok-cli",
                "--driver",
                "demo",
                "--config",
                "samplerate=24000000",
                "--time",
                "10",
                "-O",
                "srzip",
                "-o",
                str(_DEMO_FIXTURE_PATH),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            pytest.skip(f"sigrok-cli demo capture failed, skipping: {result.stderr}")
    return _DEMO_FIXTURE_PATH
