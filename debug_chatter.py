import pytest
from src.slidko.measure.smoke import detect_edge_chatter

def test_debug():
    """Debug the edge chatter detection logic"""
    # Simulate chatter - multiple edges in quick succession  
    edges = [0, 40, 50, 60, 70, 100]
    t_bit = 100
    
    # Manually trace through the computation:
    print("Edges:", edges)
    intervals = [edges[i+1] - edges[i] for i in range(len(edges)-1)]
    print("Intervals:", intervals)
    
    print("CHATTER_FRACTION * t_bit =", 0.25 * 100)
    for i, interval in enumerate(intervals):
        print(f"Interval {i}: {interval} < {0.25 * 100}? {interval < 0.25 * 100}")
    
    findings = detect_edge_chatter(edges, t_bit, "channel_A")
    print("Findings:", findings)
    
if __name__ == "__main__":
    test_debug()