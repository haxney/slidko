#ifndef TIMING_H
#define TIMING_H

#include <stdint.h>

// Timing constants for DShot commands - computed at compile time based on SYS_CLK_HZ
typedef struct {
    uint32_t bit_0_low;
    uint32_t bit_0_high;
    uint32_t bit_1_low;
    uint32_t bit_1_high;
} dshot_timing_t;

// Timing constants for WS2812 LEDs - computed at compile time based on SYS_CLK_HZ
typedef struct {
    uint32_t period;
    uint32_t bit_0_low;
    uint32_t bit_0_high;
    uint32_t bit_1_low;
    uint32_t bit_1_high;
} ws2812_timing_t;

// Compute DShot timing based on clock rate (assuming 150 MHz system clock)
dshot_timing_t compute_dshot_timing(uint32_t rate);

// Compute WS2812 timing based on clock rate
ws2812_timing_t compute_ws2812_timing(void);

#endif // TIMING_H