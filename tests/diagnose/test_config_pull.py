"""
Config pull - READ-ONLY by construction (design.md § Config pull, task
group 5). No serial I/O; frame construction only. No DUT is contacted in
tests.
"""

import inspect

import pytest

from slidko.diagnose import config_pull
from slidko.diagnose.config_pull import (
    MspReadCommand,
    ProductBoundaryError,
    build_read_request,
)

# The design.md read allowlist, verbatim.
DESIGN_MD_READ_IDS = {
    1,  # MSP_API_VERSION
    2,  # MSP_FC_VARIANT
    3,  # MSP_FC_VERSION
    4,  # MSP_BOARD_INFO
    5,  # MSP_BUILD_INFO
    54,  # MSP_CF_SERIAL_CONFIG
    36,  # MSP_FEATURE_CONFIG
    44,  # MSP_RX_CONFIG
    64,  # MSP_RX_MAP
    84,  # MSP_OSD_CONFIG
    88,  # MSP_VTX_CONFIG
    101,  # MSP_STATUS
    110,  # MSP_ANALOG
    130,  # MSP_BATTERY_STATE
    160,  # MSP_UID
}

# Known MSP_SET_* / write command IDs (betaflight/src/main/msp/msp_protocol.h)
# that must never be constructible.
MSP_SET_PID = 202
MSP_RESET_CONF = 208


def test_msp_status_read_request_frame_is_correct():
    """MSP_STATUS (id 101): $M< frame, size 0, correct XOR checksum."""
    frame = build_read_request(MspReadCommand.STATUS)

    assert frame[0:3] == b"$M<"
    size = frame[3]
    cmd = frame[4]
    checksum = frame[5]
    assert size == 0
    assert cmd == 101
    assert checksum == (size ^ cmd)
    assert len(frame) == 6  # header(3) + size + cmd + checksum, no payload


def test_all_allowlisted_commands_build_valid_frames():
    for command in MspReadCommand:
        frame = build_read_request(command)
        assert frame[0:3] == b"$M<"
        assert frame[3] == 0
        assert frame[4] == command.value
        assert frame[5] == command.value  # checksum = 0 ^ cmd for reads


def test_write_shaped_command_raises_product_boundary_error():
    """Requesting MSP_SET_PID (202), outside the read allowlist, raises
    ProductBoundaryError."""
    with pytest.raises(ProductBoundaryError):
        build_read_request(MSP_SET_PID)


def test_reset_conf_raises_product_boundary_error():
    with pytest.raises(ProductBoundaryError):
        build_read_request(MSP_RESET_CONF)


def test_arbitrary_unrecognized_id_raises_product_boundary_error():
    with pytest.raises(ProductBoundaryError):
        build_read_request(9999)


def test_allowlist_matches_design_md_exactly():
    """The allowlist contains exactly the design.md read IDs and none from
    the MSP_SET_* range (task 5.3)."""
    allowlist_ids = {command.value for command in MspReadCommand}

    assert allowlist_ids == DESIGN_MD_READ_IDS
    # MSP_SET_* family starts at 200+ in betaflight/src/main/msp/msp_protocol.h
    assert not any(cmd_id >= 200 for cmd_id in allowlist_ids)


def test_public_api_exposes_no_write_flash_set_function():
    """Inspect the module's public callables: none may write/flash/set/
    program anything - config pull is read-only by construction."""
    suspicious_prefixes = ("write", "set_", "flash", "program", "erase", "reset")
    public_callables = [
        name
        for name, obj in inspect.getmembers(config_pull)
        if not name.startswith("_")
        and (inspect.isfunction(obj) or inspect.isclass(obj))
    ]

    assert public_callables  # sanity: the module has a public surface
    for name in public_callables:
        lowered = name.lower()
        assert not any(lowered.startswith(prefix) for prefix in suspicious_prefixes), (
            f"{name} looks like a write-capable function - config pull must "
            "be read-only by construction"
        )


if __name__ == "__main__":
    pytest.main([__file__])
