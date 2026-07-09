# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2024 Raspberry Pi Ltd.
#
# This file is imported into the top level CMakeLists.txt of your project to pull in
# the pico sdk and set up the build. It also provides helper functions.
include_guard(GLOBAL)

# Set default PICO_SDK_PATH if not already set
if (NOT DEFINED PICO_SDK_PATH)
    set(PICO_SDK_PATH ${CMAKE_CURRENT_SOURCE_DIR}/vendor/pico-sdk)
endif ()

# Include the Pico SDK
set(PICO_SDK_PATH ${PICO_SDK_PATH} CACHE PATH "Location of pico-sdk")
if (NOT EXISTS ${PICO_SDK_PATH})
    message(FATAL_ERROR "PICO_SDK_PATH (${PICO_SDK_PATH}) not found")
endif ()
include(${PICO_SDK_PATH}/pico_sdk_init.cmake)
