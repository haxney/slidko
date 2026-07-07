cmake_minimum_required(VERSION 3.13)

# Pull in pico-sdk (must be before project)
set(PICO_SDK_PATH "${CMAKE_CURRENT_SOURCE_DIR}/vendor/pico-sdk")
include(pico_sdk_import.cmake)

project(exerciser-firmware C CXX ASM)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

# Initialize the Pico SDK
pico_sdk_init()

# Create the executable
add_executable(exerciser-firmware
    src/main.c
    src/hw/*.c
    src/protocol/*.c
)

# Add pico-usb and pico-pio modules
pico_enable_stdio_usb(exerciser-firmware 1)
pico_enable_stdio_uart(exerciser-firmware 0)
pico_add_extra_outputs(exerciser-firmware)

# Target-specific configurations
if (PICO_BOARD STREQUAL "pico")
    # RP2040: 133 MHz
    target_compile_definitions(exerciser-firmware PRIVATE
        PICO_BOARD=${PICO_BOARD}
        SYS_CLK_HZ=133000000
    )
elseif (PICO_BOARD STREQUAL "pico2")
    # RP2350: 150 MHz
    target_compile_definitions(exerciser-firmware PRIVATE
        PICO_BOARD=${PICO_BOARD}
        SYS_CLK_HZ=150000000
    )
else()
    message(FATAL_ERROR "Unsupported board: ${PICO_BOARD}")
endif()

# Link the firmware to protocol sources only (for separation)
target_link_libraries(exerciser-firmware 
    pico-usb 
    pico-pio
    pico-blinky
)

# Add the include directory for our protocol headers
target_include_directories(exerciser-firmware PRIVATE src/protocol)