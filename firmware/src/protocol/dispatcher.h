#ifndef DISPATCHER_H
#define DISPATCHER_H

#include "command.h"
#include "parser.h"

// Dispatch a command and generate a response
// Returns 0 on success, non-zero on failure
int dispatch_command(const command_t* cmd, response_t* resp);

#endif // DISPATCHER_H
