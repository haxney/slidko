#include "e9_policy.h"
#include "command.h"

// E9 policy check: returns 0 if command is allowed, non-zero if blocked by E9 policy
int e9_policy_check(const command_t* cmd, uint8_t e9_affected) {
    // If E9 is not affected, all commands are allowed
    if (!e9_affected) {
        return 0;
    }

    // If E9 is affected, we check for input-sensing commands that should be blocked
    if (is_input_sensing_command(cmd->base.cmd_id)) {
        // Return error indicating E9 unavailable for this command
        return -1; // Blocked by E9 policy
    }
    
    // Default: allow the command
    return 0;
}

// Check if a command is input-sensing (requires E9 policy check)
int is_input_sensing_command(command_id_t cmd_id) {
    switch(cmd_id) {
        case CMD_SYNC:
            return 1;  // sync is input sensing (readback)
        case CMD_I2C_SCAN:
            // In some interpretations this might be input-sensing
            return 0;
        default:
            return 0; // Not input sensing
    }
}