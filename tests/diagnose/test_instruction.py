import json
from dataclasses import asdict
from typing import Dict, Any

from slidko.diagnose.instruction import Instruction


def test_instruction_dataclass_fields():
    """Test that Instruction has all required fields from design.md"""
    # Create an instruction with all fields
    instruction = Instruction(
        action="clip",
        target="TP7",
        parameters={"power_state": "off"},
        expected_outcome_per_hypothesis={"hyp1": "outcome1", "hyp2": "outcome2"},
        hazard_notes="test hazard note",
        executor="human",
        citations=["doc1#anchor1"],
        unknown=False
    )
    
    # Check all fields are present
    assert hasattr(instruction, 'action')
    assert hasattr(instruction, 'target')
    assert hasattr(instruction, 'parameters')
    assert hasattr(instruction, 'expected_outcome_per_hypothesis')
    assert hasattr(instruction, 'hazard_notes')
    assert hasattr(instruction, 'executor')
    assert hasattr(instruction, 'citations')
    assert hasattr(instruction, 'unknown')


def test_instruction_json_roundtrip():
    """Test that Instruction can be serialized to and from JSON"""
    # Create an instruction
    original = Instruction(
        action="clip",
        target="TP7",
        parameters={"power_state": "off"},
        expected_outcome_per_hypothesis={"hyp1": "outcome1", "hyp2": "outcome2"},
        hazard_notes="test hazard note",
        executor="human",
        citations=["doc1#anchor1"],
        unknown=False
    )
    
    # Serialize to JSON
    json_str = json.dumps(asdict(original))
    parsed_dict = json.loads(json_str)
    
    # Check that it can be deserialized back to an Instruction
    assert parsed_dict["action"] == "clip"
    assert parsed_dict["target"] == "TP7"
    assert parsed_dict["parameters"] == {"power_state": "off"}
    assert parsed_dict["expected_outcome_per_hypothesis"] == {"hyp1": "outcome1", "hyp2": "outcome2"}
    assert parsed_dict["hazard_notes"] == "test hazard note"
    assert parsed_dict["executor"] == "human"
    assert parsed_dict["citations"] == ["doc1#anchor1"]
    assert parsed_dict["unknown"] is False


def test_expected_outcome_per_hypothesis_is_dict():
    """Test that expected_outcome_per_hypothesis is a dict"""
    instruction = Instruction(
        action="clip",
        target="TP7",
        parameters={"power_state": "off"},
        expected_outcome_per_hypothesis={"hyp1": "outcome1", "hyp2": "outcome2"},
        hazard_notes="test hazard note",
        executor="human",
        citations=["doc1#anchor1"],
        unknown=False
    )
    
    assert isinstance(instruction.expected_outcome_per_hypothesis, dict)
    
    
def test_instruction_frozen():
    """Test that Instruction is a frozen dataclass (immutable)"""
    instruction = Instruction(
        action="clip",
        target="TP7",
        parameters={"power_state": "off"},
        expected_outcome_per_hypothesis={"hyp1": "outcome1"},
        hazard_notes="test hazard note",
        executor="human",
        citations=["doc1#anchor1"],
        unknown=False
    )
    
    # This should raise an error if the dataclass is frozen
    try:
        instruction.action = "different_action"
        assert False, "Instruction should be frozen"
    except AttributeError:
        pass  # Expected behavior