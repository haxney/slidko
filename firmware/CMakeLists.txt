cmake_minimum_required(VERSION 3.13)

# Board must be set before pico_sdk_import.cmake/pico_sdk_init() -- it picks
# the platform (rp2040 vs rp2350) and thus the cross-compiler target.
#   cmake -S firmware -B firmware/build -DPICO_BOARD=pico  -DPICO_SDK_PATH=firmware/vendor/pico-sdk
#   cmake -S firmware -B firmware/build -DPICO_BOARD=pico2 -DPICO_SDK_PATH=firmware/vendor/pico-sdk
set(PICO_BOARD pico2 CACHE STRING "Board to build for: pico (RP2040) or pico2 (RP2350)")

include(pico_sdk_import.cmake)

project(exerciser-firmware C CXX ASM)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

pico_sdk_init()

if (PICO_BOARD STREQUAL "pico")
    set(EXERCISER_SYS_CLK_HZ 133000000)
elseif (PICO_BOARD STREQUAL "pico2")
    set(EXERCISER_SYS_CLK_HZ 150000000)
else()
    message(FATAL_ERROR "Unsupported board: ${PICO_BOARD} (use pico or pico2)")
endif()

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
target_compile_definitions(exerciser-firmware PRIVATE SYS_CLK_HZ=${EXERCISER_SYS_CLK_HZ})

pico_enable_stdio_usb(exerciser-firmware 1)
pico_enable_stdio_uart(exerciser-firmware 0)
pico_add_extra_outputs(exerciser-firmware)

target_link_libraries(exerciser-firmware
    pico_stdlib
    hardware_pio
    hardware_i2c
    hardware_pwm
)
