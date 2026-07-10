#ifndef PARSER_H
#define PARSER_H

#include "command.h"

#include <stddef.h>

// Parse one JSON-lines command object into `cmd`. Returns 0 on success,
// non-zero if the line is not a well-formed object, is missing `id`/`cmd`,
// or `cmd` does not name a known v1 command. On failure `cmd->id` is best-
// effort populated from a raw `id` field if one was found, so callers can
// still echo it in an error response.
int parse_command(const char *input_line, command_t *cmd);

// Serialize a response to a JSON-lines string. Returns 0 on success, non-zero
// if `output_buffer` is too small.
int serialize_response(const response_t *resp, char *output_buffer, size_t buffer_size);

#endif // PARSER_H
