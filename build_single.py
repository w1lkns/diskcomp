#!/usr/bin/env python3
"""
Build script to generate diskcomp.py from package modules in dependency order.

Reads diskcomp/ modules and inlines them into a single executable file with:
- Shebang and auto-generated header
- All stdlib imports deduplicated and sorted
- All module code inlined sequentially
- No internal package imports (all relative imports removed)
"""

import os
import re
from pathlib import Path

# Module dependency order (no internal package imports after inlining)
MODULES_IN_ORDER = [
    "types.py",           # base dataclasses, no internal deps
    "ansi_codes.py",      # ANSI constants, no internal deps
    "scanner.py",         # imports types
    "hasher.py",          # imports types
    "reporter.py",        # imports types
    "benchmarker.py",     # stdlib only
    "health.py",          # imports types, benchmarker
    "drive_picker.py",    # imports types, health
    "ui.py",              # imports ansi_codes (rich optional via try/except)
    "deletion.py",        # imports types
    "cli.py",             # imports all of the above
]

# Standard library modules to collect and deduplicate
STDLIB_MODULES = {
    "os", "sys", "json", "csv", "hashlib", "datetime",
    "typing", "dataclasses", "pathlib", "shutil", "subprocess",
    "tempfile", "re", "collections", "enum", "abc", "stat",
    "argparse", "time", "platform", "textwrap", "warnings",
    "contextlib", "io"
}

def extract_stdlib_imports(content):
    """Extract all stdlib import lines from module content."""
    imports = set()

    # Match: import X, import X as Y, from X import Y, from X import Y as Z
    import_pattern = re.compile(r"^(?:from\s+(\w+)|import\s+(\w+))", re.MULTILINE)

    for match in import_pattern.finditer(content):
        module = match.group(1) or match.group(2)
        if module in STDLIB_MODULES:
            # Extract the full import line
            line_start = content.rfind('\n', 0, match.start()) + 1
            line_end = content.find('\n', match.end())
            if line_end == -1:
                line_end = len(content)
            full_line = content[line_start:line_end].strip()
            if full_line:
                imports.add(full_line)

    return imports


def strip_module_docstring(content):
    """Remove leading module docstring if present."""
    # Match triple-quoted docstrings at the start (after shebang/comments)
    lines = content.split('\n')
    idx = 0

    # Skip shebang and encoding comments
    while idx < len(lines) and (
        lines[idx].startswith('#!') or
        lines[idx].startswith('# -*- coding') or
        lines[idx].startswith('# coding:') or
        lines[idx].strip() == ''
    ):
        idx += 1

    # Check for docstring
    if idx < len(lines):
        line = lines[idx].strip()
        if line.startswith('"""') or line.startswith("'''"):
            quote = '"""' if line.startswith('"""') else "'''"
            # Find closing quote
            if line.count(quote) >= 2:
                # Single-line docstring
                idx += 1
            else:
                # Multi-line docstring
                idx += 1
                while idx < len(lines):
                    if quote in lines[idx]:
                        idx += 1
                        break
                    idx += 1

    return '\n'.join(lines[idx:])


def remove_internal_imports(content):
    """Remove 'from diskcomp.xxx import' and 'import diskcomp.xxx' lines."""
    lines = content.split('\n')
    filtered = []

    for line in lines:
        # Skip diskcomp imports (will be inlined)
        if re.match(r"^\s*from\s+diskcomp\.|^\s*import\s+diskcomp", line):
            continue
        filtered.append(line)

    return '\n'.join(filtered)


def read_and_process_module(module_path):
    """Read a module file and extract its code (no docstring, no internal imports)."""
    with open(module_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Strip module-level docstring
    content = strip_module_docstring(content)

    # Remove internal diskcomp imports
    content = remove_internal_imports(content)

    return content.rstrip()  # Remove trailing whitespace


def build_single_file():
    """Build diskcomp.py from modules in dependency order."""
    project_root = Path(__file__).parent
    diskcomp_dir = project_root / "diskcomp"
    output_file = project_root / "diskcomp.py"

    # Collect all stdlib imports
    all_imports = set()
    module_codes = []

    print("Building diskcomp.py...")

    for module_name in MODULES_IN_ORDER:
        module_path = diskcomp_dir / module_name
        if not module_path.exists():
            print(f"⚠ Warning: {module_name} not found, skipping")
            continue

        print(f"  Reading {module_name}...", end=" ")

        with open(module_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract imports
        imports = extract_stdlib_imports(content)
        all_imports.update(imports)

        # Process module
        processed = read_and_process_module(module_path)
        module_codes.append((module_name, processed))

        print("✓")

    # Sort imports
    sorted_imports = sorted(all_imports)

    # Write output file
    with open(output_file, 'w', encoding='utf-8') as f:
        # Shebang
        f.write("#!/usr/bin/env python3\n")

        # Header comment
        f.write("# Auto-generated by build_single.py — do not edit directly\n\n")

        # All imports
        for imp in sorted_imports:
            f.write(imp + "\n")

        # Blank line
        f.write("\n")

        # All module code
        for module_name, code in module_codes:
            f.write(f"# --- {module_name} ---\n")
            f.write(code)
            f.write("\n\n")

    print(f"\n✓ Generated {output_file} ({len(module_codes)} modules, {len(sorted_imports)} stdlib imports)")
    return output_file


if __name__ == "__main__":
    build_single_file()
