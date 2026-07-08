cmake_minimum_required(VERSION 3.13)

# Add a native test executable using host compiler
add_executable(test_protocol
    test_protocol.c
    ../src/protocol/*.c
)

# Link only protocol layer (no SDK headers)
target_include_directories(test_protocol PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/../src/protocol
    ${CMAKE_CURRENT_SOURCE_DIR}/../src
)

# Set the C standard to 11 for compatibility
set_target_properties(test_protocol PROPERTIES
    C_STANDARD 11
)

# This target can be built and run with host compiler from the CLI:
# cmake -S test -B test/build
# cmake --build test/build
target_compile_definitions(test_protocol PRIVATE
    TEST_MODE=1
)
