from dataclasses import dataclass
from typing import Protocol

# Minimum pin pitch (mm) that triggers the accessibility filter on a powered
# board (ARCHITECTURE.md: never needle-probe fine-pitch (<= 0.5mm) IC pads).
MIN_PITCH_FOR_ACCESSIBILITY_MM = 0.5


class RetrievalLike(Protocol):
    """Structural shape validate_instruction needs from a librarian Retrieval.

    The librarian module itself (phase-5-diagnose-loop) is not built yet;
    this Protocol covers only what this module accesses, so it stays
    accurate without depending on unbuilt code.
    """

    @property
    def fragments(self) -> dict[str, str]: ...


@dataclass(frozen=True)
class Instruction:
    action: str
    target: str
    parameters: dict
    hazard_notes: str
    executor: str  # "human" | "exerciser"
    citations: list[str]  # ["doc-id#anchor", ...]
    expected_outcome_per_hypothesis: dict[str, str] | None = (
        None  # one entry per live hyp
    )
    unknown: bool = False  # explicit "I don't know where" flag


class ValidationError(Exception):
    """Raised when validation fails"""


def _is_ic_pin(target: str) -> bool:
    """
    Determine if target refers to an IC pin.

    This is a simple check for strings containing "pin" that are likely IC pins.

    Returns:
        bool: True if this looks like an IC pin
    """
    # Simple check - targets with format like "U3 pin 4" typically indicate IC pins
    return " pin " in target.lower()


def is_pad_level_claim(instruction: Instruction) -> bool:
    """
    Determine if instruction is a pad-level placement claim.

    A pad-level placement claim places a probe/clip on a specific physical
    point identified by pad/pin/test-point (e.g. action="clip", target="TP7"
    or target="U3 pin 4").

    Returns:
        bool: True if this is a pad-level claim
    """
    # Any instruction with action that involves clipping/placing on something
    # that could be a physical point, such as pad/pin/test-point is a pad-level claim

    # Actions that indicate placing/interacting with a physical point
    pad_level_actions = {"clip", "probe", "measure", "connect"}

    # If no action given or it's not a pad level action, it's not a pad level claim
    if not instruction.action:
        return False

    return instruction.action in pad_level_actions


def validate_instruction(
    instruction: Instruction, retrieval: RetrievalLike
) -> list[ValidationError]:
    """
    Validate instruction against schema rules.

    Args:
        instruction: Instruction to validate
        retrieval: Retrieval object with board tier and fragments information

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Rule 2: Check pad-level claims for citations or unknown flag
    if is_pad_level_claim(instruction):
        # Pad level instruction needs either citation or unknown flag
        if not instruction.unknown and not instruction.citations:
            errors.append(
                ValidationError(
                    "Pad-level placement claim requires citation or unknown=True"
                )
            )

        # If there are citations, check that they resolve
        if instruction.citations and not instruction.unknown:
            for citation in instruction.citations:
                # Check the citation resolves to something in retrieval fragments
                if citation not in retrieval.fragments:
                    errors.append(ValidationError(f"Dangling citation: {citation}"))

    # Rule 5: Empty hazard notes on pad-level placement instructions
    if is_pad_level_claim(instruction) and not instruction.hazard_notes:
        errors.append(
            ValidationError("Pad-level placement claim requires non-empty hazard_notes")
        )

    # Rule 6: Executor must be valid
    if instruction.executor not in {"human", "exerciser"}:
        errors.append(ValidationError("Executor must be 'human' or 'exerciser'"))

    # Accessibility filter (Rule 4 from design): fine-pitch IC pins on
    # powered boards are rejected.
    if is_pad_level_claim(instruction):
        power_state = instruction.parameters.get("power_state", "off").lower()
        pitch = instruction.parameters.get("pitch", None)

        # Target looks like an IC pin, fine pitch, board is powered.
        if (
            _is_ic_pin(instruction.target)
            and power_state == "on"
            and pitch is not None
            and pitch < MIN_PITCH_FOR_ACCESSIBILITY_MM
        ):
            errors.append(
                ValidationError(
                    f"Accessibility filter: Fine pitch IC pin ({pitch}mm) on "
                    "powered board not allowed"
                )
            )

    return errors
