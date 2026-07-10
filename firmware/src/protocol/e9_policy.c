#include "e9_policy.h"

#include <string.h>

bool command_is_input_sensing(const command_t *cmd) {
    switch (cmd->cmd_id) {
    case CMD_LOOPBACK:
        return true;
    case CMD_SYNC:
        return strcmp(cmd->sync_mode, "input") == 0;
    default:
        return false;
    }
}

int e9_policy_check(const command_t *cmd, bool e9_affected) {
    if (e9_affected && command_is_input_sensing(cmd)) {
        return -1;
    }
    return 0;
}

// Capability list advertised by `info`. Entries are feature names, not raw
// command names 1:1: `sync` splits into its always-available output-marker
// role and its E9-gated readback role.
typedef struct {
    const char *name;
    bool is_input_sensing;
} capability_entry_t;

static const capability_entry_t CAPABILITY_TABLE[] = {
    {"info", false},          {"ws2812", false},       {"dshot", false},    {"pwm", false},
    {"uart_tx", false},       {"i2c_scan", false},     {"i2c_read", false}, {"spi_tx", false},
    {"sync_stimulus", false}, {"sync_readback", true}, {"loopback", true},
};
#define CAPABILITY_COUNT (sizeof(CAPABILITY_TABLE) / sizeof(CAPABILITY_TABLE[0]))

size_t get_capabilities(bool e9_affected, capability_t *out, size_t max) {
    size_t n = 0;
    for (size_t i = 0; i < CAPABILITY_COUNT && n < max; i++) {
        out[n].name = CAPABILITY_TABLE[i].name;
        out[n].available = !(e9_affected && CAPABILITY_TABLE[i].is_input_sensing);
        n++;
    }
    return n;
}
