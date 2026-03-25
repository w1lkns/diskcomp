#!/bin/bash

# diskcomp v1.0.3 Publishing Script
# This script builds and publishes diskcomp to PyPI

set -e

echo "🏗️  Building diskcomp v1.0.3..."

# Create clean build environment
rm -rf venv-build dist/ build/ *.egg-info/
python3 -m venv venv-build
source venv-build/bin/activate

# Install build tools
pip install --upgrade build twine

# Build the package
python -m build

# Check the package
python -m twine check dist/*

echo "✅ Package built successfully!"
echo ""
echo "📦 Files created:"
ls -la dist/

echo ""
echo "🚀 To publish to PyPI, run:"
echo "   source venv-build/bin/activate"
echo "   python -m twine upload dist/*"
echo ""
echo "🧪 To test on TestPyPI first, run:"
echo "   python -m twine upload --repository testpypi dist/*"
echo ""
echo "📝 You'll need your PyPI API token when prompted."
echo "   Get it from: https://pypi.org/manage/account/token/"

# Clean up
deactivate 2>/dev/null || true