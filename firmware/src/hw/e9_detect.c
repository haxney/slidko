#include "e9_detect.h"

#if PICO_RP2350
#include "pico.h" // pico/platform.h errors if not included via pico.h
#endif

bool hw_detect_e9_affected(silicon_stepping_t *out_stepping) {
#if PICO_RP2350
    uint8_t version = rp2350_chip_version(); // 2 = A2, 3 = A3/A4
    if (version <= 2) {
        *out_stepping = SILICON_A2;
        return true;
    }
    *out_stepping = SILICON_A4;
    return false;
#else
    // RP2040 (`pico` target): E9 is an RP2350 erratum, not applicable.
    *out_stepping = SILICON_UNKNOWN;
    return false;
#endif
}
