"""The LLM boundary (design.md § LLM boundary): a narrow Protocol wrapping
the Anthropic SDK. This is the ONLY module in the diagnose loop that talks
to a real model - everything else (schema validation, citation enforcement,
accessibility filter, fault-tree ordering) is deterministic and testable
without it. Tests inject a fake; the real client is never called in CI.
"""

import json
from typing import Any, Protocol

import anthropic

# Per the project's model guidance (claude-api skill): default to the
# current Opus-tier model unless the caller names a different one. Do NOT
# hardcode a deprecated/retired model id here.
DEFAULT_MODEL = "claude-opus-4-8"


class LLM(Protocol):
    def propose_instruction(self, context: dict[str, Any]) -> dict[str, Any]: ...


class AnthropicLLM:
    """Real Anthropic-backed implementation. Never constructed in tests -
    the fake below satisfies the same Protocol for offline testing."""

    def __init__(self, model: str = DEFAULT_MODEL, client: Any = None) -> None:
        self.model = model
        self.client: Any = client if client is not None else anthropic.Anthropic()

    def propose_instruction(self, context: dict[str, Any]) -> dict[str, Any]:
        """Ask Claude for a next-instruction proposal given the diagnostic
        context (assertions, retrieval, symptom). Returns the raw parsed
        dict - schema validation happens downstream in validate_instruction,
        never here."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            output_config={
                "format": {
                    "type": "json_schema",
                    "schema": _INSTRUCTION_PROPOSAL_SCHEMA,
                }
            },
            messages=[{"role": "user", "content": _render_context(context)}],
        )
        text = next(block.text for block in response.content if block.type == "text")
        result: dict[str, Any] = json.loads(text)
        return result


class FakeLLM:
    """Test double satisfying the LLM Protocol: returns a canned dict (or
    a queue of them) with no network call whatsoever."""

    def __init__(self, canned: dict[str, Any] | list[dict[str, Any]]) -> None:
        self._queue: list[dict[str, Any]] = (
            list(canned) if isinstance(canned, list) else [canned]
        )
        self.calls: list[dict[str, Any]] = []

    def propose_instruction(self, context: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(context)
        if len(self._queue) > 1:
            return self._queue.pop(0)
        return self._queue[0]


_INSTRUCTION_PROPOSAL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "action": {"type": "string"},
        "target": {"type": "string"},
        "parameters": {"type": "object"},
        "expected_outcome_per_hypothesis": {"type": "object"},
        "hazard_notes": {"type": "string"},
        "executor": {"type": "string", "enum": ["human", "exerciser"]},
        "citations": {"type": "array", "items": {"type": "string"}},
        "unknown": {"type": "boolean"},
    },
    "required": [
        "action",
        "target",
        "parameters",
        "expected_outcome_per_hypothesis",
        "hazard_notes",
        "executor",
        "citations",
    ],
    "additionalProperties": False,
}


def _render_context(context: dict[str, Any]) -> str:
    return json.dumps(context)
