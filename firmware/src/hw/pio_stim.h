#ifndef HW_PIO_STIM_H
#define HW_PIO_STIM_H

#include <stdint.h>

// PIO-driven push-pull stimulus: WS2812 (from ws2812.pio, copied verbatim
// from the pico-sdk's own vendored src/rp2_common/pico_status_led/ws2812.pio
// -- a real, known-good reference already used elsewhere in the SDK) and
// DShot (dshot.pio, adapted from the same pattern -- see that file's
// confidence note). Compile-verified only in this session; hardware
// validation is a human step (see design.md).

// Sends `led_count` GRB triples (24 bits each, MSB first) out `pin` at
// 800 kHz WS2812 timing.
void pio_stim_ws2812_send(uint32_t pin, const uint8_t *grb_bytes, uint32_t led_count);

// Sends one 16-bit DShot frame (see dshot_encode_frame in protocol/timing.h)
// out `pin` at the given DShot rate (150/300/600).
void pio_stim_dshot_send(uint32_t pin, uint32_t rate, uint16_t frame);

#endif // HW_PIO_STIM_H
