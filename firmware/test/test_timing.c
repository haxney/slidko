// Native (host) tests for clock-parameterized timing. No SYS_CLK_HZ macro
// dependency: compute_dshot_timing/compute_ws2812_timing take clk_hz as an
// explicit argument, so this single test binary can recompute at both
// RP2040 (133 MHz) and RP2350 (150 MHz) without recompiling.
#include "timing.h"

#include <assert.h>
#include <stddef.h>
#include <stdio.h>

#define CLK_RP2040_HZ 133000000u
#define CLK_RP2350_HZ 150000000u

static void test_dshot_t1h_is_always_2x_t0h(void) {
    const uint32_t rates[] = {150, 300, 600};
    const uint32_t clocks[] = {CLK_RP2040_HZ, CLK_RP2350_HZ};
    for (size_t r = 0; r < sizeof(rates) / sizeof(rates[0]); r++) {
        for (size_t c = 0; c < sizeof(clocks) / sizeof(clocks[0]); c++) {
            dshot_timing_t t;
            assert(compute_dshot_timing(rates[r], clocks[c], &t) == 0);
            assert(t.t1h_cycles == 2 * t.t0h_cycles);
            assert(t.t0h_cycles > 0);
        }
    }
}

static void test_dshot_timing_differs_per_clock(void) {
    dshot_timing_t t133;
    dshot_timing_t t150;
    assert(compute_dshot_timing(600, CLK_RP2040_HZ, &t133) == 0);
    assert(compute_dshot_timing(600, CLK_RP2350_HZ, &t150) == 0);
    // Higher clock -> more cycles for the same physical time.
    assert(t150.t0h_cycles > t133.t0h_cycles);
    assert(t150.bit_period_cycles > t133.bit_period_cycles);
}

static void test_dshot_timing_rejects_unknown_rate(void) {
    dshot_timing_t t;
    assert(compute_dshot_timing(1200, CLK_RP2350_HZ, &t) != 0);
}

static void test_dshot600_faster_than_dshot150(void) {
    // Higher DShot rate -> shorter bit period at the same clock.
    dshot_timing_t d150;
    dshot_timing_t d600;
    assert(compute_dshot_timing(150, CLK_RP2350_HZ, &d150) == 0);
    assert(compute_dshot_timing(600, CLK_RP2350_HZ, &d600) == 0);
    assert(d600.bit_period_cycles < d150.bit_period_cycles);
}

static void test_dshot_encode_frame_matches_known_vector(void) {
    // value=0 (disarm), telemetry=false -> packet=0, csum over nibbles of 0
    // is 0 -> frame 0x0000.
    assert(dshot_encode_frame(0, false) == 0x0000);

    // value=1 (0-throttle command range start), telemetry=false:
    // packet = 1<<1|0 = 0b0000_0000_0010 (0x002); nibbles 0x2,0x0,0x0 ->
    // csum = 0x2^0x0^0x0 = 0x2; frame = (0x002<<4)|0x2 = 0x0022.
    assert(dshot_encode_frame(1, false) == 0x0022);

    // value=1, telemetry=true: packet = 1<<1|1 = 0x003; nibbles
    // 0x3,0x0,0x0 -> csum=0x3; frame = (0x003<<4)|0x3 = 0x0033.
    assert(dshot_encode_frame(1, true) == 0x0033);
}

static void test_dshot_encode_frame_low_nibble_is_crc_of_high_12_bits(void) {
    for (uint16_t v = 0; v < 2048; v += 137) {
        uint16_t frame = dshot_encode_frame(v, false);
        uint16_t packet = frame >> 4;
        uint16_t csum = frame & 0xF;
        uint16_t expect_csum = (uint16_t)((packet ^ (packet >> 4) ^ (packet >> 8)) & 0xF);
        assert(csum == expect_csum);
        assert(packet == (uint16_t)(v << 1));
    }
}

static void test_ws2812_timing_computed_from_clock(void) {
    ws2812_timing_t t133;
    ws2812_timing_t t150;
    compute_ws2812_timing(CLK_RP2040_HZ, &t133);
    compute_ws2812_timing(CLK_RP2350_HZ, &t150);

    assert(t133.t0h_cycles > 0);
    assert(t133.t1h_cycles > t133.t0h_cycles);
    assert(t150.t0h_cycles > t133.t0h_cycles);
    assert(t150.period_cycles > t133.period_cycles);
}

int main(void) {
    test_dshot_t1h_is_always_2x_t0h();
    test_dshot_timing_differs_per_clock();
    test_dshot_timing_rejects_unknown_rate();
    test_dshot600_faster_than_dshot150();
    test_dshot_encode_frame_matches_known_vector();
    test_dshot_encode_frame_low_nibble_is_crc_of_high_12_bits();
    test_ws2812_timing_computed_from_clock();

    printf("test_timing: all tests passed\n");
    return 0;
}
