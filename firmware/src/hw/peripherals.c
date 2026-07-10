#include "peripherals.h"

#include "hardware/gpio.h"
#include "hardware/i2c.h"
#include "hardware/pwm.h"
#include "pico/time.h"

#include <stddef.h>

// -- i2c: hardware peripheral (pin -> instance per the standard RP2040/2350
// GPIO function-table pattern: SDA/SCL alternate i2c0/i2c1 every 2 pins) --

static i2c_inst_t *i2c_instance_for_pin(uint32_t sda_pin) {
    return ((sda_pin >> 1) & 1u) ? i2c1 : i2c0;
}

static void i2c_bus_init(i2c_inst_t *inst, uint32_t sda, uint32_t scl, uint32_t speed_hz) {
    i2c_init(inst, speed_hz);
    gpio_set_function(sda, GPIO_FUNC_I2C);
    gpio_set_function(scl, GPIO_FUNC_I2C);
    gpio_pull_up(sda);
    gpio_pull_up(scl);
}

uint32_t hw_i2c_scan(uint32_t sda, uint32_t scl, uint32_t speed_hz, uint8_t *found_addrs,
                     uint32_t max) {
    i2c_inst_t *inst = i2c_instance_for_pin(sda);
    i2c_bus_init(inst, sda, scl, speed_hz);

    uint32_t n = 0;
    uint8_t dummy;
    for (uint8_t addr = 0x08; addr <= 0x77 && n < max; addr++) {
        int ret = i2c_read_blocking(inst, addr, &dummy, 1, false);
        if (ret >= 0) {
            found_addrs[n++] = addr;
        }
    }
    return n;
}

bool hw_i2c_read_reg(uint32_t sda, uint32_t scl, uint32_t speed_hz, uint8_t addr, uint8_t reg,
                     uint8_t *out, uint32_t len) {
    i2c_inst_t *inst = i2c_instance_for_pin(sda);
    i2c_bus_init(inst, sda, scl, speed_hz);

    if (i2c_write_blocking(inst, addr, &reg, 1, /*nostop=*/true) < 0) {
        return false;
    }
    return i2c_read_blocking(inst, addr, out, len, /*nostop=*/false) >= 0;
}

// -- spi_tx: bit-banged (arbitrary sck/mosi/cs pins per the v1 schema; the
// hardware SPI peripheral is pin-fixed) --

static inline void spi_send_bit(uint32_t sck, uint32_t mosi, bool bit, bool cpol, bool cpha,
                                uint32_t half_period_us) {
    if (!cpha) {
        gpio_put(mosi, bit);
        busy_wait_us(half_period_us);
        gpio_put(sck, !cpol);
        busy_wait_us(half_period_us);
        gpio_put(sck, cpol);
    } else {
        gpio_put(sck, !cpol);
        gpio_put(mosi, bit);
        busy_wait_us(half_period_us);
        gpio_put(sck, cpol);
        busy_wait_us(half_period_us);
    }
}

void hw_spi_tx(uint32_t sck, uint32_t mosi, uint32_t cs, uint32_t mode, uint32_t speed_hz,
               const uint8_t *payload, uint32_t len) {
    bool cpol = (mode == 2 || mode == 3);
    bool cpha = (mode == 1 || mode == 3);
    uint32_t half_period_us = (speed_hz > 0) ? (500000u / speed_hz) : 1;
    if (half_period_us == 0) {
        half_period_us = 1;
    }

    gpio_init(sck);
    gpio_init(mosi);
    gpio_init(cs);
    gpio_set_dir(sck, true);
    gpio_set_dir(mosi, true);
    gpio_set_dir(cs, true);
    gpio_put(sck, cpol);
    gpio_put(cs, true);

    gpio_put(cs, false);
    for (uint32_t i = 0; i < len; i++) {
        for (int b = 7; b >= 0; b--) {
            spi_send_bit(sck, mosi, (payload[i] >> b) & 1u, cpol, cpha, half_period_us);
        }
    }
    gpio_put(cs, true);
}

// -- uart_tx: bit-banged (arbitrary pin; also the only way to represent
// SBUS's inverted idle-low line level without extra hardware) --

static inline void uart_put_bit(uint32_t pin, bool logical_level, bool inverted,
                                uint32_t period_us) {
    gpio_put(pin, inverted ? !logical_level : logical_level);
    busy_wait_us(period_us);
}

static void uart_send_byte(uint32_t pin, uint8_t byte, uint8_t data_bits, char parity,
                           uint8_t stop_bits, bool inverted, uint32_t bit_period_us) {
    uart_put_bit(pin, false, inverted, bit_period_us); // start bit
    int ones = 0;
    for (uint8_t i = 0; i < data_bits; i++) {
        bool bit = (byte >> i) & 1u;
        if (bit) {
            ones++;
        }
        uart_put_bit(pin, bit, inverted, bit_period_us);
    }
    if (parity == 'E') {
        uart_put_bit(pin, (ones % 2) != 0, inverted, bit_period_us);
    } else if (parity == 'O') {
        uart_put_bit(pin, (ones % 2) == 0, inverted, bit_period_us);
    }
    for (uint8_t s = 0; s < stop_bits; s++) {
        uart_put_bit(pin, true, inverted, bit_period_us); // stop bit
    }
}

void hw_uart_tx(uint32_t pin, uint32_t baud, uint8_t data_bits, uint8_t stop_bits, char parity,
                bool inverted, const uint8_t *payload, uint32_t len) {
    gpio_init(pin);
    gpio_set_dir(pin, true);
    gpio_put(pin, inverted ? false : true); // idle

    uint32_t bit_period_us = (baud > 0) ? (1000000u / baud) : 100;
    for (uint32_t i = 0; i < len; i++) {
        uart_send_byte(pin, payload[i], data_bits, parity, stop_bits, inverted, bit_period_us);
    }
}

// -- pwm: hardware peripheral --

void hw_pwm_set(uint32_t pin, uint32_t freq_hz, bool is_pulse_us, uint32_t duty_or_pulse_us) {
    if (freq_hz == 0) {
        return;
    }
    gpio_set_function(pin, GPIO_FUNC_PWM);
    uint slice = pwm_gpio_to_slice_num(pin);

    uint32_t wrap = SYS_CLK_HZ / freq_hz;
    if (wrap < 1) {
        wrap = 1;
    }
    if (wrap > 65535) {
        wrap = 65535;
    }
    pwm_set_wrap(slice, (uint16_t)(wrap - 1));

    uint32_t level;
    if (is_pulse_us) {
        uint64_t level64 = ((uint64_t)duty_or_pulse_us * SYS_CLK_HZ) / 1000000ULL;
        level = (level64 > wrap) ? wrap : (uint32_t)level64;
    } else {
        uint32_t duty_pct = (duty_or_pulse_us > 100) ? 100 : duty_or_pulse_us;
        level = (wrap * duty_pct) / 100;
    }
    pwm_set_gpio_level(pin, (uint16_t)level);
    pwm_set_enabled(slice, true);
}
