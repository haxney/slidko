// Native (host) tests for the JSON-lines parser and the id-echo/ok|err
// dispatch contract. No pico-sdk headers, no hardware: protocol/ is pure C
// over plain structs (see design.md "Directory + build split").
#include "command.h"
#include "dispatcher.h"
#include "parser.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

// -- group 2: parsing --------------------------------------------------

static void test_parse_info_command(void) {
    command_t cmd;
    int rc = parse_command("{\"id\":42,\"cmd\":\"info\"}", &cmd);
    assert(rc == 0);
    assert(cmd.id == 42);
    assert(cmd.cmd_id == CMD_INFO);
}

static void test_parse_dshot_command(void) {
    command_t cmd;
    int rc = parse_command(
        "{\"id\":123,\"cmd\":\"dshot\",\"pin\":5,\"rate\":600,\"value\":1000,\"repeat\":2,"
        "\"assert_undriven\":true}",
        &cmd);
    assert(rc == 0);
    assert(cmd.id == 123);
    assert(cmd.cmd_id == CMD_DSHOT);
    assert(cmd.pin == 5);
    assert(cmd.rate == 600);
    assert(cmd.value == 1000);
    assert(cmd.repeat == 2);
    assert(cmd.assert_undriven == true);
}

static void test_parse_i2c_read_command(void) {
    command_t cmd;
    int rc = parse_command(
        "{\"id\":7,\"cmd\":\"i2c_read\",\"sda\":2,\"scl\":3,\"addr\":104,\"reg\":117,\"len\":1}",
        &cmd);
    assert(rc == 0);
    assert(cmd.cmd_id == CMD_I2C_READ);
    assert(cmd.sda == 2);
    assert(cmd.scl == 3);
    assert(cmd.addr == 104);
    assert(cmd.reg == 117);
    assert(cmd.len == 1);
}

static void test_parse_sync_readback_mode(void) {
    command_t cmd;
    int rc = parse_command("{\"id\":9,\"cmd\":\"sync\",\"pin\":22,\"mode\":\"input\"}", &cmd);
    assert(rc == 0);
    assert(cmd.cmd_id == CMD_SYNC);
    assert(strcmp(cmd.sync_mode, "input") == 0);
}

static void test_parse_malformed_json(void) {
    command_t cmd;
    // Missing closing brace.
    int rc = parse_command("{\"id\":42,\"cmd\":\"info\"", &cmd);
    assert(rc != 0);
}

static void test_parse_unparseable_line(void) {
    command_t cmd;
    int rc = parse_command("this is not valid json", &cmd);
    assert(rc != 0);
}

static void test_parse_unknown_command_name(void) {
    command_t cmd;
    int rc = parse_command("{\"id\":1,\"cmd\":\"flash\"}", &cmd);
    assert(rc != 0);
}

// -- group 3: id-echo + ok/err response contract ------------------------

static void test_dispatch_valid_command_echoes_id(void) {
    command_t cmd;
    assert(parse_command("{\"id\":42,\"cmd\":\"info\"}", &cmd) == 0);

    response_t resp;
    int rc = dispatch_command(&cmd, /*e9_affected=*/false, &resp);
    assert(rc == 0);
    assert(resp.id == 42);
    assert(resp.status == RESP_OK);
}

static void test_handle_line_valid_command_serializes_ok(void) {
    response_t resp;
    handle_line("{\"id\":42,\"cmd\":\"info\"}", /*e9_affected=*/false, &resp);
    assert(resp.id == 42);
    assert(resp.status == RESP_OK);

    char buf[128];
    assert(serialize_response(&resp, buf, sizeof(buf)) == 0);
    assert(strstr(buf, "\"id\":42") != NULL);
    assert(strstr(buf, "\"status\":\"ok\"") != NULL);
}

static void test_handle_line_unparseable_yields_err_with_reason(void) {
    response_t resp;
    handle_line("this is not valid json", /*e9_affected=*/false, &resp);
    assert(resp.status == RESP_ERR);
    assert(strlen(resp.err_reason) > 0);

    char buf[128];
    assert(serialize_response(&resp, buf, sizeof(buf)) == 0);
    assert(strstr(buf, "\"status\":\"err\"") != NULL);
    assert(strstr(buf, resp.err_reason) != NULL);
}

int main(void) {
    test_parse_info_command();
    test_parse_dshot_command();
    test_parse_i2c_read_command();
    test_parse_sync_readback_mode();
    test_parse_malformed_json();
    test_parse_unparseable_line();
    test_parse_unknown_command_name();

    test_dispatch_valid_command_echoes_id();
    test_handle_line_valid_command_serializes_ok();
    test_handle_line_unparseable_yields_err_with_reason();

    printf("test_protocol: all tests passed\n");
    return 0;
}
