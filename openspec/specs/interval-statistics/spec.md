# interval-statistics

## Purpose

Interval histogram, autocorrelation, and dominant-period/periodicity-strength
primitives shared by every Phase 1 discriminator (SCL regularity, SPI clock
burst detection, PWM base rate). Deterministic DSP only — no ML — with every
estimate carrying a numeric confidence in [0, 1].

## Requirements

### Requirement: Interval histogram primitives
Measure SHALL compute inter-edge interval histograms per channel (numpy-vectorized) exposing the dominant interval clusters that discriminators consume.

#### Scenario: Bimodal square-wave histogram
- **WHEN** intervals of a clean square wave are histogrammed
- **THEN** a single dominant cluster at the half-period appears with all mass within ±1 sample

### Requirement: Autocorrelation period estimation with confidence
Measure SHALL estimate the dominant clock period of a channel via autocorrelation (or equivalent closed-form DSP), returning the period and a numeric confidence in [0, 1]; no learned models.

#### Scenario: Known-period recovery
- **WHEN** the estimator runs on a synthetic stream with known bit period and no jitter
- **THEN** the estimated period matches ground truth exactly and confidence is high (≥ 0.9)

#### Scenario: Confidence degrades under jitter, answer does not lie
- **WHEN** the estimator runs on the same stream with heavy injected jitter
- **THEN** either the period remains correct or the reported confidence drops below the caller-visible threshold — never a confidently wrong period

### Requirement: Dominant-period extraction utilities
The module SHALL expose dominant-period / periodicity-strength helpers shared by all discriminators (SCL regularity, SPI clock burst detection, PWM base rate).

#### Scenario: Periodicity strength separates clock from data
- **WHEN** periodicity strength is computed for an I²C SCL channel and its paired SDA channel
- **THEN** SCL scores strictly higher than SDA
