#ifndef PARSER_H
#define PARSER_H

#include "command.h"
#include <stddef.h>

// Parse a JSON command string into a command_t structure
// Returns 0 on success, non-zero on failure
int parse_command(const char* input_line, command_t* cmd);

// Serialize a response to a JSON string
// Returns 0 on success, non-zero on failure
int serialize_response(const response_t* resp, char* output_buffer, size_t buffer_size);

#endif // PARSER_H
