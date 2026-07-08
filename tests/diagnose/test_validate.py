from dataclasses import dataclass
from typing import Any

# Import from the actual module being tested
from slidko.diagnose.instruction import Instruction, validate_instruction


# Mock retrieval class for testing
@dataclass(frozen=True)
class MockRetrieval:
    board_id: str
    tier: str  # "open-book" | "pinout-only" | "dark"
    fragments: dict[str, str]  # "doc-id#anchor" -> content


def test_missing_expected_outcome_per_hypothesis_field():
    """A canned LLM output missing expected_outcome_per_hypothesis is rejected
    with a field-level validation error, not a construction-time TypeError.

    expected_outcome_per_hypothesis is Optional[...] = None at the dataclass
    level (House Decision 2), so a canned/raw dict missing it constructs
    fine; validate_instruction() is what reports the missing field.
    """
    canned_output: dict[str, Any] = {
        "action": "clip",
        "target": "TP7",
        "parameters": {},
        # expected_outcome_per_hypothesis deliberately omitted (defaults to None)
        "hazard_notes": "test hazard note",
        "executor": "human",
        "citations": [],
    }

    instruction = Instruction(**canned_output)
    mock_retrieval = MockRetrieval(
        board_id="test-board", tier="open-book", fragments={"doc1#anchor1": "content1"}
    )

    errors = validate_instruction(instruction, mock_retrieval)
    assert len(errors) > 0
    error_messages = [str(e) for e in errors]
    assert any("expected_outcome_per_hypothesis" in msg for msg in error_messages)


def test_pad_level_claim_without_citation_or_unknown_flag():
    """Test that pad-level claim without citation or unknown flag is rejected"""
    # Create pad-level instruction without citation or unknown flag
    instruction = Instruction(
        action="clip",
        target="TP7",
        parameters={"power_state": "off"},
        expected_outcome_per_hypothesis={"hyp1": "outcome1"},
        hazard_notes="test hazard note",
        executor="human",
        citations=[],  # No citation
        unknown=False,  # No unknown flag
    )

    # Mock retrieval - not dark board
    mock_retrieval = MockRetrieval(
        board_id="test-board", tier="open-book", fragments={"doc1#anchor1": "content1"}
    )

    # Try to validate - should return error for missing citation/unknown flag
    errors = validate_instruction(instruction, mock_retrieval)
    assert len(errors) > 0
    error_messages = [str(e) for e in errors]
    assert any(
        "Pad-level placement claim requires citation or unknown=True" in msg
        for msg in error_messages
    )


def test_dangling_citation():
    """Test that instruction with dangling citation is rejected"""
    # Create instruction with citation not in fragments
    instruction = Instruction(
        action="clip",
        target="TP7",
        parameters={"power_state": "off"},
        expected_outcome_per_hypothesis={"hyp1": "outcome1"},
        hazard_notes="test hazard note",
        executor="human",
        citations=["doc2#anchor2"],  # This citation does not exist in fragments
        unknown=False,
    )

    # Mock retrieval - no citation available
    mock_retrieval = MockRetrieval(
        board_id="test-board", tier="open-book", fragments={"doc1#anchor1": "content1"}
    )

    # Try to validate - should return error for dangling citation
    errors = validate_instruction(instruction, mock_retrieval)
    assert len(errors) > 0
    error_messages = [str(e) for e in errors]
    assert any("Dangling citation" in msg for msg in error_messages)


def test_empty_hazard_notes_on_placement_instruction():
    """Test that placement instruction with empty hazard notes is rejected"""
    # Create pad-level instruction with empty hazard notes
    instruction = Instruction(
        action="clip",
        target="TP7",
        parameters={"power_state": "off"},
        expected_outcome_per_hypothesis={"hyp1": "outcome1"},
        hazard_notes="",  # Empty hazard notes
        executor="human",
        citations=["doc1#anchor1"],
        unknown=False,
    )

    # Mock retrieval
    mock_retrieval = MockRetrieval(
        board_id="test-board", tier="open-book", fragments={"doc1#anchor1": "content1"}
    )

    # Try to validate - should return error for empty hazard notes
    errors = validate_instruction(instruction, mock_retrieval)
    assert len(errors) > 0
    error_messages = [str(e) for e in errors]
    assert any(
        "Pad-level placement claim requires non-empty hazard_notes" in msg
        for msg in error_messages
    )


def test_valid_instruction():
    """Test that a valid instruction passes validation"""
    # Create valid instruction
    instruction = Instruction(
        action="clip",
        target="TP7",
        parameters={"power_state": "off"},
        expected_outcome_per_hypothesis={"hyp1": "outcome1"},
        hazard_notes="test hazard note",
        executor="human",
        citations=["doc1#anchor1"],
        unknown=False,
    )

    # Mock retrieval
    mock_retrieval = MockRetrieval(
        board_id="test-board", tier="open-book", fragments={"doc1#anchor1": "content1"}
    )

    # Should not return any errors for valid instruction
    errors = validate_instruction(instruction, mock_retrieval)
    assert len(errors) == 0


def test_valid_ic_pin_with_accessibility_filter():
    """A pad-level claim with a fine-pitch IC pin on an unpowered board is
    still rejected, but only for missing citation (not accessibility)."""
    # A pad level claim should be rejected because citation is missing
    # The accessibility filter wouldn't trigger as it's not powered
    instruction = Instruction(
        action="probe",
        target="U3 pin 4",
        parameters={"power_state": "off", "pitch": 0.4},  # Fine pitch but powered off
        expected_outcome_per_hypothesis={"hyp1": "outcome1"},
        hazard_notes="test hazard note",
        executor="human",
        citations=[],  # No citation
        unknown=False,
    )

    # Mock retrieval
    mock_retrieval = MockRetrieval(
        board_id="test-board", tier="open-book", fragments={"doc1#anchor1": "content1"}
    )

    # Should fail because no citation, but NOT for accessibility (powered off)
    errors = validate_instruction(instruction, mock_retrieval)
    assert len(errors) > 0
    error_messages = [str(e) for e in errors]
    # Should be about missing citation, not accessibility
    assert any(
        "citation" in msg.lower() or "unknown" in msg.lower() for msg in error_messages
    )
    assert not any("Accessibility filter" in msg for msg in error_messages)
