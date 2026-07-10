#ifndef COMMAND_H
#define COMMAND_H

#include <stdbool.h>
#include <stdint.h>

// v1 command set (EXERCISER.md "Command interface")
typedef enum {
    CMD_UNKNOWN = -1,
    CMD_INFO = 0,
    CMD_WS2812 = 1,
    CMD_DSHOT = 2,
    CMD_PWM = 3,
    CMD_UART_TX = 4,
    CMD_I2C_SCAN = 5,
    CMD_I2C_READ = 6,
    CMD_SPI_TX = 7,
    CMD_SYNC = 8,
    CMD_LOOPBACK = 9,
    CMD_COUNT = 10
} command_id_t;

typedef enum { RESP_OK = 0, RESP_ERR = 1 } response_status_t;

#define COMMAND_MAX_PAYLOAD 64
#define COMMAND_MAX_FRAME 16
#define COMMAND_MAX_MODE 8
#define COMMAND_MAX_ERR_REASON 32

// Flattened command struct: only the fields relevant to `cmd_id` are
// populated. A hand-rolled parser (see parser.c) fills this directly from a
// JSON-lines input; there is no per-command dynamic allocation so the whole
// pipeline stays interrupt/embedded friendly.
typedef struct {
    uint32_t id;
    command_id_t cmd_id;

    // Hazard-envelope assertion (push-pull commands only; see hazard.c)
    bool assert_undriven;

    // Pin/bus fields
    uint32_t pin;
    uint32_t sda;
    uint32_t scl;
    uint32_t sck;
    uint32_t mosi;
    uint32_t cs;
    uint32_t generator_pin;
    uint32_t capture_pin;

    // ws2812
    uint32_t count;
    uint32_t repeat;

    // dshot
    uint32_t rate;
    uint32_t value;

    // pwm
    uint32_t freq_hz;
    bool is_pulse_us;
    uint32_t duty;
    uint32_t pulse_us;

    // uart_tx
    uint32_t baud;
    char frame[COMMAND_MAX_FRAME];
    uint8_t payload[COMMAND_MAX_PAYLOAD];
    uint32_t payload_len;

    // i2c_scan / i2c_read
    uint32_t speed_hz;
    uint8_t addr;
    uint8_t reg;
    uint32_t len;

    // spi_tx
    uint32_t mode;

    // sync: mode is "input" (readback) or "output" (marker toggle)
    char sync_mode[COMMAND_MAX_MODE];
} command_t;

typedef struct {
    uint32_t id;
    response_status_t status;
    char err_reason[COMMAND_MAX_ERR_REASON];
} response_t;

// Canonical name for a command id, e.g. CMD_WS2812 -> "ws2812". Returns
// "unknown" for CMD_UNKNOWN.
const char *command_name(command_id_t cmd_id);

// Reverse of command_name(); returns CMD_UNKNOWN if no match.
command_id_t command_id_from_name(const char *name);

// Push-pull stimulus commands (ws2812/dshot/pwm/uart_tx/spi_tx) require the
// hazard-envelope `assert_undriven` field; open-drain bus-master ops
// (i2c_scan/i2c_read) and non-stimulus commands do not.
bool command_is_push_pull(command_id_t cmd_id);

#endif // COMMAND_H
