// Native (host) tests for the E9 runtime guard policy. The stepping
// detection itself lives in hw/ (hardware, compile-only); this exercises
// the pure policy logic with e9_affected supplied directly, per design.md
// "E9 runtime guard (silicon-aware)".
#include "command.h"
#include "dispatcher.h"
#include "e9_policy.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

static command_t make_command(command_id_t cmd_id) {
    command_t cmd;
    memset(&cmd, 0, sizeof(cmd));
    cmd.id = 42;
    cmd.cmd_id = cmd_id;
    return cmd;
}

static void test_loopback_is_input_sensing(void) {
    command_t cmd = make_command(CMD_LOOPBACK);
    assert(command_is_input_sensing(&cmd) == true);
}

static void test_sync_readback_is_input_sensing(void) {
    command_t cmd = make_command(CMD_SYNC);
    strcpy(cmd.sync_mode, "input");
    assert(command_is_input_sensing(&cmd) == true);
}

static void test_sync_output_marker_is_not_input_sensing(void) {
    command_t cmd = make_command(CMD_SYNC);
    strcpy(cmd.sync_mode, "output");
    assert(command_is_input_sensing(&cmd) == false);
}

static void test_dshot_is_not_input_sensing(void) {
    command_t cmd = make_command(CMD_DSHOT);
    assert(command_is_input_sensing(&cmd) == false);
}

static void test_input_sensing_command_e9_unavailable_when_affected(void) {
    command_t cmd = make_command(CMD_LOOPBACK);
    response_t resp;
    int rc = dispatch_command(&cmd, /*e9_affected=*/true, &resp);
    assert(rc != 0);
    assert(resp.status == RESP_ERR);
    assert(strcmp(resp.err_reason, "e9_unavailable") == 0);
    assert(resp.id == 42);
}

static void test_output_stimulus_stays_functional_when_e9_affected(void) {
    command_t cmd = make_command(CMD_DSHOT);
    cmd.assert_undriven = true; // clear the (unrelated) hazard gate too
    response_t resp;
    int rc = dispatch_command(&cmd, /*e9_affected=*/true, &resp);
    assert(rc == 0);
    assert(resp.status == RESP_OK);
}

static void test_input_sensing_command_ok_when_not_affected(void) {
    command_t cmd = make_command(CMD_LOOPBACK);
    response_t resp;
    int rc = dispatch_command(&cmd, /*e9_affected=*/false, &resp);
    assert(rc == 0);
    assert(resp.status == RESP_OK);
}

static bool capability_available(const capability_t *caps, size_t n, const char *name) {
    for (size_t i = 0; i < n; i++) {
        if (strcmp(caps[i].name, name) == 0) {
            return caps[i].available;
        }
    }
    assert(0 && "capability not found");
    return false;
}

static void test_capability_list_differs_exactly_on_input_sensing_entries(void) {
    capability_t a2[16];
    capability_t a4[16];
    size_t n_a2 = get_capabilities(/*e9_affected=*/true, a2, 16);
    size_t n_a4 = get_capabilities(/*e9_affected=*/false, a4, 16);
    assert(n_a2 == n_a4);

    size_t differences = 0;
    for (size_t i = 0; i < n_a2; i++) {
        assert(strcmp(a2[i].name, a4[i].name) == 0);
        if (a2[i].available != a4[i].available) {
            differences++;
            // Every difference must be an input-sensing entry that's
            // unavailable on A2 (e9_affected) and available on A4.
            assert(a2[i].available == false);
            assert(a4[i].available == true);
        }
    }
    assert(differences == 2); // sync_readback, loopback
    assert(capability_available(a2, n_a2, "sync_readback") == false);
    assert(capability_available(a2, n_a2, "loopback") == false);
    assert(capability_available(a4, n_a4, "sync_readback") == true);
    assert(capability_available(a4, n_a4, "loopback") == true);
    // Output-stimulus entries are untouched by E9 posture.
    assert(capability_available(a2, n_a2, "dshot") == true);
    assert(capability_available(a2, n_a2, "sync_stimulus") == true);
}

int main(void) {
    test_loopback_is_input_sensing();
    test_sync_readback_is_input_sensing();
    test_sync_output_marker_is_not_input_sensing();
    test_dshot_is_not_input_sensing();

    test_input_sensing_command_e9_unavailable_when_affected();
    test_output_stimulus_stays_functional_when_e9_affected();
    test_input_sensing_command_ok_when_not_affected();

    test_capability_list_differs_exactly_on_input_sensing_entries();

    printf("test_e9: all tests passed\n");
    return 0;
}
