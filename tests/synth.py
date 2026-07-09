"""
Synthetic capture generators for Slidko - ground-truth labeled
in-memory signal generation (the program's test infrastructure).

Each generator function returns a (Capture, GroundTruth) tuple.
The GroundTruth label dataclass contains protocol metadata and
fault information that can be used to verify the correctness of
auto-detection algorithms.

Signals are built as run-length-encoded (level, sample_count) segments,
then expanded into boolean numpy arrays. Consecutive equal-level segments
naturally coalesce (no edge) once expanded, so callers may freely emit a
level per logical bit without special-casing repeats.
"""

from dataclasses import dataclass, replace
from itertools import pairwise

import numpy as np

from slidko.capture import Capture
from slidko.measure.dshot import DSHOT_FRAME_GAP_NS, DSHOT_TIMING_NS, dshot_checksum

DEFAULT_SAMPLE_RATE_HZ = 24_000_000


@dataclass
class GroundTruth:
    """Label for a synthetic capture - contains ground-truth protocol info."""

    # Protocol identification
    protocol: str  # "UART", "I2C", "SPI", "WS2812", etc.

    # Protocol-specific parameters
    parameters: dict

    # Payload data (if applicable)
    payload: list[int] | None = None

    # Injected faults - each a dict with at least a "kind" key (see the
    # inject_* functions below for the concrete shapes).
    injected_faults: list[dict] | None = None

    # Random seed for reproducibility
    seed: int = 0

    def __post_init__(self):
        if self.injected_faults is None:
            self.injected_faults = []


class Generator:
    """Base class for synthetic capture generators."""

    def __init__(self, seed: int = 0):
        self.seed = seed
        self.rng = np.random.default_rng(seed)

    def generate(self) -> tuple[Capture, GroundTruth]:
        """Generate a synthetic capture with ground truth label.

        Returns:
            Tuple of (Capture, GroundTruth)
        """
        raise NotImplementedError("Subclasses must implement generate()")


def expand_segments(segments: list[tuple[bool, int]]) -> np.ndarray:
    """Expand (level, sample_count) run-length segments into a bool array."""
    segments = [(level, count) for level, count in segments if count > 0]
    if not segments:
        return np.array([], dtype=bool)
    return np.concatenate([
        np.full(count, level, dtype=bool) for level, count in segments
    ])


def channel_to_segments(channel: np.ndarray) -> list[tuple[bool, int]]:
    """Inverse of `expand_segments`: run-length-encode a bool array."""
    if len(channel) == 0:
        return []
    change_idx = np.flatnonzero(np.diff(channel.astype(int)) != 0) + 1
    boundaries = np.concatenate([[0], change_idx, [len(channel)]])
    return [
        (bool(channel[start]), int(end - start)) for start, end in pairwise(boundaries)
    ]


def byte_bits_msb_first(byte: int, width: int = 8) -> list[bool]:
    return [bool((byte >> i) & 1) for i in range(width - 1, -1, -1)]


def byte_bits_lsb_first(byte: int, width: int = 8) -> list[bool]:
    return [bool((byte >> i) & 1) for i in range(width)]


# ---------------------------------------------------------------------------
# UART (+ SBUS as a parameterized frame variant)
# ---------------------------------------------------------------------------

UART_IDLE_LEAD_BITS = 4
UART_IDLE_GAP_BITS = 3
UART_IDLE_TRAIL_BITS = 4


