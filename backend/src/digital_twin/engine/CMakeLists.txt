cmake_minimum_required(VERSION 3.14)
project(DigitalTwinEngine VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# Build type
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

# Optimization flags
set(CMAKE_CXX_FLAGS_RELEASE "-O3 -DNDEBUG")
set(CMAKE_CXX_FLAGS_DEBUG "-g -O0")

# Include directories
include_directories(${CMAKE_SOURCE_DIR}/include)

# Source files
set(ENGINE_SOURCES
    src/laplace_solver.cpp
    src/whatif_simulator.cpp
)

# Header files
set(ENGINE_HEADERS
    include/laplace_solver.hpp
    include/whatif_simulator.hpp
    include/digital_twin_engine.hpp
)

# Static library for the engine
add_library(twin_engine_static STATIC ${ENGINE_SOURCES})
target_include_directories(twin_engine_static PUBLIC ${CMAKE_SOURCE_DIR}/include)

# Shared library
add_library(twin_engine SHARED ${ENGINE_SOURCES})
target_include_directories(twin_engine PUBLIC ${CMAKE_SOURCE_DIR}/include)

# ============================================
# Python Bindings with pybind11
# ============================================
find_package(Python3 COMPONENTS Interpreter Development REQUIRED)

# Fetch pybind11
include(FetchContent)
FetchContent_Declare(
    pybind11
    GIT_REPOSITORY https://github.com/pybind/pybind11.git
    GIT_TAG v2.11.1
)
FetchContent_MakeAvailable(pybind11)

# Python module
pybind11_add_module(twin_engine_py python/bindings.cpp ${ENGINE_SOURCES})
target_include_directories(twin_engine_py PRIVATE ${CMAKE_SOURCE_DIR}/include)

# Set output name without 'lib' prefix
set_target_properties(twin_engine_py PROPERTIES
    OUTPUT_NAME "twin_engine_py"
    PREFIX ""
)

# ============================================
# Test executable
# ============================================
add_executable(test_engine tests/test_engine.cpp)
target_link_libraries(test_engine PRIVATE twin_engine_static)

# ============================================
# Installation
# ============================================
install(TARGETS twin_engine twin_engine_static
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
)

install(FILES ${ENGINE_HEADERS}
    DESTINATION include/digital_twin
)

# Print configuration
message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")
message(STATUS "C++ Standard: ${CMAKE_CXX_STANDARD}")
message(STATUS "Python executable: ${Python3_EXECUTABLE}")
