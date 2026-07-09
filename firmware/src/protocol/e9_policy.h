#ifndef E9_POLICY_H
#define E9_POLICY_H

#include "command.h"
#include <stdint.h>

// E9 policy check: returns 0 if command is allowed, non-zero if blocked by E9 policy
int e9_policy_check(const command_t* cmd, uint8_t e9_affected);

// Check if a command is input-sensing (requires E9 policy check)
int is_input_sensing_command(command_id_t cmd_id);

#endif // E9_POLICY_H
