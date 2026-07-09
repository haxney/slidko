"""The symptom -> fault-tree map (design.md § Fault-tree ordering):
config-pull branches always sort before probe branches. Deterministic and
LLM-free - the routing decision, not the instruction content, is what must
be config-first.
"""

from dataclasses import dataclass

from slidko.diagnose.config_pull import MspReadCommand


@dataclass(frozen=True)
class ConfigBranch:
    """A probe-free fault-tree branch: a specific config value that, if
    already known and if it explains the symptom, resolves the case with
    no physical probing at all."""

    command: MspReadCommand
    explains: str  # substring match (lowercased) against assertion text
    fix_suggestion: str


@dataclass(frozen=True)
class SymptomEntry:
    """Ordered fault-tree branches for one symptom. Config branches are
    checked first, always - that ordering is the point of this module, not
    a runtime decision."""

    trigger: str  # substring match (lowercased) identifying this symptom
    config_branches: tuple[ConfigBranch, ...] = ()


# EMPIRICAL, n=this-bench: a small seed set, not exhaustive. Grows by
# editing this table (design.md's own discipline for the address book
# applies here too - data, not branching logic).
SYMPTOM_FAULT_TREE: tuple[SymptomEntry, ...] = (
    SymptomEntry(
        trigger="no data on uart2",
        config_branches=(
            ConfigBranch(
                command=MspReadCommand.CF_SERIAL_CONFIG,
                explains="uart2 disabled",
                fix_suggestion=(
                    "Enable UART2 in the serial configuration "
                    "(MSP_CF_SERIAL_CONFIG) and retry."
                ),
            ),
        ),
    ),
)


def classify_symptom(assertion_texts: list[str]) -> SymptomEntry | None:
    """Match the first symptom whose trigger substring appears in any
    assertion's text (case-insensitive). Returns None when nothing in the
    fault tree matches - the caller falls through to the probe/LLM branch."""
    lowered = [text.lower() for text in assertion_texts]
    for entry in SYMPTOM_FAULT_TREE:
        if any(entry.trigger in text for text in lowered):
            return entry
    return None
