#!/bin/bash
# Build diskcomp binary for current platform using PyInstaller
set -e

echo "Building diskcomp binary..."

# Clean previous builds
rm -rf build/ dist/

# Build with PyInstaller spec
pyinstaller diskcomp.spec --clean

# Get binary info
BINARY_PATH="dist/diskcomp"
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    BINARY_PATH="dist/diskcomp.exe"
fi

if [ -f "$BINARY_PATH" ]; then
    BINARY_SIZE=$(du -h "$BINARY_PATH" | cut -f1)
    echo "✅ Binary built successfully: $BINARY_PATH ($BINARY_SIZE)"
    
    # Test the binary
    echo "Testing binary..."
    if "$BINARY_PATH" --help > /dev/null 2>&1; then
        echo "✅ Binary test passed"
    else
        echo "❌ Binary test failed"
        exit 1
    fi
else
    echo "❌ Binary build failed"
    exit 1
fi

echo "Build complete!"