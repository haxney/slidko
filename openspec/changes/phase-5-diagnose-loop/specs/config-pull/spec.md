# Delta: config-pull

## ADDED Requirements

### Requirement: Read-only interrogation over documented protocols
Config pull SHALL interrogate DUT configuration exclusively via documented, read-only protocol operations (e.g., Betaflight MSP query, CLI dump capture). The module SHALL expose no write, flash, or command capability of any kind — this is a product-premise boundary, not a milestone.

#### Scenario: No write paths exist
- **WHEN** the config-pull module's public API is inspected by test
- **THEN** every operation is a read/query; no function transmits state-changing commands to the DUT

#### Scenario: Write-shaped request refused
- **WHEN** a caller attempts to route a state-changing operation through config pull (canned request)
- **THEN** it is rejected with an explicit product-boundary error

### Requirement: Probe-free first layer of the fault tree
Config pull results SHALL be structured so Diagnose can consume them as the fault tree's first layer: retrieved settings mapped to symptom-relevant checks before any probe instruction is generated.

#### Scenario: Config answer short-circuits probing
- **WHEN** a scripted scenario's symptom is fully explained by a retrieved config value (e.g., disabled UART port)
- **THEN** the diagnosis cites the config evidence and emits a config-fix suggestion, with no probe instruction issued
