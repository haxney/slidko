#ifndef HW_E9_DETECT_H
#define HW_E9_DETECT_H

#include "e9_policy.h"

// Detects the RP2350 silicon stepping at boot and returns whether the E9
// erratum applies (true on A2, false on A4). Always false when built for
// RP2040 (`pico` target) -- E9 is RP2350-specific silicon, not applicable.
//
// CONFIDENCE: MODERATE, per EXERCISER.md's own caveat ("exact chip-ID/
// stepping read path should be verified against the current pico-sdk and
// RP2350 datasheet... before trusting it"). Primary path uses the SDK's
// rp2350_chip_version(). Verify-on-hardware is an explicit human step; this
// function is compile-verified only in this session.
bool hw_detect_e9_affected(silicon_stepping_t *out_stepping);

#endif // HW_E9_DETECT_H
