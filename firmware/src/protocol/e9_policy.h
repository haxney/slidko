#ifndef E9_POLICY_H
#define E9_POLICY_H

#include "command.h"

#include <stdbool.h>
#include <stddef.h>

// RP2350 silicon stepping, per EXERCISER.md "RP2350 E9 erratum". A2 is
// E9-affected; A4 has the hardware fix.
typedef enum {
    SILICON_UNKNOWN = 0,
    SILICON_A2 = 1,
    SILICON_A4 = 2,
} silicon_stepping_t;

typedef struct {
    const char *name;
    bool available;
} capability_t;

// True for commands (or command+mode combinations) that read a DUT-facing
// line back into the chip: `sync` in readback ("input") mode, and
// `loopback`'s closed-loop capture. E9 latches an enabled input buffer near
// ~2.1-2.2V on A2, so these are the capabilities the erratum gates -- NOT
// i2c_scan/i2c_read, which are open-drain bus-master reads unrelated to the
// RP2350's own input-buffer/pull-down pathology.
bool command_is_input_sensing(const command_t *cmd);

// 0 if `cmd` is allowed under the current E9 posture, non-zero if it must be
// refused with `e9_unavailable` (input-sensing command on an e9_affected
// chip).
int e9_policy_check(const command_t *cmd, bool e9_affected);

// Fills `out` (capacity `max`) with the `info` capability list, entries
// unavailable exactly where e9_affected disables an input-sensing feature.
// Returns the number of entries written.
size_t get_capabilities(bool e9_affected, capability_t *out, size_t max);

#endif // E9_POLICY_H
