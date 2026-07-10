cmake_minimum_required(VERSION 3.13)

# Board must be set before pico_sdk_import.cmake/pico_sdk_init() -- it picks
# the platform (rp2040 vs rp2350) and thus the cross-compiler target.
#   cmake -S firmware -B firmware/build -DPICO_BOARD=pico  -DPICO_SDK_PATH=firmware/vendor/pico-sdk
#   cmake -S firmware -B firmware/build -DPICO_BOARD=pico2 -DPICO_SDK_PATH=firmware/vendor/pico-sdk
set(PICO_BOARD pico2 CACHE STRING "Board to build for: pico (RP2040) or pico2 (RP2350)")

# SYS_CLK_HZ is also a macro hardware/clocks.h itself recognizes (it special-
# cases exactly 200 MHz on RP2040 for a canned fast-clock PLL recipe); any
# other value -- including our 133 MHz RP2040 target -- requires us to supply
# PLL_SYS_VCO_FREQ_HZ/POSTDIV1/POSTDIV2 explicitly, or clocks.h hard-errors.
# 133 MHz: VCO = 12 MHz(XOSC) * FBDIV; gcd(12, 133) = 1 (133 = 7*19), so FBDIV
# must itself be a multiple of 133 -- FBDIV=133 is the only one in the valid
# 16-320 range, giving VCO=1596 MHz (within the 750-1600 MHz range) and
# POSTDIV1*POSTDIV2=12 (6*2).
# These must be visible to every translation unit in the SDK that includes
# hardware/clocks.h (not just our own target), so add_compile_definitions()
# (directory-scoped) is used instead of target_compile_definitions(), and set
# before pico_sdk_init() pulls in the SDK's subdirectories.
if (PICO_BOARD STREQUAL "pico")
    set(EXERCISER_SYS_CLK_HZ 133000000)
    add_compile_definitions(
        SYS_CLK_HZ=${EXERCISER_SYS_CLK_HZ}
        PLL_SYS_VCO_FREQ_HZ=1596000000
        PLL_SYS_POSTDIV1=6
        PLL_SYS_POSTDIV2=2
    )
elseif (PICO_BOARD STREQUAL "pico2")
    set(EXERCISER_SYS_CLK_HZ 150000000)
    add_compile_definitions(SYS_CLK_HZ=${EXERCISER_SYS_CLK_HZ})
else()
    message(FATAL_ERROR "Unsupported board: ${PICO_BOARD} (use pico or pico2)")
endif()

include(pico_sdk_import.cmake)

project(exerciser-firmware C CXX ASM)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

pico_sdk_init()

file(GLOB HW_SOURCES ${CMAKE_CURRENT_SOURCE_DIR}/src/hw/*.c)
file(GLOB PROTOCOL_SOURCES ${CMAKE_CURRENT_SOURCE_DIR}/src/protocol/*.c)

add_executable(exerciser-firmware
    src/main.c
    ${HW_SOURCES}
    ${PROTOCOL_SOURCES}
)

pico_generate_pio_header(exerciser-firmware ${CMAKE_CURRENT_SOURCE_DIR}/src/hw/ws2812.pio)
pico_generate_pio_header(exerciser-firmware ${CMAKE_CURRENT_SOURCE_DIR}/src/hw/dshot.pio)

target_include_directories(exerciser-firmware PRIVATE src src/protocol src/hw)

pico_enable_stdio_usb(exerciser-firmware 1)
pico_enable_stdio_uart(exerciser-firmware 0)
pico_add_extra_outputs(exerciser-firmware)

target_link_libraries(exerciser-firmware
    pico_stdlib
    hardware_pio
    hardware_i2c
    hardware_pwm
)
