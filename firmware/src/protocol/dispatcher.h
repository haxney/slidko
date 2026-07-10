#ifndef DISPATCHER_H
#define DISPATCHER_H

#include "command.h"

#include <stdbool.h>

// Dispatch a successfully-parsed command: runs the E9 policy gate, then the
// hazard-envelope gate, and fills `resp`. Returns 0 if the command is
// accepted (resp->status = RESP_OK), non-zero if refused (resp->status =
// RESP_ERR with a reason).
int dispatch_command(const command_t *cmd, bool e9_affected, response_t *resp);

// Convenience wrapper: parse `line`, then dispatch it. On a parse failure,
// `resp` carries reason "parse_error" (id echoed if it could be recovered,
// else 0).
void handle_line(const char *line, bool e9_affected, response_t *resp);

#endif // DISPATCHER_H
