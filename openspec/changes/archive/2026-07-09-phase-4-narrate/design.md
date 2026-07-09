# Design: phase-4-narrate

## Context

Narrate is the highest-leverage layer (docs/ARCHITECTURE.md, docs/DESIGN.md):
flat decoded fields + smoke findings + cross-channel alignment become
diagnostically salient English assertions. The engineering tension (DESIGN.md
§ ordering principle) is to extract aggressively enough to be legible,
conservatively enough not to discard an anomaly not yet hypothesized. Assertions
are structured objects first, rendered to English second, and every one is
traceable to the events/samples it derives from.

The load-bearing correctness case is **the receiver rule** (DESIGN.md): a
capture that decodes cleanly at the instrument's 1.4 V threshold but whose
receiver verdict is "flickered" must narrate a caveat, never "bus healthy."

## Goals / Non-Goals

**Goals:**
- Quantitative, protocol-aware, cross-channel assertions as structured objects.
- Every assertion carries evidence references (event indices / sample ranges).
- Golden-file eval, order-insensitive.
- The receiver-rule caveat as tested product behavior.

**Non-Goals:**
- No LLM (that is Diagnose, Phase 5). No next-instruction generation. No doc
  retrieval. Narrate is deterministic assembly of assertions from lower layers.

## Decisions

### Assertion schema

```python
@dataclass(frozen=True)
class Assertion:
    kind: str              # "device.identified" | "transaction.summary" |
                           # "event.anomaly" | "coincidence" |
                           # "receiver_rule.caveat"
    text: str              # rendered English, quantitative, with units
    evidence: Evidence     # traceable back to source
    confidence: float      # [0,1]

@dataclass(frozen=True)
class Evidence:
    event_indices: tuple[int, ...] = ()      # indices into the DecodedEvent list
    sample_ranges: tuple[tuple[int, int], ...] = ()
    finding_refs: tuple[int, ...] = ()       # indices into the SmokeFinding list
```

Assertions compare by value; `evidence` must survive JSON round-trip (the
traceability scenario). Store the source sample ranges, not seconds.

### I²C address → part-name lookup

Addresses are NOT unique (docs UX-loop finding: "0x12 ≠ automatically PMSA003I").
The lookup returns a LIST of candidate parts, never a single identification, and
the assertion says "matches known part(s): …" — a candidate set, so Diagnose and
the user can disambiguate by traffic pattern or package marking. Ship a starter
address book as committed data (`narrate/address_book.py` or a JSON), keyed by
7-bit address, values = list of `{part, kind, note}`. Seed set (maker/drone
common parts; confidence HIGH on these being the usual suspects, MODERATE that a
given board uses them — the assertion is candidacy, not identification):

| Addr(s) | Candidate parts (kind) |
|---|---|
| 0x68, 0x69 | MPU-6050 / MPU-9250 / ICM-20602 (IMU); DS3231 / DS1307 (RTC) |
| 0x76, 0x77 | BMP280 / BME280 (baro/humidity); BMP180 (0x77) |
| 0x0C, 0x0D | AK8963 (mag, aux); QMC5883L (0x0D, mag) |
| 0x1E | HMC5883L (magnetometer) |
| 0x29 | VL53L0X (ToF distance) |
| 0x3C, 0x3D | SSD1306 / SH1106 (OLED display) |
| 0x40–0x4F | INA219/INA226 (current); PCA9685 (PWM/servo driver); Si7021 |
| 0x50–0x57 | 24Cxx (I²C EEPROM) |
| 0x12 | PMSA003I (particulate sensor) |

Keep the table small and correct; it is data, not logic, and grows by editing
the table (never by branching). Cite the address in the assertion text.

### Transaction summarization

Aggregate `DecodedEvent`s into per-target summaries: "N I²C transactions to
0x68 (candidates: MPU-6050/ICM-20602 IMU, DS3231 RTC); M NAKed." Numbers with
units; the evidence references the contributing event indices.

### Cross-channel coincidence detection

Given events/findings on multiple channels, detect pairs whose sample ranges
fall within a configurable coincidence window (`COINCIDENCE_WINDOW_SAMPLES`,
default derived from a small time window, e.g. 100 µs → samples at the capture
rate). When a NAK on one channel and a smoke finding on another coincide, emit a
single `coincidence` assertion stating both events, their channels, and the time
delta in real units. This is the "transaction 38 NAKed, coincident with a rail
dip on CH7" pattern from ARCHITECTURE.md.

### Receiver-rule caveat (the killer case)

Inputs: capture provenance (`instrument.threshold_v`) and, where present, the
corpus sidecar's `receiver` block (`vih_v`) and `receiver_verdict.observed`
(from docs/CORPUS.md schema). Rule: when the instrument threshold differs
materially from the receiver V_IH **and** the receiver verdict contradicts a
clean decode (decode succeeded but verdict is a failure like "flicker"), emit a
`receiver_rule.caveat` assertion naming both thresholds and stating the decode
cannot be trusted as receiver-truth — and SUPPRESS any "bus healthy" assertion.
Concretely, the WS2812 killer case: instrument 1.4 V, receiver V_IH ≈ 3.5 V
(5 V WS2812), verdict "flicker" → caveat present, no health claim. "Materially
different" is a named constant (`RECEIVER_THRESHOLD_MARGIN_V`, default 0.5 V).

Where no receiver metadata exists (bare capture), Narrate does not fabricate a
verdict — it may note the instrument threshold as a stated limitation but makes
no receiver claim either way. It never asserts "healthy" about receiver behavior
it cannot see.

### Golden-file harness

`tests/narrate/golden/<entry>.json` holds the expected assertion set. The
comparison is order-insensitive (compare as sets/multisets of assertions by
`kind`+`text`+`evidence`), so ordering churn never breaks tests; missing or
extra assertions DO fail. Provide a helper to (re)generate goldens deliberately,
but the committed goldens are the contract.

## Risks / Trade-offs

- [Over-extraction discards un-hypothesized anomalies] → Narrate never deletes
  smoke findings; it surfaces them as `event.anomaly` assertions even when it
  cannot summarize them, preserving the conservative side of the tension.
- [Address book implies false certainty] → lookups return candidate LISTS and
  the text says "candidates"; identification is deferred to Diagnose + package
  marking, per the UX-loop ruling.
- [Receiver metadata absent in bare captures] → the caveat rule degrades to
  "state the limitation, make no receiver claim"; it never invents a verdict.
