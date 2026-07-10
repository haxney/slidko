#include "hazard.h"

int hazard_check(const command_t *cmd) {
    if (command_is_push_pull(cmd->cmd_id) && !cmd->assert_undriven) {
        return -1;
    }
    return 0;
}
