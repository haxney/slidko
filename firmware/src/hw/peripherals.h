#ifndef HW_PERIPHERALS_H
#define HW_PERIPHERALS_H

#include <stdbool.h>
#include <stdint.h>

// i2c_scan/i2c_read use the hardware I2C peripheral (i2c0/i2c1, selected by
// pin per the standard RP2040/2350 GPIO function-table pattern: instance =
// (sda_pin >> 1) & 1). Open-drain bus-master ops per the hazard envelope --
// no series-resistor/undriven concerns, no assert_undriven gate.

// Scans addresses 0x08..0x77; writes ACKed 7-bit addresses into
// `found_addrs` (capacity `max`). Returns the count found.
uint32_t hw_i2c_scan(uint32_t sda, uint32_t scl, uint32_t speed_hz, uint8_t *found_addrs,
                     uint32_t max);

// Register read: writes `reg` (no stop), then reads `len` bytes into `out`.
// Returns true on ACK'd transfer.
bool hw_i2c_read_reg(uint32_t sda, uint32_t scl, uint32_t speed_hz, uint8_t addr, uint8_t reg,
                     uint8_t *out, uint32_t len);

// spi_tx and uart_tx are bit-banged (not the fixed-pinout hardware SPI/UART
// peripherals) because the v1 command schema allows an arbitrary GPIO for
// sck/mosi/cs/pin, and only specific pin pairs route to the hardware
// peripherals. Timing precision is busy-wait-loop-limited; fine for the
// baud/clock rates in EXERCISER.md's examples, NOT validated on hardware in
// this session.

void hw_spi_tx(uint32_t sck, uint32_t mosi, uint32_t cs, uint32_t mode, uint32_t speed_hz,
               const uint8_t *payload, uint32_t len);

// `inverted` is set for SBUS-style framing (idle-low, inverted UART logic).
// `parity`: 'N', 'E', or 'O'.
void hw_uart_tx(uint32_t pin, uint32_t baud, uint8_t data_bits, uint8_t stop_bits, char parity,
                bool inverted, const uint8_t *payload, uint32_t len);

// pwm uses the hardware PWM peripheral (fixed pin->slice/channel mapping is
// looked up at runtime via pwm_gpio_to_slice_num/pwm_gpio_to_channel).
void hw_pwm_set(uint32_t pin, uint32_t freq_hz, bool is_pulse_us, uint32_t duty_or_pulse_us);

#endif // HW_PERIPHERALS_H
