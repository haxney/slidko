"""The poke-loop orchestrator (design.md § Fault-tree ordering, § LLM
boundary): symptom -> librarian -> instruction. Config-caused symptoms are
checked first and can short-circuit with no probe at all; only once the
fault tree has nothing left to say does the LLM get asked to propose a
physical probe instruction, and even then the validator - not the model -
is what a caller can trust.
"""

from typing import Any

from slidko.diagnose.config_pull import build_read_request
from slidko.diagnose.fault_tree import ConfigBranch, classify_symptom
from slidko.diagnose.instruction import (
    Instruction,
    ValidationError,
    validate_instruction,
)
from slidko.diagnose.llm import LLM
from slidko.librarian import Librarian
from slidko.narrate.model import Assertion


def diagnose(
    assertions: list[Assertion],
    librarian: Librarian,
    llm: LLM,
    board_id: str,
) -> Instruction:
    """Emit the next diagnostic instruction. Config-pull branches for a
    recognized symptom are tried before any probe: if the config value is
    already known (present in `assertions`) and explains the symptom, this
    short-circuits with a config-fix suggestion and no probe; if the
    symptom is recognized but the value isn't known yet, a config-pull
    instruction is emitted - still ahead of any probe. Only when neither
    applies does an LLM-proposed probe instruction get validated and
    returned.
    """
    retrieval = librarian.retrieve(board_id)
    assertion_texts = [a.text for a in assertions]

    symptom = classify_symptom(assertion_texts)
    if symptom is not None:
        for branch in symptom.config_branches:
            explaining = [a for a in assertions if branch.explains in a.text.lower()]
            if explaining:
                instruction = _config_fix_instruction(branch, explaining[0])
            else:
                instruction = _config_pull_instruction(branch)

            errors = validate_instruction(instruction, retrieval)
            if errors:
                raise ValidationError(
                    f"internally-constructed config instruction failed "
                    f"validation: {errors}"
                )
            return instruction

    context: dict[str, Any] = {
        "assertions": assertion_texts,
        "board_id": board_id,
        "tier": retrieval.tier,
        "citable_docs": sorted(retrieval.fragments),
    }
    proposal = llm.propose_instruction(context)
    instruction = Instruction(**proposal)

    errors = validate_instruction(instruction, retrieval)
    if errors:
        raise ValidationError(f"LLM-proposed instruction failed validation: {errors}")
    return instruction


def _config_pull_instruction(branch: ConfigBranch) -> Instruction:
    frame = build_read_request(branch.command)
    return Instruction(
        action="config_pull",
        target=branch.command.name,
        parameters={"frame_hex": frame.hex()},
        expected_outcome_per_hypothesis={
            "config_cause": (
                f"{branch.command.name} reveals whether this explains the symptom"
            )
        },
        hazard_notes="read-only MSP query; no risk to the board",
        executor="human",
        citations=[],
        unknown=False,
    )


def _config_fix_instruction(branch: ConfigBranch, evidence: Assertion) -> Instruction:
    return Instruction(
        action="config_fix",
        target=branch.command.name,
        parameters={"cited_evidence": evidence.text, "fix": branch.fix_suggestion},
        expected_outcome_per_hypothesis={"config_cause": branch.fix_suggestion},
        hazard_notes="",
        executor="human",
        citations=[],
        unknown=False,
    )
