"""Config pull: READ-ONLY DUT configuration interrogation over documented
protocols (design.md § Config pull). CLAUDE.md guardrail 4 is a
product-premise boundary, enforced structurally here, not by convention:
the module builds requests ONLY for an allowlist of read-only MSP v1
command IDs and has NO code path that constructs a write/set/flash frame.
Any request for a command outside the allowlist raises
`ProductBoundaryError`. No serial I/O - frame construction only.

Reference protocol: Betaflight/iNav MSP v1 (betaflight/src/main/msp/
msp_protocol.h). Request frame: `$` `M` `<` `<size>` `<cmd>` `<payload...>`
`<checksum>`, checksum = XOR of size, cmd, and payload bytes. Read requests
carry size 0 and no payload.
"""

from enum import IntEnum


class MspReadCommand(IntEnum):
    """The ENTIRE set of MSP v1 commands config_pull can request - this
    allowlist IS the guard (design.md: allowlist, not blocklist). Every
    MSP_SET_*/MSP_EEPROM_WRITE/write command is deliberately absent."""

    API_VERSION = 1
    FC_VARIANT = 2
    FC_VERSION = 3
    BOARD_INFO = 4
    BUILD_INFO = 5
    FEATURE_CONFIG = 36
    RX_CONFIG = 44
    CF_SERIAL_CONFIG = 54
    RX_MAP = 64
    OSD_CONFIG = 84
    VTX_CONFIG = 88
    STATUS = 101
    ANALOG = 110
    BATTERY_STATE = 130
    UID = 160


class ProductBoundaryError(Exception):
    """Raised when a caller attempts to route any command outside the
    read-only allowlist through config pull. This is a product-premise
    boundary (CLAUDE.md guardrail 4: no DUT write/control capability,
    ever) - not a recoverable-by-retry error."""


def build_read_request(command: int) -> bytes:
    """Build an MSP v1 read request frame for an allowlisted command.

    Raises ProductBoundaryError for any command not in MspReadCommand,
    including known write commands (e.g. MSP_SET_PID=202) and arbitrary
    unrecognized IDs alike - the allowlist is the guard.
    """
    try:
        MspReadCommand(command)
    except ValueError as exc:
        raise ProductBoundaryError(
            f"command {command} is not in the read-only allowlist"
        ) from exc

    size = 0  # read requests carry no payload
    checksum = size ^ command
    return bytes([ord("$"), ord("M"), ord("<"), size, command, checksum])
