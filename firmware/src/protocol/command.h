#ifndef COMMAND_H
#define COMMAND_H

#include <stdint.h>

// Command IDs for the v1 command set
typedef enum {
    CMD_INFO = 0,
    CMD_WS2812 = 1,
    CMD_DSHOT = 2,
    CMD_PWM = 3,
    CMD_UART_TX = 4,
    CMD_I2C_SCAN = 5,
    CMD_I2C_READ = 6,
    CMD_SPI_TX = 7,
    CMD_SYNC = 8,
    CMD_LOOPBACK = 9
} command_id_t;

// Error codes for responses
typedef enum {
    ERR_OK = 0,
    ERR_PARSE_FAILED = 1,
    ERR_E9_UNAVAILABLE = 2,
    ERR_HAZARD_VIOLATION = 3,
    ERR_INVALID_CMD = 4,
    ERR_UNSPECIFIED = 5
} error_code_t;

// Base command structure with common fields
typedef struct {
    uint32_t id;
    command_id_t cmd_id;
} base_command_t;

// Command structure definitions for each command type

// info command - no additional fields
typedef struct {
    base_command_t base;
} info_cmd_t;

// ws2812 command
typedef struct {
    base_command_t base;
    uint32_t pin;
    uint32_t count;
    uint8_t* pattern; // 3 bytes per LED (RGB)
    uint32_t repeat;
} ws2812_cmd_t;

// dshot command
typedef struct {
    base_command_t base;
    uint32_t pin;
    uint32_t rate; // DShot150/300/600
    uint32_t value;
    uint32_t repeat;
} dshot_cmd_t;

// pwm command
typedef struct {
    base_command_t base;
    uint32_t pin;
    uint32_t freq_hz;
    union {
        uint32_t duty;
        uint32_t pulse_us;
    } pulse;
    uint8_t is_pulse_us;
} pwm_cmd_t;

// uart_tx command
typedef struct {
    base_command_t base;
    uint32_t pin;
    uint32_t baud;
    uint8_t frame[16]; // up to 16 bytes for frame config
    uint8_t* payload;
    uint32_t payload_len;
    uint32_t repeat;
} uart_tx_cmd_t;

// i2c_scan command
typedef struct {
    base_command_t base;
    uint32_t sda;
    uint32_t scl;
    uint32_t speed_hz;
} i2c_scan_cmd_t;

// i2c_read command
typedef struct {
    base_command_t base;
    uint32_t sda;
    uint32_t scl;
    uint8_t addr;
    uint8_t reg;
    uint32_t len;
} i2c_read_cmd_t;

// spi_tx command
typedef struct {
    base_command_t base;
    uint32_t sck;
    uint32_t mosi;
    uint32_t cs;
    uint32_t mode;
    uint32_t speed_hz;
    uint8_t* payload;
    uint32_t payload_len;
} spi_tx_cmd_t;

// sync command
typedef struct {
    base_command_t base;
    uint32_t pin;
    uint8_t mode; // 0 = input, 1 = output
} sync_cmd_t;

// loopback command
typedef struct {
    base_command_t base;
    uint32_t generator_pin;
    uint32_t capture_pin;
} loopback_cmd_t;

// Union of all command types
typedef union {
    base_command_t base;
    info_cmd_t info;
    ws2812_cmd_t ws2812;
    dshot_cmd_t dshot;
    pwm_cmd_t pwm;
    uart_tx_cmd_t uart_tx;
    i2c_scan_cmd_t i2c_scan;
    i2c_read_cmd_t i2c_read;
    spi_tx_cmd_t spi_tx;
    sync_cmd_t sync;
    loopback_cmd_t loopback;
} command_t;

// Response structure
typedef struct {
    uint32_t id;
    uint8_t status; // 0 for ok, non-zero for error
    union {
        char* err_msg;
        info_cmd_t info_resp;
    } data;
} response_t;

#endif // COMMAND_H
