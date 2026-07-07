from dataclasses import dataclass, asdict
from typing import Tuple
import json

@dataclass(frozen=True)
class Evidence:
    event_indices: Tuple[int, ...] = ()
    sample_ranges: Tuple[Tuple[int, int], ...] = ()
    finding_refs: Tuple[int, ...] = ()

@dataclass(frozen=True)
class Assertion:
    kind: str
    text: str
    evidence: Evidence
    confidence: float
    
    def to_json(self) -> str:
        """Convert Assertion to JSON string"""
        return json.dumps(asdict(self))
    
    @classmethod
    def from_json(cls, json_str: str):
        """Create Assertion from JSON string"""
        data = json.loads(json_str)
        evidence_data = data['evidence']
        evidence = Evidence(
            event_indices=tuple(evidence_data['event_indices']),
            sample_ranges=tuple(tuple(r) for r in evidence_data['sample_ranges']),
            finding_refs=tuple(evidence_data['finding_refs'])
        )
        return cls(
            kind=data['kind'],
            text=data['text'],
            evidence=evidence,
            confidence=data['confidence']
        )