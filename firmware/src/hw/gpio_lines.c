#include "gpio_lines.h"

#include "hardware/gpio.h"
#include "pico/time.h"

void hw_sync_set(uint32_t pin, bool level) {
    gpio_init(pin);
    gpio_set_dir(pin, true);
    gpio_put(pin, level);
}

bool hw_sync_read(uint32_t pin) {
    gpio_init(pin);
    gpio_set_dir(pin, false);
    return gpio_get(pin);
}

bool hw_loopback_emit(uint32_t generator_pin, uint32_t capture_pin) {
    gpio_init(generator_pin);
    gpio_set_dir(generator_pin, true);
    gpio_init(capture_pin);
    gpio_set_dir(capture_pin, false);

    bool all_matched = true;
    for (int i = 0; i < 4; i++) {
        bool level = (i % 2) == 0;
        gpio_put(generator_pin, level);
        busy_wait_us(10);
        if (gpio_get(capture_pin) != level) {
            all_matched = false;
        }
    }
    return all_matched;
}
