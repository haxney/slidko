#include "parser.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Minimal hand-rolled JSON-object field scanner. Not a general JSON parser:
// it assumes a single flat object per line (the v1 command schema has no
// nested objects/arrays), no escape sequences in string values, and is
// deliberately tolerant of key order and extra whitespace. Kept in
// protocol/ (no pico-sdk headers) so it is host-unit-testable.

// Find the value-start position for `"key":` in `json`, or NULL if absent.
static const char *find_value(const char *json, const char *key) {
    size_t keylen = strlen(key);
    const char *p = json;
    while ((p = strchr(p, '"')) != NULL) {
        if (strncmp(p + 1, key, keylen) == 0 && p[1 + keylen] == '"') {
            const char *colon = p + 1 + keylen + 1;
            while (*colon == ' ' || *colon == '\t') {
                colon++;
            }
            if (*colon == ':') {
                colon++;
                while (*colon == ' ' || *colon == '\t') {
                    colon++;
                }
                return colon;
            }
        }
        p++;
    }
    return NULL;
}

static int json_get_int(const char *json, const char *key, long *out) {
    const char *v = find_value(json, key);
    if (v == NULL || (*v != '-' && (*v < '0' || *v > '9'))) {
        return -1;
    }
    char *end = NULL;
    long val = strtol(v, &end, 10);
    if (end == v) {
        return -1;
    }
    *out = val;
    return 0;
}

static int json_get_bool(const char *json, const char *key, bool *out) {
    const char *v = find_value(json, key);
    if (v == NULL) {
        return -1;
    }
    if (strncmp(v, "true", 4) == 0) {
        *out = true;
        return 0;
    }
    if (strncmp(v, "false", 5) == 0) {
        *out = false;
        return 0;
    }
    return -1;
}

static int json_get_str(const char *json, const char *key, char *out, size_t out_size) {
    const char *v = find_value(json, key);
    if (v == NULL || *v != '"') {
        return -1;
    }
    v++;
    size_t n = 0;
    while (v[n] != '"' && v[n] != '\0' && n + 1 < out_size) {
        out[n] = v[n];
        n++;
    }
    if (v[n] != '"') {
        return -1; // unterminated string
    }
    out[n] = '\0';
    return 0;
}

// True if `line` (after leading whitespace) starts with '{' and, ignoring
// trailing whitespace/newline, ends with '}'. Catches truncated/malformed
// input without needing a full parse.
static bool looks_like_object(const char *line) {
    while (*line == ' ' || *line == '\t') {
        line++;
    }
    if (*line != '{') {
        return false;
    }
    size_t len = strlen(line);
    while (len > 0 && (line[len - 1] == '\n' || line[len - 1] == '\r' || line[len - 1] == ' ' ||
                       line[len - 1] == '\t')) {
        len--;
    }
    return len > 0 && line[len - 1] == '}';
}

