#include "dispatcher.h"
#include <stdlib.h>
#include <string.h>

int dispatch_command(const command_t* cmd, response_t* resp) {
    // Initialize the response
    resp->id = cmd->base.id;
    resp->status = ERR_OK;  // Default to success

    // Currently just return an error - we will implement proper dispatching later
    // This simulates a failing implementation for tests
    return -1;  // Indicate dispatcher failure (for now)
}