class SimpleUARTGenerator(Generator):
    """UART generator - arbitrary baud, parameterized 8N1-family frames.

    Idle-high line; each frame is start bit (low) + data_bits (LSB first) +
    optional parity bit + stop_bits (high). SBUS is just this generator with
    baud=100000, parity="even", stop_bits=2 (8E2) - see `sbus()`.
    """

    def __init__(
        self,
        baud: int = 9600,
        payload: list[int] | None = None,
        data_bits: int = 8,
        parity: str = "none",
        stop_bits: float = 1.0,
        sample_rate_hz: int = DEFAULT_SAMPLE_RATE_HZ,
        seed: int = 0,
    ):
        super().__init__(seed)
        self.baud = baud
        self.payload = payload or [0x55]
        self.data_bits = data_bits
        self.parity = parity
        self.stop_bits = stop_bits
        self.sample_rate_hz = sample_rate_hz

    @classmethod
    def sbus(
        cls, payload: list[int] | None = None, seed: int = 0
    ) -> "SimpleUARTGenerator":
        """SBUS: 100000 baud, 8E2 (8 data bits, even parity, 2 stop bits)."""
        return cls(
            baud=100_000,
            payload=payload,
            data_bits=8,
            parity="even",
            stop_bits=2.0,
            seed=seed,
        )

    def _frame_segments(self, byte: int, bit_samples: int) -> list[tuple[bool, int]]:
        segments: list[tuple[bool, int]] = [(False, bit_samples)]  # start bit
        data_bits = byte_bits_lsb_first(byte, self.data_bits)
        for bit in data_bits:
            segments.append((bit, bit_samples))
        if self.parity != "none":
            ones = sum(data_bits)
            even_parity_bit = ones % 2
            parity_bit = (
                even_parity_bit if self.parity == "even" else 1 - even_parity_bit
            )
            segments.append((bool(parity_bit), bit_samples))
        stop_full_bits = round(self.stop_bits)
        for _ in range(stop_full_bits):
            segments.append((True, bit_samples))
        return segments

    def generate(self) -> tuple[Capture, GroundTruth]:
        bit_samples = round(self.sample_rate_hz / self.baud)
        if bit_samples < 1:
            raise ValueError(
                f"baud {self.baud} too high for sample rate {self.sample_rate_hz}"
            )

        segments: list[tuple[bool, int]] = [(True, bit_samples * UART_IDLE_LEAD_BITS)]
        for byte in self.payload:
            segments += self._frame_segments(byte, bit_samples)
            segments.append((True, bit_samples * UART_IDLE_GAP_BITS))
        segments.append((True, bit_samples * UART_IDLE_TRAIL_BITS))

        channel = expand_segments(segments)
        capture = Capture(
            channels={"ch0": channel},
            samplerate_hz=self.sample_rate_hz,
            provenance={"instrument": "synthetic", "source": "UART"},
        )
        ground_truth = GroundTruth(
            protocol="UART",
            parameters={
                "baud": self.baud,
                "data_bits": self.data_bits,
                "parity": self.parity,
                "stop_bits": self.stop_bits,
                "bit_samples": bit_samples,
                "sample_rate_hz": self.sample_rate_hz,
            },
            payload=self.payload,
            seed=self.seed,
        )
        return capture, ground_truth


# ---------------------------------------------------------------------------
# I2C
# ---------------------------------------------------------------------------


class _I2CBuilder:
    """Bit-bangs SCL/SDA run-length segments for an I2C transaction."""

    def __init__(self, quarter_period_samples: int):
        self.q = quarter_period_samples
        self.scl_segments: list[tuple[bool, int]] = []
        self.sda_segments: list[tuple[bool, int]] = []

    def _emit(self, scl_level: bool, sda_level: bool, samples: int) -> None:
        self.scl_segments.append((scl_level, samples))
        self.sda_segments.append((sda_level, samples))

    def idle(self, samples: int) -> None:
        self._emit(True, True, samples)

    def start(self) -> None:
        self._emit(True, True, self.q)  # settle idle
        self._emit(True, False, self.q)  # SDA falls while SCL high: START
        self._emit(False, False, self.q * 2)  # SCL drops to begin clocking

    def bit(self, value: bool) -> None:
        self._emit(False, value, self.q)  # setup while SCL low
        self._emit(True, value, self.q * 2)  # data valid while SCL high
        self._emit(False, value, self.q)  # SCL falls, next bit may change SDA

    def byte(self, value: int, ack: bool = True, stretch_samples: int = 0) -> None:
        for bit in byte_bits_msb_first(value):
            self.bit(bit)
        # ACK/NAK: SDA low = ACK (slave pulls down), high = NAK
        self.bit(not ack)
        if stretch_samples:
            # Clock stretching: slave holds SCL low past the nominal low phase.
            self._emit(False, False, stretch_samples)

    def stop(self) -> None:
        self._emit(False, False, self.q)
        self._emit(True, False, self.q * 2)  # SCL high, SDA low held
        self._emit(True, True, self.q)  # SDA rises while SCL high: STOP

    def build(self, sample_rate_hz: int, provenance_source: str) -> Capture:
        return Capture(
            channels={
                "scl": expand_segments(self.scl_segments),
                "sda": expand_segments(self.sda_segments),
            },
            samplerate_hz=sample_rate_hz,
            provenance={"instrument": "synthetic", "source": provenance_source},
        )


