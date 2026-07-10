# Standalone HOST-native project: builds firmware/src/protocol/ with the
# host `cc`, no pico-sdk, no ARM toolchain. protocol/ includes no SDK
# headers by design (see design.md "Directory + build split"), so this is
# the whole point of the split -- run with:
#   cmake -S firmware/test -B firmware/test/build
#   cmake --build firmware/test/build
#   ctest --test-dir firmware/test/build --output-on-failure
cmake_minimum_required(VERSION 3.13)
project(exerciser-firmware-tests C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

enable_testing()

file(GLOB PROTOCOL_SOURCES ${CMAKE_CURRENT_SOURCE_DIR}/../src/protocol/*.c)

function(add_protocol_test name)
    add_executable(${name} ${name}.c ${PROTOCOL_SOURCES})
    target_include_directories(${name} PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/../src/protocol)
    target_compile_options(${name} PRIVATE -Wall -Wextra -Werror)
    add_test(NAME ${name} COMMAND ${name})
endfunction()

add_protocol_test(test_protocol)
add_protocol_test(test_timing)
add_protocol_test(test_e9)
add_protocol_test(test_hazard)
