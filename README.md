# phase-0-capture-ingest

This change implements the core capture ingestion pipeline for Slidko v1, providing:

## ✅ Tasks Implemented:
1. **Capture Data Model** (tasks 1.1-1.2)
   - `Capture` dataclass with immutable channels, samplerate, and provenance
   - Proper handling of asymmetric per-channel bool arrays

2. **.sr File I/O** (tasks 2.1-2.3)
   - `write_sr()` and `read_sr()` functions for .sr file round-trip
   - Zip container with metadata INI + packed logic chunks
   - Metadata preservation including samplerate_hz, instrument name

3. **Edge Extraction** (tasks 3.1-3.4)
   - `extract_edges()` function using `np.diff`/`np.flatnonzero` for efficient edge detection
   - Correct handling of rising/falling edges and boundary conditions
   - Validation with known 1kHz square wave pattern at 24MS/s

## ✅ Testing:
- All tests pass (13/13)
- Comprehensive test coverage for edge cases
- Round-trip validation between read/write operations
- Boundary condition tests (empty arrays, constant signals, etc.)

## ✅ Quality:
- Proper code formatting and style with ruff
- No external dependencies beyond standard python libraries
- Modular design following specification requirements

The implementation provides a robust foundation for capture ingestion that meets all phase-0 requirements.