class SimpleI2CGenerator(Generator):
    """I2C generator - start/stop conditions, 7-bit address, ACK/NAK, payload."""

    def __init__(
        self,
        address: int = 0x55,
        payload: list[int] | None = None,
        rw: int = 0,
        speed_hz: int = 100_000,
        clock_stretching: bool = False,
        sample_rate_hz: int = DEFAULT_SAMPLE_RATE_HZ,
        seed: int = 0,
    ):
        super().__init__(seed)
        self.address = address
        self.payload = payload or [0xAA]
        self.rw = rw
        self.speed_hz = speed_hz
        self.clock_stretching = clock_stretching
        self.sample_rate_hz = sample_rate_hz

    def generate(self) -> tuple[Capture, GroundTruth]:
        period_samples = round(self.sample_rate_hz / self.speed_hz)
        q = max(1, period_samples // 4)
        stretch_samples = q * 2 if self.clock_stretching else 0

        builder = _I2CBuilder(q)
        builder.idle(q * 4)
        builder.start()
        addr_rw = ((self.address & 0x7F) << 1) | (self.rw & 1)
        builder.byte(addr_rw, ack=True, stretch_samples=stretch_samples)
        for byte in self.payload:
            builder.byte(byte, ack=True, stretch_samples=stretch_samples)
        builder.stop()
        builder.idle(q * 4)

        capture = builder.build(self.sample_rate_hz, "I2C")
        ground_truth = GroundTruth(
            protocol="I2C",
            parameters={
                "address": self.address,
                "rw": self.rw,
                "speed_hz": self.speed_hz,
                "clock_stretching": self.clock_stretching,
                "quarter_period_samples": q,
                "sample_rate_hz": self.sample_rate_hz,
            },
            payload=self.payload,
            seed=self.seed,
        )
        return capture, ground_truth


# ---------------------------------------------------------------------------
# SPI
# ---------------------------------------------------------------------------


class SimpleSPIGenerator(Generator):
    """SPI generator - all four CPOL/CPHA modes, CS framing, MOSI data."""

    def __init__(
        self,
        cpol: int = 0,
        cpha: int = 0,
        payload: list[int] | None = None,
        speed_hz: int = 1_000_000,
        sample_rate_hz: int = DEFAULT_SAMPLE_RATE_HZ,
        seed: int = 0,
    ):
        super().__init__(seed)
        if cpol not in (0, 1) or cpha not in (0, 1):
            raise ValueError("cpol and cpha must each be 0 or 1")
        self.cpol = cpol
        self.cpha = cpha
        self.payload = payload or [0x55]
        self.speed_hz = speed_hz
        self.sample_rate_hz = sample_rate_hz

    def _bit_phase_segments(
        self, bit: bool, q: int
    ) -> tuple[list[tuple[bool, int]], list[tuple[bool, int]]]:
        clock_idle = bool(self.cpol)
        clock_active = not clock_idle
        if self.cpha == 0:
            # Data set up while clock idle (leading edge samples it).
            clk = [(clock_idle, q), (clock_active, q)]
        else:
            # Data set up at the leading edge; trailing edge samples it.
            clk = [(clock_active, q), (clock_idle, q)]
        mosi = [(bit, q), (bit, q)]
        return clk, mosi

    def generate(self) -> tuple[Capture, GroundTruth]:
        period_samples = round(self.sample_rate_hz / self.speed_hz)
        q = max(1, period_samples // 2)
        lead = q * 2
        trail = q * 2
        idle_gap = q * 4
        clock_idle = bool(self.cpol)

        clk_segments: list[tuple[bool, int]] = [(clock_idle, idle_gap)]
        mosi_segments: list[tuple[bool, int]] = [(False, idle_gap)]
        cs_segments: list[tuple[bool, int]] = [(True, idle_gap)]

        clk_segments.append((clock_idle, lead))
        mosi_segments.append((False, lead))
        burst_samples = lead

        for byte in self.payload:
            for bit in byte_bits_msb_first(byte):
                clk, mosi = self._bit_phase_segments(bit, q)
                clk_segments += clk
                mosi_segments += mosi
                burst_samples += 2 * q

        clk_segments.append((clock_idle, trail))
        mosi_segments.append((False, trail))
        burst_samples += trail

        clk_segments.append((clock_idle, idle_gap))
        mosi_segments.append((False, idle_gap))

        cs_segments.append((False, burst_samples))
        cs_segments.append((True, idle_gap))

        mosi_array = expand_segments(mosi_segments)
        if self.cpha == 1:
            # CPHA=1 changes data exactly on the leading edge (zero setup
            # margin by definition), so a wrong-CPHA (leading-edge) decode
            # would coincidentally sample the just-changed value instead of
            # the previous bit's. A minimal realistic propagation delay
            # breaks that coincidence. CPHA=0 already has full setup margin
            # on its sample (leading) edge, and its data-change edge
            # (trailing) is where a wrong-CPHA decode correctly reads the
            # adjacent bit - no delay needed there.
            mosi_array = np.concatenate([mosi_array[:1], mosi_array[:-1]])

        capture = Capture(
            channels={
                "sck": expand_segments(clk_segments),
                "mosi": mosi_array,
                "cs": expand_segments(cs_segments),
            },
            samplerate_hz=self.sample_rate_hz,
            provenance={"instrument": "synthetic", "source": "SPI"},
        )
        ground_truth = GroundTruth(
            protocol="SPI",
            parameters={
                "cpol": self.cpol,
                "cpha": self.cpha,
                "speed_hz": self.speed_hz,
                "quarter_period_samples": q,
                "sample_rate_hz": self.sample_rate_hz,
            },
            payload=self.payload,
            seed=self.seed,
        )
        return capture, ground_truth


# ---------------------------------------------------------------------------
# WS2812
# ---------------------------------------------------------------------------

# Datasheet nominal cell timing (WS2812B): 800 kHz bit rate, ±150 ns windows.
WS2812_T0H_NS = 400
WS2812_T1H_NS = 800
WS2812_PERIOD_NS = 1250  # 800 kHz
WS2812_RESET_NS = 60_000  # >= 50 us low latches the reset code


class SimpleWS2812Generator(Generator):
    """WS2812 generator - spec-exact 800 kHz cells at the given sample rate."""

    def __init__(
        self,
        payload: list[int] | None = None,
        sample_rate_hz: int = DEFAULT_SAMPLE_RATE_HZ,
        seed: int = 0,
    ):
        super().__init__(seed)
        self.payload = payload or [0x55]
        self.sample_rate_hz = sample_rate_hz

    def generate(self) -> tuple[Capture, GroundTruth]:
        sample_ns = 1e9 / self.sample_rate_hz
        bit_period_samples = round(WS2812_PERIOD_NS / sample_ns)
        t0h_samples = round(WS2812_T0H_NS / sample_ns)
        t1h_samples = round(WS2812_T1H_NS / sample_ns)
        t0l_samples = bit_period_samples - t0h_samples
        t1l_samples = bit_period_samples - t1h_samples
        reset_samples = round(WS2812_RESET_NS / sample_ns)

        segments: list[tuple[bool, int]] = [
            (False, bit_period_samples)
        ]  # idle low lead-in
        for byte in self.payload:
            for bit in byte_bits_msb_first(byte):
                if bit:
                    segments.append((True, t1h_samples))
                    segments.append((False, t1l_samples))
                else:
                    segments.append((True, t0h_samples))
                    segments.append((False, t0l_samples))
        segments.append((False, reset_samples))

        channel = expand_segments(segments)
        capture = Capture(
            channels={"din": channel},
            samplerate_hz=self.sample_rate_hz,
            provenance={"instrument": "synthetic", "source": "WS2812"},
        )
        ground_truth = GroundTruth(
            protocol="WS2812",
            parameters={
                "bit_period_samples": bit_period_samples,
                "t0h_samples": t0h_samples,
                "t1h_samples": t1h_samples,
                "t0l_samples": t0l_samples,
                "t1l_samples": t1l_samples,
                "sample_rate_hz": self.sample_rate_hz,
            },
            payload=self.payload,
            seed=self.seed,
        )
        return capture, ground_truth


# ---------------------------------------------------------------------------
# PWM / servo
# ---------------------------------------------------------------------------


class SimplePWMGenerator(Generator):
    """PWM/servo generator - fixed frame rate, ground-truth pulse width."""

    def __init__(
        self,
        freq_hz: float = 50.0,
        pulse_us: float = 1500.0,
        num_pulses: int = 3,
        sample_rate_hz: int = DEFAULT_SAMPLE_RATE_HZ,
        seed: int = 0,
    ):
        super().__init__(seed)
        self.freq_hz = freq_hz
        self.pulse_us = pulse_us
        self.num_pulses = num_pulses
        self.sample_rate_hz = sample_rate_hz

    def generate(self) -> tuple[Capture, GroundTruth]:
        period_samples = round(self.sample_rate_hz / self.freq_hz)
        pulse_samples = round(self.pulse_us * 1e-6 * self.sample_rate_hz)
        if pulse_samples >= period_samples:
            raise ValueError("pulse_us must be shorter than one PWM period")

        segments: list[tuple[bool, int]] = [(False, period_samples - pulse_samples)]
        for _ in range(self.num_pulses):
            segments.append((True, pulse_samples))
            segments.append((False, period_samples - pulse_samples))

        channel = expand_segments(segments)
        capture = Capture(
            channels={"pwm": channel},
            samplerate_hz=self.sample_rate_hz,
            provenance={"instrument": "synthetic", "source": "PWM"},
        )
        ground_truth = GroundTruth(
            protocol="PWM",
            parameters={
                "freq_hz": self.freq_hz,
                "pulse_us": self.pulse_us,
                "period_samples": period_samples,
                "pulse_samples": pulse_samples,
                "sample_rate_hz": self.sample_rate_hz,
            },
            payload=None,
            seed=self.seed,
        )
        return capture, ground_truth


# ---------------------------------------------------------------------------
# DShot
# ---------------------------------------------------------------------------
#
# Timing table and checksum live in slidko.measure.dshot (production code
# needs them for recognition too) - re-exported here so existing imports of
# `tests.synth.DSHOT_TIMING_NS` / `dshot_checksum` keep working.


class SimpleDShotGenerator(Generator):
    """DShot150/300/600 frame generator - spec-exact bit timing per
    docs/EXERCISER.md."""

    def __init__(
        self,
        rate: int = 150,
        value: int = 1000,
        telemetry: bool = False,
        repeat: int = 1,
        sample_rate_hz: int = DEFAULT_SAMPLE_RATE_HZ,
        seed: int = 0,
    ):
        super().__init__(seed)
        if rate not in DSHOT_TIMING_NS:
            raise ValueError(f"unsupported DShot rate: {rate}")
        if not (0 <= value <= 0x7FF):
            raise ValueError("DShot value must fit in 11 bits (0-2047)")
        self.rate = rate
        self.value = value
        self.telemetry = telemetry
        self.repeat = repeat
        self.sample_rate_hz = sample_rate_hz

    def generate(self) -> tuple[Capture, GroundTruth]:
        timing = DSHOT_TIMING_NS[self.rate]
        sample_ns = 1e9 / self.sample_rate_hz
        bit_period_samples = round(timing["bit_period_ns"] / sample_ns)
        t0h_samples = round(timing["t0h_ns"] / sample_ns)
        t1h_samples = round(timing["t1h_ns"] / sample_ns)
        t0l_samples = bit_period_samples - t0h_samples
        t1l_samples = bit_period_samples - t1h_samples
        gap_samples = round(DSHOT_FRAME_GAP_NS / sample_ns)

        data12 = (self.value << 1) | (1 if self.telemetry else 0)
        crc = dshot_checksum(data12)
        frame16 = (data12 << 4) | crc

        segments: list[tuple[bool, int]] = [(False, gap_samples)]
        for _ in range(self.repeat):
            for bit in byte_bits_msb_first(frame16, 16):
                if bit:
                    segments.append((True, t1h_samples))
                    segments.append((False, t1l_samples))
                else:
                    segments.append((True, t0h_samples))
                    segments.append((False, t0l_samples))
            segments.append((False, gap_samples))

        channel = expand_segments(segments)
        capture = Capture(
            channels={"dshot": channel},
            samplerate_hz=self.sample_rate_hz,
            provenance={"instrument": "synthetic", "source": "DShot"},
        )
        ground_truth = GroundTruth(
            protocol="DShot",
            parameters={
                "rate": self.rate,
                "value": self.value,
                "telemetry": self.telemetry,
                "crc": crc,
                "frame16": frame16,
                "bit_period_samples": bit_period_samples,
                "t0h_samples": t0h_samples,
                "t1h_samples": t1h_samples,
                "sample_rate_hz": self.sample_rate_hz,
            },
            payload=[self.value],
            seed=self.seed,
        )
        return capture, ground_truth


# ---------------------------------------------------------------------------
# Fault / jitter injection
#
# Operates post-hoc on any (Capture, GroundTruth) pair from the generators
# above: run-length-decode the target channel, perturb it, re-encode, and
# record the fault in the ground-truth label so the smoke detector's tests
# (and any discriminator jitter-degradation test) can consume dirty
# synthetics with a machine-readable answer key.
# ---------------------------------------------------------------------------


def _with_channel(capture: Capture, channel_name: str, channel: np.ndarray) -> Capture:
    new_channels = dict(capture.channels)
    new_channels[channel_name] = channel
    return Capture(
        channels=new_channels,
        samplerate_hz=capture.samplerate_hz,
        provenance=capture.provenance,
    )


def _with_fault(ground_truth: GroundTruth, fault: dict) -> GroundTruth:
    faults = [*list(ground_truth.injected_faults or []), fault]
    return replace(ground_truth, injected_faults=faults)


def inject_jitter(
    capture: Capture,
    ground_truth: GroundTruth,
    channel_name: str,
    jitter_frac: float,
    seed: int = 0,
) -> tuple[Capture, GroundTruth]:
    """Perturb every run length on `channel_name` by up to +/- jitter_frac
    (uniform, seeded) - reproducible per-edge timing jitter."""
    rng = np.random.default_rng(seed)
    segments = channel_to_segments(capture.channels[channel_name])
    jittered = [
        (level, max(1, round(count * (1 + rng.uniform(-jitter_frac, jitter_frac)))))
        for level, count in segments
    ]
    new_capture = _with_channel(capture, channel_name, expand_segments(jittered))
    new_ground_truth = _with_fault(
        ground_truth,
        {
            "kind": "jitter",
            "channel": channel_name,
            "jitter_frac": jitter_frac,
            "seed": seed,
        },
    )
    return new_capture, new_ground_truth


def inject_glitches(
    capture: Capture,
    ground_truth: GroundTruth,
    channel_name: str,
    count: int,
    pulse_samples: int = 1,
    seed: int = 0,
) -> tuple[Capture, GroundTruth]:
    """Insert `count` runt/glitch pulses (brief opposite-polarity blips, each
    `pulse_samples` wide) at random positions - reproducibly seeded."""
    rng = np.random.default_rng(seed)
    channel = capture.channels[channel_name].copy()
    n = len(channel)
    affected: list[int] = []

    valid_positions = n - pulse_samples - 1
    if valid_positions > 1:
        num_glitches = min(count, valid_positions - 1)
        positions = rng.choice(
            np.arange(1, valid_positions), size=num_glitches, replace=False
        )
        for pos in sorted(int(p) for p in positions):
            channel[pos : pos + pulse_samples] = ~channel[pos : pos + pulse_samples]
            affected.append(pos)

    new_capture = _with_channel(capture, channel_name, channel)
    new_ground_truth = _with_fault(
        ground_truth,
        {
            "kind": "glitch",
            "channel": channel_name,
            "pulse_samples": pulse_samples,
            "affected_indices": affected,
            "seed": seed,
        },
    )
    return new_capture, new_ground_truth


def inject_ws2812_violation(
    capture: Capture,
    ground_truth: GroundTruth,
    channel_name: str,
    bit_index: int,
    violation_ns: int = 300,
) -> tuple[Capture, GroundTruth]:
    """Deliberately push one WS2812 bit's high time outside its +/-150 ns
    spec window by `violation_ns`, recording the violation class and the
    affected bit index in the ground-truth label."""
    channel = capture.channels[channel_name]
    segments = channel_to_segments(channel)
    sample_ns = 1e9 / capture.samplerate_hz
    violation_samples = max(1, round(violation_ns / sample_ns))

    # Segment 0 is the idle-low lead-in; each bit cell is a (high, low) pair
    # after that.
    cell_start = 1 + bit_index * 2
    if cell_start >= len(segments) - 1:
        raise ValueError(f"bit_index {bit_index} out of range for this capture")
    level, high_samples = segments[cell_start]
    if not level:
        raise ValueError(f"segment at bit_index {bit_index} is not a high phase")
    segments[cell_start] = (level, high_samples + violation_samples)

    new_capture = _with_channel(capture, channel_name, expand_segments(segments))
    new_ground_truth = _with_fault(
        ground_truth,
        {
            "kind": "ws2812_timing_violation",
            "channel": channel_name,
            "bit_index": bit_index,
            "violation_ns": violation_ns,
        },
    )
    return new_capture, new_ground_truth
