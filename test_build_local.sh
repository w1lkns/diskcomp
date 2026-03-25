#!/bin/bash
# Test binary build locally to simulate CI environment

echo "=== Testing Binary Build Locally ==="

# Check if we're in the right directory
if [ ! -f "diskcomp.spec" ]; then
    echo "❌ Must run from diskcomp project root"
    exit 1
fi

# Install PyInstaller if not available
if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo "Installing PyInstaller..."
    pip3 install pyinstaller
fi

# Make build script executable
chmod +x build_binary.sh

# Run the build
echo "Running build..."
./build_binary.sh

echo "=== Build Test Complete ==="