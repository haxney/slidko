"""Glue between Measure's classifier output and Decode's backend interface.

`measure.classify.classify()` and `decode.backend.ProtocolHypothesis` were
designed independently (design.md § ProtocolHypothesis); this module is the
zero-configuration seam design.md calls for: Measure infers, Decode consumes,
no manual parameters in between.
"""

from slidko.decode.backend import ProtocolHypothesis
from slidko.measure.classify import Claim

SPI_DEFAULT_WORDSIZE = 8


def hypothesis_from_claim(claim: Claim) -> ProtocolHypothesis:
    """Adapt a Measure `Claim` into the `ProtocolHypothesis` shape a Decode
    backend expects, per protocol.

    SPI is the one lossy mapping: Measure's single-ended `classify_spi`
    identifies one `data` channel (it cannot distinguish MOSI from MISO from
    a single line), which is assumed to be MOSI; `miso` is left unset.
    """
    protocol = claim.protocol.lower()

    if protocol == "uart":
        rx_channel = claim.channels["rx"]
        parameters = {
            "baud": claim.parameters["baud"],
            "data_bits": claim.parameters.get("data_bits", 8),
            "parity": claim.parameters.get("parity", "none"),
            "stop_bits": claim.parameters.get("stop_bits", 1.0),
            "rx_channel": rx_channel,
        }
        return ProtocolHypothesis(
            protocol="uart",
            parameters=parameters,
            channel_assignments={"rx": rx_channel},
        )

    if protocol == "i2c":
        scl_channel = claim.channels["scl"]
        sda_channel = claim.channels["sda"]
        return ProtocolHypothesis(
            protocol="i2c",
            parameters={"scl_channel": scl_channel, "sda_channel": sda_channel},
            channel_assignments={"scl": scl_channel, "sda": sda_channel},
        )

    if protocol == "spi":
        clk_channel = claim.channels["clk"]
        mosi_channel = claim.channels.get("data")
        cs_channel = claim.channels.get("cs")
        parameters = {
            "clk": clk_channel,
            "mosi": mosi_channel,
            "miso": None,
            "cs": cs_channel,
            "cpol": claim.parameters.get("cpol", 0),
            "cpha": claim.parameters.get("cpha", 0),
            "wordsize": SPI_DEFAULT_WORDSIZE,
        }
        channel_assignments = {"clk": clk_channel}
        if mosi_channel is not None:
            channel_assignments["mosi"] = mosi_channel
        if cs_channel is not None:
            channel_assignments["cs"] = cs_channel

        return ProtocolHypothesis(
            protocol="spi",
            parameters=parameters,
            channel_assignments=channel_assignments,
        )

    raise ValueError(f"No Decode hypothesis mapping for protocol {claim.protocol!r}")
