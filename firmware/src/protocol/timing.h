#ifndef TIMING_H
#define TIMING_H

#include <stdbool.h>
#include <stdint.h>

// Cycle counts at a given SYS_CLK_HZ. T1H is always exactly 2x T0H by
// construction (EXERCISER.md: "T1H is always 2x T0H"), not independently
// rounded from nanoseconds, so the invariant holds at any clock rate.
typedef struct {
    uint32_t bit_period_cycles;
    uint32_t t0h_cycles;
    uint32_t t1h_cycles;
} dshot_timing_t;

typedef struct {
    uint32_t period_cycles;
    uint32_t t0h_cycles;
    uint32_t t1h_cycles;
} ws2812_timing_t;

// Computes DShot bit timing for `rate` (150/300/600) at `clk_hz`. Returns 0
// on success, non-zero if `rate` is not one of 150/300/600.
int compute_dshot_timing(uint32_t rate, uint32_t clk_hz, dshot_timing_t *out);

// Computes WS2812 (800 kHz) bit timing at `clk_hz`.
void compute_ws2812_timing(uint32_t clk_hz, ws2812_timing_t *out);

// Encodes an 11-bit DShot value (0-2047) plus the telemetry-request bit into
// the 16-bit on-wire frame: [11-bit value][telemetry bit][4-bit XOR CRC].
// The standard Betaflight DShot CRC (widely published, not project-derived):
// crc = (nibble0 ^ nibble1 ^ nibble2) & 0xF over the 12-bit
// value<<1|telemetry, folded 4 bits at a time.
uint16_t dshot_encode_frame(uint16_t value, bool telemetry);

#endif // TIMING_H
