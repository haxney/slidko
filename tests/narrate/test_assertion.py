import json
import unittest
from dataclasses import dataclass
from typing import Tuple, List, Any

# Test that the Assertion and Evidence dataclasses are frozen and compare by value
# Test that the to_json/from_json methods correctly handle round-trips with evidence

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
        return json.dumps({
            "kind": self.kind,
            "text": self.text,
            "evidence": {
                "event_indices": list(self.evidence.event_indices),
                "sample_ranges": [list(r) for r in self.evidence.sample_ranges],
                "finding_refs": list(self.evidence.finding_refs)
            },
            "confidence": self.confidence
        })
    
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

class TestAssertion(unittest.TestCase):
    
    def test_evidence_is_frozen(self):
        """Evidence should be a frozen dataclass that compares by value"""
        e1 = Evidence(event_indices=(0, 1), sample_ranges=((0, 10), (20, 30)))
        e2 = Evidence(event_indices=(0, 1), sample_ranges=((0, 10), (20, 30)))
        
        # Should be equal
        self.assertEqual(e1, e2)
        
        # Should not be able to modify the instance (this will throw AttributeError)
        with self.assertRaises(AttributeError):
            e1.event_indices = (2, 3)

    def test_assertion_is_frozen(self):
        """Assertion should be a frozen dataclass that compares by value""" 
        evidence = Evidence(event_indices=(0, 1), sample_ranges=((0, 10), (20, 30)))
        a1 = Assertion(kind="test", text="test text", evidence=evidence, confidence=0.8)
        a2 = Assertion(kind="test", text="test text", evidence=evidence, confidence=0.8)
        
        # Should be equal
        self.assertEqual(a1, a2)
        
        # Should not be able to modify the instance (this will throw AttributeError)
        with self.assertRaises(AttributeError):
            a1.kind = "modified"

    def test_evidence_comparison(self):
        """Evidence should compare by value"""
        e1 = Evidence(event_indices=(0, 1), sample_ranges=((0, 10), (20, 30)))
        e2 = Evidence(event_indices=(0, 1), sample_ranges=((0, 10), (20, 30)))  
        e3 = Evidence(event_indices=(1, 2), sample_ranges=((0, 10), (20, 30)))
        
        self.assertEqual(e1, e2)
        self.assertNotEqual(e1, e3)

    def test_assertion_comparison(self):
        """Assertion should compare by value"""
        evidence1 = Evidence(event_indices=(0, 1))
        evidence2 = Evidence(event_indices=(2, 3))
        
        a1 = Assertion(kind="test", text="text1", evidence=evidence1, confidence=0.8)
        a2 = Assertion(kind="test", text="text1", evidence=evidence1, confidence=0.8)
        a3 = Assertion(kind="different", text="text1", evidence=evidence1, confidence=0.8)
        a4 = Assertion(kind="test", text="text2", evidence=evidence1, confidence=0.8)
        a5 = Assertion(kind="test", text="text1", evidence=evidence2, confidence=0.8)
        
        self.assertEqual(a1, a2)
        self.assertNotEqual(a1, a3)  # Different kind  
        self.assertNotEqual(a1, a4)  # Different text
        self.assertNotEqual(a1, a5)  # Different evidence

    def test_json_roundtrip(self):
        """Assertion should round-trip correctly through JSON"""
        original_evidence = Evidence(
            event_indices=(0, 1, 2),
            sample_ranges=((10, 20), (30, 40)),
            finding_refs=(5, 6)
        )
        
        original_assertion = Assertion(
            kind="transaction.summary",
            text="37 transactions to 0x68, 3 NAKed",
            evidence=original_evidence,
            confidence=0.95
        )
        
        # Serialize to JSON string using to_json method
        json_str = original_assertion.to_json()
        
        # Deserialize from JSON string
        loaded_assertion = Assertion.from_json(json_str)
        
        # Check that the original and reloaded are equal
        self.assertEqual(original_assertion, loaded_assertion)

    def test_to_json_method(self):
        """Test that to_json method produces expected output"""
        evidence = Evidence(
            event_indices=(1, 2),
            sample_ranges=((10, 20), (30, 40))
        )
        assertion = Assertion(
            kind="transaction.summary",
            text="37 transactions to 0x68, 3 NAKed",
            evidence=evidence,
            confidence=0.95
        )
        
        json_str = assertion.to_json()
        parsed = json.loads(json_str)
        
        self.assertEqual(parsed['kind'], "transaction.summary")
        self.assertEqual(parsed['text'], "37 transactions to 0x68, 3 NAKed")
        self.assertEqual(parsed['confidence'], 0.95)
        self.assertEqual(parsed['evidence']['event_indices'], [1, 2])
        self.assertEqual(parsed['evidence']['sample_ranges'], [[10, 20], [30, 40]])
        self.assertEqual(parsed['evidence']['finding_refs'], [])

    def test_from_json_method(self):
        """Test that from_json method creates correct object"""
        json_str = '''{
            "kind": "transaction.summary",
            "text": "37 transactions to 0x68, 3 NAKed",
            "evidence": {
                "event_indices": [1, 2],
                "sample_ranges": [[10, 20], [30, 40]],
                "finding_refs": [5]
            },
            "confidence": 0.95
        }'''
        
        assertion = Assertion.from_json(json_str)
        
        self.assertEqual(assertion.kind, "transaction.summary")
        self.assertEqual(assertion.text, "37 transactions to 0x68, 3 NAKed")
        self.assertEqual(assertion.confidence, 0.95)
        self.assertEqual(assertion.evidence.event_indices, (1, 2))
        self.assertEqual(assertion.evidence.sample_ranges, ((10, 20), (30, 40)))
        self.assertEqual(assertion.evidence.finding_refs, (5,))

if __name__ == '__main__':
    unittest.main()