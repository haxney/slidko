# edge-extraction

## Purpose

TBD — captures vectorized edge-timestamp extraction and inter-edge interval
helpers that serve as the shared primitives for downstream Measure-layer
discriminators.

## Requirements

### Requirement: Vectorized edge timestamp extraction
The Measure layer SHALL extract rising and falling edge timestamps per channel from bit arrays using vectorized numpy operations (`np.diff`/`np.flatnonzero`-class, no Python-level sample loops), returning arrays of (sample_index, polarity).

#### Scenario: Square wave exactness
- **WHEN** edges are extracted from a synthetic 1 kHz square wave sampled at 24 MS/s
- **THEN** inter-edge intervals are exactly 12000 samples (± 0) and polarity strictly alternates

#### Scenario: Edge cases at array boundaries
- **WHEN** a bit array begins or ends mid-level (no transition at index 0 or the final index)
- **THEN** no spurious edge is reported at either boundary

### Requirement: Inter-edge interval helpers
The edge-extraction module SHALL provide interval computation helpers (per-channel inter-edge intervals, same-polarity intervals) as the shared primitives for downstream discriminators.

#### Scenario: Interval round trip on known stream
- **WHEN** intervals are computed for a synthetic edge stream with known spacing
- **THEN** the interval arrays match the generator's ground truth exactly
