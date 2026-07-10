#include "command.h"

#include <string.h>

static const char *const COMMAND_NAMES[CMD_COUNT] = {
    [CMD_INFO] = "info",         [CMD_WS2812] = "ws2812",   [CMD_DSHOT] = "dshot",
    [CMD_PWM] = "pwm",           [CMD_UART_TX] = "uart_tx", [CMD_I2C_SCAN] = "i2c_scan",
    [CMD_I2C_READ] = "i2c_read", [CMD_SPI_TX] = "spi_tx",   [CMD_SYNC] = "sync",
    [CMD_LOOPBACK] = "loopback",
};

const char *command_name(command_id_t cmd_id) {
    if (cmd_id < 0 || cmd_id >= CMD_COUNT) {
        return "unknown";
    }
    return COMMAND_NAMES[cmd_id];
}

command_id_t command_id_from_name(const char *name) {
    if (name == NULL) {
        return CMD_UNKNOWN;
    }
    for (int i = 0; i < CMD_COUNT; i++) {
        if (strcmp(name, COMMAND_NAMES[i]) == 0) {
            return (command_id_t)i;
        }
    }
    return CMD_UNKNOWN;
}

bool command_is_push_pull(command_id_t cmd_id) {
    switch (cmd_id) {
    case CMD_WS2812:
    case CMD_DSHOT:
    case CMD_PWM:
    case CMD_UART_TX:
    case CMD_SPI_TX:
        return true;
    default:
        return false;
    }
}
