from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Instrument:
    model: str
    samplerate_hz: int
    threshold_v: float
    channels: dict[str, str]


@dataclass(frozen=True)
class Driver:
    chip: str
    vdd_v: float
    series_r_ohm: float


@dataclass(frozen=True)
class Transport:
    cable: str
    length_m: float
    twisted: bool
    shielded: bool
    termination: str


@dataclass(frozen=True)
class Receiver:
    part: str
    vdd_v: float
    vih_v: float


@dataclass(frozen=True)
class Protocol:
    name: str
    nominal: dict[str, Any]


@dataclass(frozen=True)
class FaultInjected:
    class_: str  # Note: using class_ to avoid Python keyword collision
    params: dict[str, Any]


@dataclass(frozen=True)
class ReceiverVerdict:
    observed: str
    notes: str
    contemporaneous: bool


@dataclass(frozen=True)
class SweepCell:
    name: str
    axis: str
    value: float


@dataclass(frozen=True)
class Sidecar:
    id: str
    capture_file: str
    instrument: Instrument
    driver: Driver
    transport: Transport
    receiver: Receiver
    protocol: Protocol
    fault_injected: FaultInjected
    receiver_verdict: ReceiverVerdict
    sweep_cell: SweepCell | None = None
    referee: dict[str, Any] | None = None

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "Sidecar":
        """Create a Sidecar instance from JSON data, handling key name collisions."""
        # Handle the special case where "class" in JSON maps to "class_" in Python
        fault_injected_data = data.get("fault_injected", {})
        if "class" in fault_injected_data:
            fault_injected_data["class_"] = fault_injected_data.pop("class")

        # Reconstruct the nested dataclasses from JSON
        instrument = Instrument(**data["instrument"])
        driver = Driver(**data["driver"])
        transport = Transport(**data["transport"])
        receiver = Receiver(**data["receiver"])
        protocol = Protocol(**data["protocol"])
        fault_injected = FaultInjected(**fault_injected_data)
        receiver_verdict = ReceiverVerdict(**data["receiver_verdict"])

        # Handle optional fields
        sweep_cell = None
        if data.get("sweep_cell") is not None:
            sweep_cell = SweepCell(**data["sweep_cell"])

        referee = data.get("referee")

        return cls(
            id=data["id"],
            capture_file=data["capture_file"],
            instrument=instrument,
            driver=driver,
            transport=transport,
            receiver=receiver,
            protocol=protocol,
            fault_injected=fault_injected,
            receiver_verdict=receiver_verdict,
            sweep_cell=sweep_cell,
            referee=referee,
        )

    def to_json(self) -> dict[str, Any]:
        """Convert the Sidecar instance back to JSON format."""
        # Convert the dataclass to dict and handle special cases
        result = asdict(self)

        # Handle the class_ field mapping back to "class" for JSON output
        if self.fault_injected is not None:
            result["fault_injected"]["class"] = result["fault_injected"].pop(
                "class_", None
            )

        return result

    @staticmethod
    def validate(sidecar: "Sidecar") -> list[str]:
        """Validate the sidecar and return list of validation errors."""
        errors = []

        # Check that receiver_verdict is present (required field)
        if sidecar.receiver_verdict is None:
            errors.append("receiver_verdict is required")

        # Check that referee validates when present
        if sidecar.referee is not None:
            # The spec says referee validates when present but doesn't define its structure
            # Since it's reserved for dual-instrument cells, we'll accept any dict as valid
            # but this could be extended with deeper validation if needed
            pass

        return errors
