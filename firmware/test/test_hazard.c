// Native (host) tests for the hazard envelope, per EXERCISER.md "Hazard
// envelope (v1 rules -- enforced in firmware AND in Diagnose)".
#include "command.h"
#include "dispatcher.h"
#include "hazard.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

static command_t make_command(command_id_t cmd_id, bool assert_undriven) {
    command_t cmd;
    memset(&cmd, 0, sizeof(cmd));
    cmd.id = 1;
    cmd.cmd_id = cmd_id;
    cmd.assert_undriven = assert_undriven;
    return cmd;
}

static const command_id_t PUSH_PULL_COMMANDS[] = {CMD_WS2812, CMD_DSHOT, CMD_PWM, CMD_UART_TX,
                                                  CMD_SPI_TX};

static void test_push_pull_without_assertion_refused(void) {
    for (size_t i = 0; i < sizeof(PUSH_PULL_COMMANDS) / sizeof(PUSH_PULL_COMMANDS[0]); i++) {
        command_t cmd = make_command(PUSH_PULL_COMMANDS[i], /*assert_undriven=*/false);
        assert(hazard_check(&cmd) != 0);

        response_t resp;
        int rc = dispatch_command(&cmd, /*e9_affected=*/false, &resp);
        assert(rc != 0);
        assert(resp.status == RESP_ERR);
        assert(strcmp(resp.err_reason, "hazard_violation") == 0);
    }
}

static void test_push_pull_with_assertion_accepted(void) {
    for (size_t i = 0; i < sizeof(PUSH_PULL_COMMANDS) / sizeof(PUSH_PULL_COMMANDS[0]); i++) {
        command_t cmd = make_command(PUSH_PULL_COMMANDS[i], /*assert_undriven=*/true);
        assert(hazard_check(&cmd) == 0);

        response_t resp;
        int rc = dispatch_command(&cmd, /*e9_affected=*/false, &resp);
        assert(rc == 0);
        assert(resp.status == RESP_OK);
    }
}

static void test_open_drain_accepted_without_assertion(void) {
    command_id_t open_drain[] = {CMD_I2C_SCAN, CMD_I2C_READ};
    for (size_t i = 0; i < sizeof(open_drain) / sizeof(open_drain[0]); i++) {
        command_t cmd = make_command(open_drain[i], /*assert_undriven=*/false);
        assert(hazard_check(&cmd) == 0);
    }
}

// The DUT-control boundary is structural: the command table has no
// flash/write/program/control path, so there is nothing for the hazard
// gate (or anything else) to accidentally let through.
static void test_command_table_has_no_dut_control_command(void) {
    static const char *const FORBIDDEN_SUBSTRINGS[] = {"flash", "write", "program",
                                                       "set",   "msp",   "command"};
    for (int id = 0; id < CMD_COUNT; id++) {
        const char *name = command_name((command_id_t)id);
        for (size_t f = 0; f < sizeof(FORBIDDEN_SUBSTRINGS) / sizeof(FORBIDDEN_SUBSTRINGS[0]);
             f++) {
            assert(strstr(name, FORBIDDEN_SUBSTRINGS[f]) == NULL);
        }
    }
    assert(CMD_COUNT == 10); // the exact v1 command set, no more
}

int main(void) {
    test_push_pull_without_assertion_refused();
    test_push_pull_with_assertion_accepted();
    test_open_drain_accepted_without_assertion();
    test_command_table_has_no_dut_control_command();

    printf("test_hazard: all tests passed\n");
    return 0;
}
