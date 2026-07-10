#include "timing.h"

// Rounds ns*clk_hz/1e9 to the nearest cycle count. 64-bit intermediate: at
// clk_hz ~150e6 and ns ~6670 (DShot150 bit period), the product is ~1e12,
// which overflows uint32_t.
static uint32_t ns_to_cycles(uint32_t ns, uint32_t clk_hz) {
    uint64_t num = (uint64_t)ns * (uint64_t)clk_hz;
    return (uint32_t)((num + 500000000ULL) / 1000000000ULL);
}

int compute_dshot_timing(uint32_t rate, uint32_t clk_hz, dshot_timing_t *out) {
    uint32_t period_ns;
    uint32_t t0h_ns;
    switch (rate) {
    case 150:
        period_ns = 6670;
        t0h_ns = 2500;
        break;
    case 300:
        period_ns = 3330;
        t0h_ns = 1250;
        break;
    case 600:
        period_ns = 1670;
        t0h_ns = 625;
        break;
    default:
        return -1;
    }
    out->bit_period_cycles = ns_to_cycles(period_ns, clk_hz);
    out->t0h_cycles = ns_to_cycles(t0h_ns, clk_hz);
    out->t1h_cycles = out->t0h_cycles * 2;
    return 0;
}

void compute_ws2812_timing(uint32_t clk_hz, ws2812_timing_t *out) {
    // Spec-exact per EXERCISER.md: 800 kHz (1250 ns period), T0H ~0.4 us,
    // T1H ~0.8 us (+-150 ns).
    out->period_cycles = ns_to_cycles(1250, clk_hz);
    out->t0h_cycles = ns_to_cycles(400, clk_hz);
    out->t1h_cycles = ns_to_cycles(800, clk_hz);
}

uint16_t dshot_encode_frame(uint16_t value, bool telemetry) {
    uint16_t packet = (uint16_t)((value << 1) | (telemetry ? 1 : 0));
    uint16_t csum = 0;
    uint16_t csum_data = packet;
    for (int i = 0; i < 3; i++) {
        csum ^= csum_data;
        csum_data >>= 4;
    }
    csum &= 0xF;
    return (uint16_t)((packet << 4) | csum);
}
