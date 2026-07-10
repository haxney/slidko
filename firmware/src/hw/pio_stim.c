#include "pio_stim.h"

#include "dshot.pio.h"
#include "hardware/pio.h"
#include "timing.h"
#include "ws2812.pio.h"

#include <stdbool.h>

static bool ws2812_loaded = false;
static uint ws2812_offset;
static uint ws2812_sm;
static int ws2812_pin_inited = -1;

static bool dshot_loaded = false;
static uint dshot_offset;
static uint dshot_sm;
static int dshot_pin_inited = -1;
static uint32_t dshot_rate_inited = 0;

void pio_stim_ws2812_send(uint32_t pin, const uint8_t *grb_bytes, uint32_t led_count) {
    if (!ws2812_loaded) {
        ws2812_offset = (uint)pio_add_program(pio0, &ws2812_program);
        ws2812_sm = (uint)pio_claim_unused_sm(pio0, true);
        ws2812_loaded = true;
    }
    if (ws2812_pin_inited != (int)pin) {
        ws2812_program_init(pio0, ws2812_sm, ws2812_offset, pin, 800000.0f, /*rgbw=*/false);
        ws2812_pin_inited = (int)pin;
    }
    // GRB, 24 bits, left-justified into the top of the 32-bit FIFO word to
    // match sm_config_set_out_shift(shift_left=true, threshold=24).
    for (uint32_t i = 0; i < led_count; i++) {
        uint32_t grb = ((uint32_t)grb_bytes[i * 3 + 0] << 16) |
                       ((uint32_t)grb_bytes[i * 3 + 1] << 8) | grb_bytes[i * 3 + 2];
        pio_sm_put_blocking(pio0, ws2812_sm, grb << 8);
    }
}

void pio_stim_dshot_send(uint32_t pin, uint32_t rate, uint16_t frame) {
    if (!dshot_loaded) {
        dshot_offset = (uint)pio_add_program(pio0, &dshot_program);
        dshot_sm = (uint)pio_claim_unused_sm(pio0, true);
        dshot_loaded = true;
    }
    if (dshot_pin_inited != (int)pin || dshot_rate_inited != rate) {
        dshot_program_init(pio0, dshot_sm, dshot_offset, pin, (float)(rate * 1000));
        dshot_pin_inited = (int)pin;
        dshot_rate_inited = rate;
    }
    // 16-bit frame, left-justified to match sm_config_set_out_shift(true, 16).
    pio_sm_put_blocking(pio0, dshot_sm, (uint32_t)frame << 16);
}
