# Architecture

## System topology (v1) — three physical components

1. **Laptop program (the product).** Capture orchestration, Measure, Decode,
   smoke detector, Narrate (numpy/scipy + wrapped sigrok decoders), librarian
   retrieval, Diagnose LLM calls. UI = the poke loop conversation.
2. **Commodity USB DLA** — fx2lafw-class (Cypress FX2LP) 8-channel 24 MS/s
   clone, natively sigrok-supported, USB 2.0 High-Speed streaming with
   unbounded capture depth. This is the capture front-end and the fidelity
   gate's hardware enforcement point. The oscilloscope is NOT core:
   escalation-only ("smoke → scope"), human-relayed in v1. Later: direct SCPI
   integration (HIGH confidence SCPI exists on bench scopes; MODERATE on
   waveform-transfer ergonomics).
3. **The exerciser** — RP2350 running project-authored firmware, structured
   serial commands from the laptop (see EXERCISER.md). The same firmware the
   bench corpus requires. Session-optional: the loop degrades to
   watch + twiddle without it.

## Dataflow: the five-verb pipeline

```
DLA ──.sr/raw binary──▶ Capture ──bit arrays──▶ Measure ──features──▶ Decode
                                                    │                    │
                                              smoke detector      decoded events
                                                    └────────┬───────────┘
                                                             ▼
                                        Narrate ──assertions──▶ Diagnose ◀── librarian (docs)
                                                                   │
                                                     next instruction (human | exerciser)
```

- **Capture:** ingest .sr files (zip container: binary logic data +
  metadata) or sigrok-cli streamed output into numpy bit arrays. Record
  instrument identity, sample rate, threshold in metadata — captures are
  evidence and must carry their chain of custody.
- **Measure (deterministic, no ML):** per-channel voltage-level clustering
  (where analog exists), edge timestamp extraction, autocorrelation → clock
  period, inter-edge interval histograms → bit period + encoding, FFT →
  carriers/PWM; cross-channel: phase relations → clock-vs-data
  identification, bus topology. Output: compact structured description of
  what the signal physically is, with quantitative confidence per claim.
  **This replaces "user, please specify the protocol and baud" — measure it,
  don't ask.** The parameter-inference layer is the differentiated
  contribution and must stay cleanly separable.
- **Decode:** a classifier (hand-built decision tree over Measure features)
  ranks candidate protocols, then invokes a decoder backend with the inferred
  parameters.
- **Narrate (the product; highest-leverage layer):** convert flat decoded
  fields into diagnostically salient assertions: "37 I²C transactions to 0x68
  (matches an IMU's default address); transaction 38 NAKed; coincident with a
  rail dip on CH7." Part cross-signal correlation, part protocol knowledge
  (address → part lookup), part event alignment. Unglamorous plumbing; where
  the defensible value concentrates.
- **Diagnose:** LLM abductive reasoning over Narrate assertions only. Emits
  the structured instruction schema:

  ```json
  {
    "action": "...", "target": "...", "parameters": {},
    "expected_outcome_per_hypothesis": {"H1": "...", "H2": "..."},
    "hazard_notes": "...",
    "executor": "human | exerciser",
    "citations": ["doc-id#anchor", "..."]
  }
  ```

  **Citation enforcement is architectural, not prompt text:** any pad-level
  placement claim REQUIRES a citation to a librarian-retrieved document or an
  explicit `"unknown": true` flag. Hallucinated pinouts are the
  product-killing failure mode — a confabulated "clip here" on a powered
  board causes shorts. Schema validation rejects uncited pad claims.
- **Accessibility filter** in instruction generation: prefer connectors, test
  points, and passive-component bodies over IC pins. Never instruct
  needle-probing fine-pitch (≤0.5 mm) IC pads on a live board.

## Sigrok posture: parasitic, not dependent

libsigrokdecode's value is not the code — it is the corpus of ~150+ protocol
decoders: person-years of tested framing/timing/edge-case knowledge.
Reimplementing UART/SPI/I²C is a weekend; the long tail is the moat.

Strategy:
- Wrap the decoder corpus as a **decode backend behind an abstraction layer**
  (`decode/backend.py` interface; sigrok is one implementation).
- **Feed it parameters Measure inferred** — removing the manual-config burden
  is our contribution and is cleanly separable from the decoders themselves.
- **Pin a known-good version.** Vendor the version pin; be ready to swap
  individual decoders if they rot. Do not couple product fate to upstream
  release cadence (upstream releases are infrequent; git activity is the
  health signal to watch — verify current state before major integration
  work).
- Robust integration path: prefer invoking `sigrok-cli` as a subprocess over
  in-process bindings; parse .sr files directly (zip + metadata + binary
  channel data) with our own reader for the ingest path.

## Offline / online split (strategic)

- **Offline-capable:** everything below Narrate — signal auto-ID, decode,
  smoke detector. Degraded mode = "magic logic analyzer, no diagnosis."
- **Internet-required:** Diagnose (frontier LLM API) + librarian (live doc
  retrieval). A local-model Diagnose backend is architecture-compatible
  future work; local models will underperform at exactly the abductive
  reasoning Diagnose exists for (MODERATE confidence on eventual adequacy).

## Hardware tier ladder (onboarding-cost lever, future)

Config-pull dongle (MCP2221A-class, ~$2) → lightweight bus exerciser
(FT232H/MPSSE) → full exerciser (RP2350, canonical) → the pod (fused
timebase). v1 ships against the middle rungs.

## Deferred: the bridge pod (DO NOT BUILD IN v1)

Definition: a single device where capture and exercise share one silicon and
one clock domain, streaming over USB HS. Defining property: the same timebase
that emits a stimulus edge timestamps the captured samples —
stimulus-to-response correlation is cycle-accurate by construction, and the
reserved sync channel dissolves.

Selected architecture (on paper): RP2350 PIO0 capture → DMA → SRAM elastic
buffer (520 KB ≈ 10–20 ms host-stall slack) → DMA → PIO1 drives an 8-bit
parallel bus with flow control → FTDI FT232H in FT245 synchronous FIFO mode
(~35–40 MB/s) → host. Control plane: RP2350's native USB FS port (TinyUSB
CDC), unified to one cable via an internal USB2 hub IC (FE1.1s/USB2514-class)
— the PIO→FTDI path stays purely unidirectional. Known trap: FT2232H
channel B is disabled when channel A runs sync FIFO (MODERATE-HIGH; verify
against datasheet before any design commit).

**Gate:** a two-cable benchmark prototype (~$15 in parts) must prove
sustained 24 MB/s PIO→DMA→PIO→FT232H before any pod engineering enters the
roadmap. The RP-family's native USB is Full-Speed (12 Mbps) — endurance
streaming capture through it is physically impossible; do not design around
it. Fixed-function bridge chips cannot replace the MCU: they lack a sovereign
sampling clock, an elastic buffer, programmable acquisition intelligence, and
a stimulus path sharing the capture clock domain.

Nothing in `src/` may import from, depend on, or block on pod concepts.
