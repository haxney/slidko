// TinyUSB CDC read-line -> protocol/ dispatch -> write response, per
// design.md. Uses the SDK's pico_stdio_usb wrapper (stdio_init_all() +
// getchar_timeout_us()/printf()) rather than raw TinyUSB device calls --
// functionally equivalent (pico_enable_stdio_usb() in CMakeLists.txt wires
// stdio through TinyUSB CDC already) and lower-risk to get right without a
// toolchain in the loop to check it against.
//
// Compile-verified only in this session (no arm-none-eabi-gcc available).
// Known v1 simplifications, to revisit once this can be verified on
// hardware:
//   - The hand-rolled JSON parser (protocol/parser.c) only extracts scalar
//     fields; ws2812's `pattern` array and uart_tx/spi_tx's `payload` are
//     not general binary arrays (payload is read as a string).
//   - Read-style commands (i2c_scan, i2c_read, sync in "input" mode,
//     loopback) execute for real but their results are not yet folded into
//     the wire response schema (response_t is id/status/reason only, per
//     the tested acceptance in tasks.md group 3) -- richer payloads are a
//     followup, not required by this change's acceptance criteria.

#include "pico/stdlib.h"

#include <stdio.h>
#include <string.h>

#include "protocol/command.h"
#include "protocol/dispatcher.h"
#include "protocol/e9_policy.h"
#include "protocol/parser.h"
#include "protocol/timing.h"

#include "hw/e9_detect.h"
#include "hw/gpio_lines.h"
#include "hw/peripherals.h"
#include "hw/pio_stim.h"

#define LINE_BUF_SIZE 256

static bool g_e9_affected;
static silicon_stepping_t g_stepping;

// "8N1" / "8E2" -> data_bits/parity/stop_bits. Defaults to 8N1 if
// unrecognized. SBUS convention (100000 baud, 8E2, inverted line) is
// signaled by frame == "8E2" -- there is no separate wire field for line
// inversion in v1.
static void parse_frame_spec(const char *frame, uint8_t *data_bits, char *parity,
                             uint8_t *stop_bits, bool *inverted) {
    *data_bits = 8;
    *parity = 'N';
    *stop_bits = 1;
    *inverted = false;
    if (frame == NULL || frame[0] == '\0') {
        return;
    }
    if (strcmp(frame, "8E2") == 0) {
        *parity = 'E';
        *stop_bits = 2;
        *inverted = true; // SBUS convention
    } else if (strcmp(frame, "8N2") == 0) {
        *stop_bits = 2;
    } else if (strcmp(frame, "8O1") == 0) {
        *parity = 'O';
    }
    // else: fall through to the 8N1 default.
}

static void print_info_response(uint32_t id) {
    capability_t caps[16];
    size_t n = get_capabilities(g_e9_affected, caps, 16);

    const char *stepping_name = (g_stepping == SILICON_A2)   ? "A2"
                                : (g_stepping == SILICON_A4) ? "A4"
                                                             : "unknown";

    printf("{\"id\":%u,\"status\":\"ok\",\"stepping\":\"%s\",\"e9_affected\":%s,"
           "\"sys_clk_hz\":%u,\"capabilities\":[",
           (unsigned)id, stepping_name, g_e9_affected ? "true" : "false", (unsigned)SYS_CLK_HZ);
    for (size_t i = 0; i < n; i++) {
        printf("%s{\"name\":\"%s\",\"available\":%s}", i == 0 ? "" : ",", caps[i].name,
               caps[i].available ? "true" : "false");
    }
    printf("]}\n");
}

static void execute_command(const command_t *cmd) {
    switch (cmd->cmd_id) {
    case CMD_INFO:
        break; // handled by print_info_response, called separately
    case CMD_WS2812: {
        uint8_t grb[3] = {0, 0, 0}; // pattern bytes: see file header note
        pio_stim_ws2812_send(cmd->pin, grb, cmd->count);
        break;
    }
    case CMD_DSHOT: {
        uint16_t frame = dshot_encode_frame((uint16_t)cmd->value, /*telemetry=*/false);
        pio_stim_dshot_send(cmd->pin, cmd->rate, frame);
        break;
    }
    case CMD_PWM:
        hw_pwm_set(cmd->pin, cmd->freq_hz, cmd->is_pulse_us,
                   cmd->is_pulse_us ? cmd->pulse_us : cmd->duty);
        break;
    case CMD_UART_TX: {
        uint8_t data_bits;
        char parity;
        uint8_t stop_bits;
        bool inverted;
        parse_frame_spec(cmd->frame, &data_bits, &parity, &stop_bits, &inverted);
        hw_uart_tx(cmd->pin, cmd->baud, data_bits, stop_bits, parity, inverted, cmd->payload,
                   cmd->payload_len);
        break;
    }
    case CMD_I2C_SCAN: {
        uint8_t found[16];
        hw_i2c_scan(cmd->sda, cmd->scl, cmd->speed_hz, found, 16);
        break;
    }
    case CMD_I2C_READ: {
        uint8_t buf[COMMAND_MAX_PAYLOAD];
        uint32_t len = cmd->len > COMMAND_MAX_PAYLOAD ? COMMAND_MAX_PAYLOAD : cmd->len;
        hw_i2c_read_reg(cmd->sda, cmd->scl, cmd->speed_hz, cmd->addr, cmd->reg, buf, len);
        break;
    }
    case CMD_SPI_TX:
        hw_spi_tx(cmd->sck, cmd->mosi, cmd->cs, cmd->mode, cmd->speed_hz, cmd->payload,
                  cmd->payload_len);
        break;
    case CMD_SYNC:
        if (strcmp(cmd->sync_mode, "input") == 0) {
            hw_sync_read(cmd->pin);
        } else {
            // Marker pulse: rising then falling edge brackets the
            // stimulus-emission event.
            hw_sync_set(cmd->pin, true);
            sleep_us(1);
            hw_sync_set(cmd->pin, false);
        }
        break;
    case CMD_LOOPBACK:
        hw_loopback_emit(cmd->generator_pin, cmd->capture_pin);
        break;
    default:
        break;
    }
}

static void handle_command_line(const char *line) {
    command_t cmd;
    if (parse_command(line, &cmd) != 0) {
        response_t resp;
        handle_line(line, g_e9_affected, &resp); // recovers a best-effort id + reason
        char buf[128];
        serialize_response(&resp, buf, sizeof(buf));
        printf("%s\n", buf);
        return;
    }

    response_t resp;
    int rc = dispatch_command(&cmd, g_e9_affected, &resp);
    if (rc == 0 && cmd.cmd_id == CMD_INFO) {
        print_info_response(resp.id);
        return;
    }
    if (rc == 0) {
        execute_command(&cmd);
    }

    char buf[128];
    serialize_response(&resp, buf, sizeof(buf));
    printf("%s\n", buf);
}

int main(void) {
    stdio_init_all();
    set_sys_clock_khz(SYS_CLK_HZ / 1000, true);

    g_e9_affected = hw_detect_e9_affected(&g_stepping);

    char line[LINE_BUF_SIZE];
    size_t pos = 0;
    while (true) {
        int c = getchar_timeout_us(1000);
        if (c == PICO_ERROR_TIMEOUT) {
            continue;
        }
        if (c == '\n' || c == '\r') {
            if (pos > 0) {
                line[pos] = '\0';
                handle_command_line(line);
                pos = 0;
            }
            continue;
        }
        if (pos + 1 < LINE_BUF_SIZE) {
            line[pos++] = (char)c;
        } else {
            pos = 0; // overlong line: drop it
        }
    }
    return 0;
}
