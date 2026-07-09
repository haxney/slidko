"""
Fault-tree ordering + the loop orchestrator (design.md § Fault-tree
ordering, task group 7): config-caused symptoms are checked before any
probe, using a fake LLM so the routing decision is testable offline.
"""

from pathlib import Path

import pytest

from slidko.diagnose.diagnose import diagnose
from slidko.diagnose.instruction import validate_instruction
from slidko.diagnose.llm import FakeLLM
from slidko.librarian import FixtureLibrarian
from slidko.narrate.model import Assertion, Evidence

FIXTURES_DIR = Path(__file__).parent.parent / "librarian" / "fixtures"

# An LLM that raises if ever called - proves the config-first branches never
# reach the model.
_UNCALLED_LLM = FakeLLM({
    "action": "clip",
    "target": "SHOULD_NOT_BE_CALLED",
    "parameters": {},
    "expected_outcome_per_hypothesis": {"h": "x"},
    "hazard_notes": "x",
    "executor": "human",
    "citations": [],
    "unknown": False,
})


def _assertion(text: str, kind: str = "event.anomaly") -> Assertion:
    return Assertion(kind=kind, text=text, evidence=Evidence(), confidence=0.8)


def test_config_caused_symptom_emits_config_pull_first():
    """A scripted scenario whose symptom has a known config cause and a
    config-pull path emits a config-pull instruction FIRST, using the fake
    LLM (which must never be called)."""
    librarian = FixtureLibrarian(FIXTURES_DIR)
    assertions = [_assertion("No data on UART2 despite receiver active")]

    instruction = diagnose(assertions, librarian, _UNCALLED_LLM, "matek-f405-wing")

    assert instruction.action == "config_pull"
    assert instruction.target == "CF_SERIAL_CONFIG"
    assert _UNCALLED_LLM.calls == []  # never asked the model


def test_symptom_fully_explained_by_config_short_circuits_no_probe():
    """A symptom fully explained by a retrieved config value (a disabled
    UART port) short-circuits: cites the config evidence, emits a
    config-fix suggestion, and issues NO probe instruction."""
    librarian = FixtureLibrarian(FIXTURES_DIR)
    assertions = [
        _assertion("No data on UART2 despite receiver active"),
        _assertion(
            "Config query shows UART2 disabled in serial config",
            kind="transaction.summary",
        ),
    ]

    instruction = diagnose(assertions, librarian, _UNCALLED_LLM, "matek-f405-wing")

    assert instruction.action == "config_fix"
    assert "uart2 disabled" in instruction.parameters["cited_evidence"].lower()
    assert instruction.action not in {"clip", "probe", "measure", "connect"}
    assert _UNCALLED_LLM.calls == []  # never asked the model


def test_no_config_cause_falls_through_to_llm_probe_proposal():
    librarian = FixtureLibrarian(FIXTURES_DIR)
    assertions = [
        _assertion(
            "37 transactions to 0x68 (MPU-6050), 3 NAKed", kind="transaction.summary"
        )
    ]
    canned = {
        "action": "clip",
        "target": "TP7",
        "parameters": {"power_state": "off"},
        "expected_outcome_per_hypothesis": {"hyp_imu_wiring": "voltage present at TP7"},
        "hazard_notes": "board is unpowered before clipping",
        "executor": "human",
        "citations": ["pinout.md#i2c1"],
        "unknown": False,
    }
    fake_llm = FakeLLM(canned)

    instruction = diagnose(assertions, librarian, fake_llm, "matek-f405-wing")

    assert instruction.action == "clip"
    assert instruction.target == "TP7"
    assert len(fake_llm.calls) == 1
    assert "board_id" in fake_llm.calls[0]


def test_end_to_end_scripted_scenario_against_rubric():
    """Seeded symptom + a plausible next-poke instruction, evaluated
    against a structural rubric (valid schema, grounded citation or
    unknown flag, hazard notes present) - not an exact string match."""
    librarian = FixtureLibrarian(FIXTURES_DIR)
    retrieval = librarian.retrieve("matek-f405-wing")
    assertions = [
        _assertion(
            "37 transactions to I2C address 0x76 (candidates: BMP280, BME280); "
            "no ACK observed on last 5 attempts",
            kind="transaction.summary",
        )
    ]
    canned = {
        "action": "probe",
        "target": "I2C1 SCL test point",
        "parameters": {"power_state": "off"},
        "expected_outcome_per_hypothesis": {
            "hyp_baro_wiring": "continuity present between SCL pad and header"
        },
        "hazard_notes": "board is unpowered before probing",
        "executor": "human",
        "citations": ["pinout.md#i2c1"],
        "unknown": False,
    }
    fake_llm = FakeLLM(canned)

    instruction = diagnose(assertions, librarian, fake_llm, "matek-f405-wing")

    # Rubric, not exact match:
    errors = validate_instruction(instruction, retrieval)
    assert errors == []  # valid schema
    assert instruction.citations or instruction.unknown  # grounded or explicit unknown
    assert instruction.hazard_notes  # hazard notes present
    assert instruction.executor in {"human", "exerciser"}
    assert instruction.expected_outcome_per_hypothesis


if __name__ == "__main__":
    pytest.main([__file__])
