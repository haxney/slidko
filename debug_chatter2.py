import pytest
from src.slidko.measure.smoke import detect_edge_chatter

def test_debug():
    """Debug the edge chatter detection logic"""
    # Test case from failing test
    edges = [0, 40, 50, 60, 70, 100]
    t_bit = 100
    
    print("Edges:", edges)
    intervals = [edges[i+1] - edges[i] for i in range(len(edges)-1)]
    print("Intervals:", intervals)
    
    # From my implementation:
    # Edge indices: 0, 1, 2, 3, 4, 5
    # Edges:        0, 40, 50, 60, 70, 100  
    # Intervals:    40, 10, 10, 10, 30
    
    # i = 0:
    #   intervals[0] = 40 < 25 ? False, continue
    #
    # i = 1:
    #   intervals[1] = 10 < 25 ? True 
    #   start_idx = 1
    #   count = 1 
    #   While loop continues: 
    #     i + count = 2, intervals[2] = 10 < 25? True  
    #     count = 2
    #     i + count = 3, intervals[3] = 10 < 25? True
    #     count = 3
    #     i + count = 4, intervals[4] = 30 < 25? False, exit loop 
    #   Since count = 3 >= CHATTER_MIN_EDGES = 3:
    #     Create finding with start_sample = edges[1] = 40
    #     end_sample = edges[i + count] = edges[4] = 70 (but wait... index 4 from intervals list is at edge index 5)
    #
    # Wait, the edges array has:
    # Edge indices: 0, 1, 2, 3, 4, 5
    # Edge values:  0, 40, 50, 60, 70, 100
    # The finding window should cover samples from edge 1 up to (including) edge 4 
    # So end_sample should be edges[4] = 70
    
    print("Expected start sample: edges[1] =", edges[1])
    print("Expected end sample: edges[4] =", edges[4])
    
if __name__ == "__main__":
    test_debug()