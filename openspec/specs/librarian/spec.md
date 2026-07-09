# librarian

## Purpose

Board-keyed retrieval of pinout/connector documentation, exposed as
citable units (`doc-id#anchor`) that Diagnose must reference for any
pad-level placement claim. Tracks documentation tier per board so
Diagnose can calibrate confidence — dark boards force unknown flags and
measure-first instructions instead of fabricated citations.

## Requirements

### Requirement: Board-keyed document retrieval
The librarian SHALL retrieve pinout/connector documentation keyed by board identity and expose retrieved content as citable units addressable as `doc-id#anchor`.

#### Scenario: Retrieval yields citable anchors
- **WHEN** documents are retrieved for a known board ID (fixture-backed, offline)
- **THEN** each retrievable claim-bearing fragment has a stable doc-id#anchor usable in instruction citations

### Requirement: Citations resolve or fail loudly
Every citation attached to an instruction SHALL resolve to retrieved content; dangling citations are validation errors, equivalent to uncited claims.

#### Scenario: Dangling citation rejected
- **WHEN** a canned instruction cites doc-id#anchor absent from the retrieval set
- **THEN** validation rejects the instruction

### Requirement: Documentation-tier awareness
Retrieval results SHALL state the board's documentation tier (open-book / pinout-only / dark) so Diagnose can calibrate: dark boards yield no pad-level citations, forcing unknown flags and measure-first instructions.

#### Scenario: Dark board forces unknown
- **WHEN** the librarian reports tier "dark" for the session's board
- **THEN** any pad-level placement claim without `"unknown": true` fails validation
