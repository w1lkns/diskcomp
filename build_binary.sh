#!/bin/bash
# Build diskcomp binary for current platform using PyInstaller
set -e

echo "Building diskcomp binary for platform: $OSTYPE"
echo "Python version: $(python3 --version)"
echo "PyInstaller version: $(python3 -c 'import PyInstaller; print(PyInstaller.__version__)')"

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build/ dist/

# Verify spec file exists
if [ ! -f "diskcomp.spec" ]; then
    echo "❌ diskcomp.spec not found"
    exit 1
fi

echo "Building with PyInstaller..."
# Build with PyInstaller spec
pyinstaller diskcomp.spec --clean --log-level INFO

# Get binary info
BINARY_PATH="dist/diskcomp"
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    BINARY_PATH="dist/diskcomp.exe"
fi

echo "Checking binary at: $BINARY_PATH"

if [ -f "$BINARY_PATH" ]; then
    BINARY_SIZE=$(du -h "$BINARY_PATH" | cut -f1)
    echo "✅ Binary built successfully: $BINARY_PATH ($BINARY_SIZE)"
    
    # Make binary executable
    chmod +x "$BINARY_PATH"
    
    # Show file info
    file "$BINARY_PATH" || true
    ls -la "$BINARY_PATH"
    
    # Test the binary
    echo "Testing binary..."
    if "$BINARY_PATH" --version > /dev/null 2>&1; then
        echo "✅ Binary --version test passed"
    elif "$BINARY_PATH" --help > /dev/null 2>&1; then
        echo "✅ Binary --help test passed"  
    else
        echo "❌ Binary test failed"
        echo "Attempting to run binary with no args..."
        "$BINARY_PATH" || echo "Binary failed to run"
        exit 1
    fi
else
    echo "❌ Binary build failed - file not found: $BINARY_PATH"
    echo "Contents of dist directory:"
    ls -la dist/ || echo "No dist directory found"
    exit 1
fi

echo "✅ Build complete!"