"""One-motion labeled capture CLI.

Runs the instrument, prompts for the contemporaneous receiver verdict (the
gold label -- REQUIRED, refuses to write without it), and writes the raw
capture + sidecar in one motion so skipping the verdict is harder than
recording it (docs/CORPUS.md, design.md "One-motion capture CLI").
"""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from slidko.corpus.paths import entry_paths
from slidko.corpus.sidecar import Sidecar


class VerdictRequiredError(Exception):
    """Raised when no receiver verdict is supplied; nothing is written."""


def capture_entry(
    cell: str,
    entry_id: str,
    sidecar_fields: dict[str, Any],
    instrument_runner: Callable[[], bytes],
    verdict_provider: Callable[[], dict[str, Any] | None],
) -> tuple[Path, Path]:
    """Capture one entry: require a verdict, run the instrument, validate,
    then write `entry_paths(cell, entry_id)` cross-referenced by `id`.

    `sidecar_fields` supplies every sidecar field except `id`,
    `capture_file`, and `receiver_verdict`, which this function fills in.
    `instrument_runner`/`verdict_provider` are injected (real callers wire
    them to `slidko.capture.sigrokcli.capture` and an interactive prompt;
    tests inject mocks -- no hardware, no real stdin).

    Raises `VerdictRequiredError` (no files written) if `verdict_provider()`
    returns a falsy value -- the verdict prompt cannot be silently skipped.
    Raises `ValueError` (no files written) if the assembled sidecar fails
    `Sidecar.validate`.
    """
    verdict = verdict_provider()
    if not verdict:
        raise VerdictRequiredError(
            "receiver_verdict is required; refusing to write an unlabeled entry"
        )

    sidecar_json = {
        **sidecar_fields,
        "id": f"{cell}/{entry_id}",
        "capture_file": f"{entry_id}.sr",
        "receiver_verdict": verdict,
    }
    sidecar = Sidecar.from_json(sidecar_json)
    errors = Sidecar.validate(sidecar)
    if errors:
        raise ValueError(f"sidecar failed validation: {errors}")

    # Instrument runs only after validation passes, so a doomed capture
    # never touches real hardware/subprocess time.
    sr_bytes = instrument_runner()

    sr_path_str, json_path_str = entry_paths(cell, entry_id)
    sr_path = Path(sr_path_str)
    json_path = Path(json_path_str)
    sr_path.parent.mkdir(parents=True, exist_ok=True)
    sr_path.write_bytes(sr_bytes)
    json_path.write_text(json.dumps(sidecar.to_json(), indent=2), encoding="utf-8")

    return sr_path, json_path


def main() -> None:
    """Console entry point.

    Wiring a real interactive session (cell selection, instrument config,
    stdin verdict prompt) needs a session-config format design.md doesn't
    specify yet -- deferred. The tested, load-bearing logic is
    `capture_entry` above; real callers (or a future CLI) supply the
    instrument_runner/verdict_provider closures.
    """
    raise SystemExit(
        "corpus capture CLI: interactive session wiring not yet implemented; "
        "use capture_entry() directly with injected instrument_runner/verdict_provider"
    )


if __name__ == "__main__":
    main()
