#!/bin/bash
# Build script for Digital Twin Engine

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/build"

echo "========================================"
echo "Digital Twin Engine Build Script"
echo "========================================"

# Check dependencies
echo "Checking dependencies..."

if ! command -v cmake &> /dev/null; then
    echo "ERROR: CMake not found. Install with: sudo apt install cmake"
    exit 1
fi

if ! command -v g++ &> /dev/null; then
    echo "ERROR: g++ not found. Install with: sudo apt install g++"
    exit 1
fi

if ! python3 -c "import pybind11" &> /dev/null; then
    echo "Installing pybind11..."
    pip install pybind11
fi

# Create build directory
echo "Creating build directory..."
mkdir -p "${BUILD_DIR}"
cd "${BUILD_DIR}"

# Configure
echo "Configuring with CMake..."
cmake .. -DCMAKE_BUILD_TYPE=Release

# Build
echo "Building..."
make -j$(nproc)

# Run tests
echo ""
echo "Running tests..."
./test_engine

# Show output location
echo ""
echo "========================================"
echo "Build complete!"
echo "========================================"
echo ""
echo "Output files:"
echo "  - Library: ${BUILD_DIR}/libtwin_engine.so"
echo "  - Python module: ${BUILD_DIR}/twin_engine_py*.so"
echo "  - Test binary: ${BUILD_DIR}/test_engine"
echo ""
echo "To use in Python:"
echo "  export PYTHONPATH=${BUILD_DIR}:\$PYTHONPATH"
echo "  python3 -c 'import twin_engine_py as te; te.print_info()'"
echo ""
