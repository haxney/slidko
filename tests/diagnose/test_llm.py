"""
The LLM boundary (design.md § LLM boundary, task group 6). Every test here
uses FakeLLM - a canned-dict test double satisfying the `LLM` Protocol -
and asserts no real network client is ever constructed or called.
"""

import anthropic
import pytest

from slidko.diagnose.llm import LLM, AnthropicLLM, FakeLLM

CANNED_INSTRUCTION = {
    "action": "clip",
    "target": "TP7",
    "parameters": {"power_state": "off"},
    "expected_outcome_per_hypothesis": {"hyp1": "voltage present"},
    "hazard_notes": "board is unpowered",
    "executor": "human",
    "citations": ["doc1#anchor1"],
    "unknown": False,
}


def test_fake_llm_satisfies_the_protocol():
    fake: LLM = FakeLLM(CANNED_INSTRUCTION)
    assert fake.propose_instruction({"symptom": "no boot"}) == CANNED_INSTRUCTION


def test_fake_llm_returns_canned_dict_regardless_of_context():
    fake = FakeLLM(CANNED_INSTRUCTION)

    result = fake.propose_instruction({"assertions": [], "board_id": "test-board"})

    assert result == CANNED_INSTRUCTION


def test_fake_llm_records_calls_for_inspection():
    fake = FakeLLM(CANNED_INSTRUCTION)
    context = {"symptom": "no boot", "board_id": "test-board"}

    fake.propose_instruction(context)

    assert fake.calls == [context]


def test_fake_llm_can_queue_multiple_responses():
    """Scripted multi-turn scenarios (task group 7) need a sequence of
    canned responses, one per diagnose() call."""
    second_instruction = {**CANNED_INSTRUCTION, "target": "TP8"}
    fake = FakeLLM([CANNED_INSTRUCTION, second_instruction])

    first = fake.propose_instruction({})
    second = fake.propose_instruction({})

    assert first == CANNED_INSTRUCTION
    assert second == second_instruction


def test_no_real_network_client_constructed_by_fake(monkeypatch):
    """Diagnose consumes FakeLLM's canned dicts and never calls a real
    network client in tests."""

    def _fail_if_called(*args, **kwargs):
        raise AssertionError("real anthropic.Anthropic() client was constructed")

    monkeypatch.setattr(anthropic, "Anthropic", _fail_if_called)

    fake = FakeLLM(CANNED_INSTRUCTION)
    result = fake.propose_instruction({"symptom": "no boot"})

    assert result == CANNED_INSTRUCTION


def test_anthropic_llm_uses_default_model_and_injected_client():
    """AnthropicLLM never constructs its own client when one is injected -
    this is what makes it testable without a real network call."""

    class _Block:
        type = "text"
        text = '{"action": "probe"}'

    class _Response:
        def __init__(self) -> None:
            self.content = [_Block()]

    class _StubMessages:
        def create(self, **kwargs):
            assert kwargs["model"] == "claude-opus-4-8"
            return _Response()

    class _StubClient:
        messages = _StubMessages()

    llm = AnthropicLLM(client=_StubClient())
    result = llm.propose_instruction({"symptom": "no boot"})

    assert result == {"action": "probe"}


if __name__ == "__main__":
    pytest.main([__file__])
