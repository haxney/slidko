#ifndef HAZARD_H
#define HAZARD_H

#include "command.h"

// 0 if `cmd` passes the hazard envelope, non-zero if it must be refused.
// Push-pull stimulus commands (see command_is_push_pull) are refused unless
// `cmd->assert_undriven` is set; open-drain bus-master ops (i2c_scan,
// i2c_read) and non-stimulus commands are always allowed here (their own
// per-command validation, if any, happens elsewhere).
int hazard_check(const command_t *cmd);

#endif // HAZARD_H
