#include "dispatcher.h"

#include "e9_policy.h"
#include "hazard.h"
#include "parser.h"

#include <string.h>

int dispatch_command(const command_t *cmd, bool e9_affected, response_t *resp) {
    resp->id = cmd->id;
    resp->err_reason[0] = '\0';

    if (cmd->cmd_id == CMD_UNKNOWN) {
        resp->status = RESP_ERR;
        strncpy(resp->err_reason, "unknown_command", sizeof(resp->err_reason) - 1);
        return -1;
    }
    if (e9_policy_check(cmd, e9_affected) != 0) {
        resp->status = RESP_ERR;
        strncpy(resp->err_reason, "e9_unavailable", sizeof(resp->err_reason) - 1);
        return -1;
    }
    if (hazard_check(cmd) != 0) {
        resp->status = RESP_ERR;
        strncpy(resp->err_reason, "hazard_violation", sizeof(resp->err_reason) - 1);
        return -1;
    }

    resp->status = RESP_OK;
    return 0;
}

void handle_line(const char *line, bool e9_affected, response_t *resp) {
    command_t cmd;
    if (parse_command(line, &cmd) != 0) {
        resp->id = cmd.id; // best-effort, 0 if not recoverable
        resp->status = RESP_ERR;
        strncpy(resp->err_reason, "parse_error", sizeof(resp->err_reason) - 1);
        return;
    }
    dispatch_command(&cmd, e9_affected, resp);
}
