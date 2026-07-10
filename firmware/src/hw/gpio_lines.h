#ifndef HW_GPIO_LINES_H
#define HW_GPIO_LINES_H

#include <stdbool.h>
#include <stdint.h>

// sync: reserved sync-channel marker (EXERCISER.md). "output" mode toggles
// the marker line at stimulus-emission events (pure output, always
// available); "input" mode reads it back (E9-gated -- see e9_policy.c).
void hw_sync_set(uint32_t pin, bool level);
bool hw_sync_read(uint32_t pin);

// loopback: emit a known toggle pattern on `generator_pin` and read it back
// on `capture_pin` (instrument self-test, per EXERCISER.md "every credible
// instrument self-tests"). Returns true if every emitted level was observed
// on the capture pin. E9-gated (it's a closed-loop read).
bool hw_loopback_emit(uint32_t generator_pin, uint32_t capture_pin);

#endif // HW_GPIO_LINES_H
