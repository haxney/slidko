# Design thesis

## The observation gap

LLMs are strong abductive reasoners over text and nearly blind to raw
electrical reality. Hardware debugging knowledge (datasheets, pinout wikis,
forum lore) is maximally legible to an LLM; the evidence (waveforms) is
maximally illegible. Slidko's core is the transducer that closes this gap:
convert raw captures into compact symbolic descriptions an LLM can reason
over, then close a measurement loop around the reasoning.

## Two independent axes

- **Logical depth** (Bennett): how much serial reasoning the task needs. Fault
  diagnosis is genuinely deep — many faults produce similar symptoms; you
  reason backward through a causal chain.
- **The fidelity gate** (Shannon; data-processing inequality): how much of the
  discriminating information survives into the representation handed to the
  model. Post-processing can only destroy mutual information. A 640×480 PNG of
  a scope screen when the fault lives at 100 MSa/s has already lost.

Four quadrants: deep + gated-out = hopeless. Shallow + gated-out = noise.
Deep + preserved = hard but solvable (this is a full-fidelity trace).
Shallow + preserved = easy and fully specified (a config file).

**A raw trace is not shallow and not noise — it is raw**: highly structured,
logically deep, and in the wrong representation. The diagnostic tokens
(edges, packets, bus states, anomalies) must be extracted before reasoning
can begin. Legibility, not depth, is what makes trace data hard for LLMs.
Confidence: HIGH that legibility dominates for current models.

## The ordering principle: fidelity, then legibility, then depth

1. **Fidelity gate first** — don't destroy the information. Hard gate; fix
   before anything else.
2. **Legibility second** — tokenize the survivors. "CH1 falls to 2.9 V at
   t=1.3 ms, 180 mV below nominal, coincident with a 400 mA spike on CH2" is
   legible; the same fact in 50,000 raw samples is not.
3. **Thinking room third** — diagnosis is abductive and needs serial depth:
   chain-of-thought space and the poke loop. The loop decomposes a deep
   problem into a sequence of shallow steps — chain-of-thought applied to
   physical measurement.

The engineering core is the tension inside Narrate: extract aggressively
enough to be legible, conservatively enough not to discard an anomaly not
yet hypothesized.

Caveat (MODERATE confidence): a frontier model with good few-shot priming may
partially bootstrap in-context decoding from raw-trace→diagnosis examples,
relaxing the legibility constraint. It cannot rescue the fidelity gate — lost
information stays lost. Test empirically.

## DSP first, ML at the margins, LLM on top

The image-model analogy (train a CNN like YOLO) breaks completely here:
(a) essentially no labeled corpus of raw captures tagged with protocol/fault
exists, and (b) the core tasks have closed-form solutions — clock recovery,
baud estimation, and edge detection are 40–60-year-old solved DSP problems
(autocorrelation, FFT, edge-interval histograms, timing recovery). When a
deterministic algorithm exists and is cheap, a learned approximation is
strictly worse: brittle, uninterpretable, and hungry for data that doesn't
exist. **Reach for classical DSP first; ML only where DSP provably can't
reach.** Confidence: HIGH.

Where learned models may eventually earn a place, in descending
justification: (1) analog-fault fingerprinting (ringing, reflections, ground
bounce) — and even there, hand-designed features + gradient boosting likely
beats a CNN until thousands of labeled examples exist; (2) protocol
classification residue — a decision tree over DSP features gets 90%+ with
zero training; (3) embeddings — SKIP: no pretrained waveform-embedding model
exists; revisit only when a direct feature vector demonstrably fails a
concrete task.

**No ML training on the v1 critical path.** The corpus labeling discipline
(see CORPUS.md) preserves the training option at zero extra cost.

## The receiver rule

A digital logic analyzer is trustworthy exactly when binarization at ITS
threshold is a faithful proxy for binarization at the RECEIVER's threshold.
The fx2lafw-class DLA has a fixed ~1.4 V threshold; a 5 V WS2812 pixel judges
the same wire at V_IH ≈ 0.7·VDD ≈ 3.5 V. The killer case: the DLA decodes
fine while the LEDs glitch (waveform clears 1.4 V but not 3.5 V — the classic
3.3 V-driver-into-5 V-strip fault). A DLA answers "what does this look like
to MY comparator" — a question nobody asked. Every signal judgment in Slidko
is referenced to the receiver's threshold; where the instrument can't see
that, the gap is stated explicitly.

## The smoke detector

Analog faults leave digital fingerprints. Pure edge-timestamp statistics can
DETECT (not diagnose) digital-abstraction contract breaches:

- **Edge chatter** — ringing/slow edges crossing threshold multiple times:
  bursts of toggles with inter-edge intervals ≪ bit period.
- **Runt/glitch pulses** — 1–2-sample pulses inconsistent with any legal
  symbol.
- **Timing violations** — bit periods outside spec, asymmetric high/low,
  excess jitter (WS2812's ±150 ns windows are a direct numeric check).
- **Protocol incoherence** — framing/checksum failures, ACKs from nobody:
  decode "succeeding" into garbage.

Detection triggers the escalation move: **smoke → scope** ("capture this line
with an oscilloscope; expect X"). Sensitivity caveat: at 24 MS/s, ringing
above ~10 MHz falls between samples — this is a smoke detector, not a gas
chromatograph.

## Logic-first sequencing

Start with a logic analyzer, not an oscilloscope. LA front-ends deliver
pre-binarized streams — the hardware has already done the analog work; what
remains is pure edge math. The oscilloscope path (brownout, ringing, analog
levels) is analog hardening and comes second, initially as human-relayed
escalation instructions only.

## Target user

Decently handy with a soldering iron; has NOT read the datasheet; cannot
answer "where do I start poking" on a mid-tier flight controller unaided.
This is exactly the user existing tools abandon: decoder tools assume
protocol parameters, scope UIs assume you know what to look for, forums
require the vocabulary to ask. Slidko fills the symptom→vocabulary gap.
Division of labor: **the user is the hands; Slidko is the entity that read
every datasheet.**

A large fraction of real faults are config, power, connector, or wiring
problems — not exotic silicon failures. The fault tree's first layer is often
probe-free (config pull); the tool must check software configuration before
sending anyone soldering.

## Adoption discipline

Stated demand is near-worthless; pull behavior at the moment of failure is
the only valid adoption signal. The tool must slot into the user's existing
workflow (their $10 logic analyzer, their bench) — tools requiring workflow
replacement carry fatal switching costs regardless of stated interest. This
is why v1 targets the commodity fx2lafw-class device the user already owns.
