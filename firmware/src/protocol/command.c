#include "command.h"

// Placeholder implementations for the command structure
// These don't do anything useful but exist to help the test compile

const char* get_command_name(command_id_t cmd_id) {
    switch(cmd_id) {
        case CMD_INFO: return "info";
        case CMD_WS2812: return "ws2812";
        case CMD_DSHOT: return "dshot";
        case CMD_PWM: return "pwm";
        case CMD_UART_TX: return "uart_tx";
        case CMD_I2C_SCAN: return "i2c_scan";
        case CMD_I2C_READ: return "i2c_read";
        case CMD_SPI_TX: return "spi_tx";
        case CMD_SYNC: return "sync";
        case CMD_LOOPBACK: return "loopback";
        default: return "unknown";
    }
}