int parse_command(const char *input_line, command_t *cmd) {
    memset(cmd, 0, sizeof(*cmd));
    cmd->cmd_id = CMD_UNKNOWN;
    if (input_line == NULL) {
        return -1;
    }

    // Best-effort id, even on later failure, so error responses can echo it.
    long id_val;
    if (json_get_int(input_line, "id", &id_val) == 0) {
        cmd->id = (uint32_t)id_val;
    }

    if (!looks_like_object(input_line)) {
        return -1;
    }
    if (json_get_int(input_line, "id", &id_val) != 0) {
        return -1;
    }
    cmd->id = (uint32_t)id_val;

    char cmd_name[16];
    if (json_get_str(input_line, "cmd", cmd_name, sizeof(cmd_name)) != 0) {
        return -1;
    }
    command_id_t cmd_id = command_id_from_name(cmd_name);
    if (cmd_id == CMD_UNKNOWN) {
        return -1;
    }
    cmd->cmd_id = cmd_id;

    bool assert_undriven = false;
    json_get_bool(input_line, "assert_undriven", &assert_undriven);
    cmd->assert_undriven = assert_undriven;

    long tmp;
    switch (cmd_id) {
    case CMD_INFO:
        break;
    case CMD_WS2812:
        if (json_get_int(input_line, "pin", &tmp) == 0) {
            cmd->pin = (uint32_t)tmp;
        }
        if (json_get_int(input_line, "count", &tmp) == 0) {
            cmd->count = (uint32_t)tmp;
        }
        if (json_get_int(input_line, "repeat", &tmp) == 0) {
            cmd->repeat = (uint32_t)tmp;
        }
        break;
    case CMD_DSHOT:
        if (json_get_int(input_line, "pin", &tmp) == 0) {
            cmd->pin = (uint32_t)tmp;
        }
        if (json_get_int(input_line, "rate", &tmp) == 0) {
            cmd->rate = (uint32_t)tmp;
        }
        if (json_get_int(input_line, "value", &tmp) == 0) {
            cmd->value = (uint32_t)tmp;
        }
        if (json_get_int(input_line, "repeat", &tmp) == 0) {
            cmd->repeat = (uint32_t)tmp;
        }
        break;
    case CMD_PWM:
        if (json_get_int(input_line, "pin", &tmp) == 0) {
            cmd->pin = (uint32_t)tmp;
        }
        if (json_get_int(input_line, "freq_hz", &tmp) == 0) {
            cmd->freq_hz = (uint32_t)tmp;
        }
        if (json_get_int(input_line, "pulse_us", &tmp) == 0) {
            cmd->pulse_us = (uint32_t)tmp;
            cmd->is_pulse_us = true;
        } else if (json_get_int(input_line, "duty", &tmp) == 0) {
            cmd->duty = (uint32_t)tmp;
            cmd->is_pulse_us = false;
        }
        break;
    case CMD_UART_TX:
        if (json_get_int(input_line, "pin", &tmp) == 0) {
            cmd->pin = (uint32_t)tmp;
        }
        if (json_get_int(input_line, "baud", &tmp) == 0) {
            cmd->baud = (uint32_t)tmp;
        }
        json_get_str(input_line, "frame", cmd->frame, sizeof(cmd->frame));
        if (json_get_str(input_line, "payload", (char *)cmd->payload, sizeof(cmd->payload)) == 0) {
            cmd->payload_len = (uint32_t)strlen((char *)cmd->payload);
        }
        if (json_get_int(input_line, "repeat", &tmp) == 0) {
            cmd->repeat = (uint32_t)tmp;
        }
        break;
    case CMD_I2C_SCAN:
        if (json_get_int(input_line, "sda", &tmp) == 0) {
            cmd->sda = (uint32_t)tmp;
        }
        if (json_get_int(input_line, "scl", &tmp) == 0) {
            cmd->scl = (uint32_t)tmp;
        }
        if (json_get_int(input_line, "speed_hz", &tmp) == 0) {
            cmd->speed_hz = (uint32_t)tmp;
        }
        break;
    case CMD_I2C_READ:
        if (json_get_int(input_line, "sda", &tmp) == 0) {
            cmd->sda = (uint32_t)tmp;
        }
        if (json_get_int(input_line, "scl", &tmp) == 0) {
            cmd->scl = (uint32_t)tmp;
        }
        if (json_get_int(input_line, "addr", &tmp) == 0) {
            cmd->addr = (uint8_t)tmp;
        }
        if (json_get_int(input_line, "reg", &tmp) == 0) {
            cmd->reg = (uint8_t)tmp;
        }
        if (json_get_int(input_line, "len", &tmp) == 0) {
            cmd->len = (uint32_t)tmp;
        }
        break;
    case CMD_SPI_TX:
        if (json_get_int(input_line, "sck", &tmp) == 0) {
            cmd->sck = (uint32_t)tmp;
        }
        if (json_get_int(input_line, "mosi", &tmp) == 0) {
            cmd->mosi = (uint32_t)tmp;
        }
        if (json_get_int(input_line, "cs", &tmp) == 0) {
            cmd->cs = (uint32_t)tmp;
        }
        if (json_get_int(input_line, "mode", &tmp) == 0) {
            cmd->mode = (uint32_t)tmp;
        }
        if (json_get_int(input_line, "speed_hz", &tmp) == 0) {
            cmd->speed_hz = (uint32_t)tmp;
        }
        if (json_get_str(input_line, "payload", (char *)cmd->payload, sizeof(cmd->payload)) == 0) {
            cmd->payload_len = (uint32_t)strlen((char *)cmd->payload);
        }
        break;
    case CMD_SYNC:
        if (json_get_int(input_line, "pin", &tmp) == 0) {
            cmd->pin = (uint32_t)tmp;
        }
        json_get_str(input_line, "mode", cmd->sync_mode, sizeof(cmd->sync_mode));
        break;
    case CMD_LOOPBACK:
        if (json_get_int(input_line, "generator_pin", &tmp) == 0) {
            cmd->generator_pin = (uint32_t)tmp;
        }
        if (json_get_int(input_line, "capture_pin", &tmp) == 0) {
            cmd->capture_pin = (uint32_t)tmp;
        }
        break;
    default:
        return -1;
    }

    return 0;
}

int serialize_response(const response_t *resp, char *output_buffer, size_t buffer_size) {
    int n;
    if (resp->status == RESP_OK) {
        n = snprintf(output_buffer, buffer_size, "{\"id\":%u,\"status\":\"ok\"}",
                     (unsigned)resp->id);
    } else {
        n = snprintf(output_buffer, buffer_size, "{\"id\":%u,\"status\":\"err\",\"reason\":\"%s\"}",
                     (unsigned)resp->id, resp->err_reason);
    }
    if (n < 0 || (size_t)n >= buffer_size) {
        return -1;
    }
    return 0;
}
