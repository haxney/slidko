#include "timing.h"
#include <stdint.h>

// Helper function to compute time in cycles for a given time in microseconds at a specific clock rate
static inline uint32_t us_to_cycles(uint32_t us, uint32_t clk_hz) {
    return (us * clk_hz + 500000) / 1000000; // Adding 500000 before division for proper rounding
}

// Compute DShot timing based on clock rate
dshot_timing_t compute_dshot_timing(uint32_t rate) {
    dshot_timing_t timing;

    // Calculate bit period in microseconds (from EXERCISER.md spec)
    uint32_t bit_period_us = 0;
    switch(rate) {
        case 150:
            bit_period_us = 667;  // 6.67 µs
            break;
        case 300:
            bit_period_us = 333;  // 3.33 µs
            break;
        case 600:
            bit_period_us = 167;  // 1.67 µs
            break;
        default:
            bit_period_us = 667;  // Default to DShot150 (6.67 µs)
    }

    // For DShot, T1H should be about 2x T0H based on specification
    uint32_t t0h_us = bit_period_us * 2500 / 10000; // 2.5 µs for T0H
    uint32_t t1h_us = bit_period_us * 5000 / 10000; // 5 µs for T1H

    // Convert to cycles using the system clock (should be defined via CMAKE)
    timing.bit_0_low = 0;
    timing.bit_0_high = us_to_cycles(t0h_us, SYS_CLK_HZ);
    timing.bit_1_low = 0;
    timing.bit_1_high = us_to_cycles(t1h_us, SYS_CLK_HZ);

    return timing;
}

// Compute WS2812 timing based on clock rate
ws2812_timing_t compute_ws2812_timing(void) {
    ws2812_timing_t timing;

    // Use exact specifications: T0H ≈ 0.4 µs, T1H ≈ 0.8 µs (±150 ns)
    uint32_t t0h_cycles = us_to_cycles(400, SYS_CLK_HZ); // 0.4 µs
    uint32_t t1h_cycles = us_to_cycles(800, SYS_CLK_HZ); // 0.8 µs

    timing.period = 0; // Full period would be about 1.25 µs (800 kHz)
    timing.bit_0_low = 0;
    timing.bit_0_high = t0h_cycles;
    timing.bit_1_low = 0;
    timing.bit_1_high = t1h_cycles;

    return timing;
}
