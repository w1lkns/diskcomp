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

def collect_stdlib_imports(content, per_module):
    """
    Parse stdlib imports from content and accumulate into per_module dict.

    per_module: {module_name: set_of_names | None}
      - set_of_names: names from 'from X import a, b'
      - None: bare 'import X' (no names to merge)
    """
    lines = content.split('\n')
    for line in lines:
        stripped = line.strip()

        # 'from X import a, b, c'
        from_match = re.match(r'^from\s+(\w+)\s+import\s+(.+)$', stripped)
        if from_match:
            module = from_match.group(1)
            if module in STDLIB_MODULES:
                names_str = from_match.group(2)
                names = [n.strip() for n in names_str.split(',') if n.strip()]
                existing = per_module.get(module)
                if existing is None and module in per_module:
                    # Already registered as bare import — upgrade to named set
                    per_module[module] = set(names)
                else:
                    per_module.setdefault(module, set()).update(names)
            continue

        # 'import X'
        import_match = re.match(r'^import\s+(\w+)', stripped)
        if import_match:
            module = import_match.group(1)
            if module in STDLIB_MODULES and module not in per_module:
                per_module[module] = None  # sentinel: bare import


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


def remove_stdlib_imports(content):
    """Remove stdlib import lines (moved to the consolidated header block)."""
    lines = content.split('\n')
    filtered = []

    for line in lines:
        stripped = line.strip()
        # 'from X import ...' where X is stdlib
        from_match = re.match(r'^from\s+(\w+)\s+import', stripped)
        if from_match and from_match.group(1) in STDLIB_MODULES:
            continue
        # 'import X' where X is stdlib
        import_match = re.match(r'^import\s+(\w+)', stripped)
        if import_match and import_match.group(1) in STDLIB_MODULES:
            continue
        filtered.append(line)

    return '\n'.join(filtered)


def read_and_process_module(module_path):
    """Read a module file and extract its code (no docstring, no imports)."""
    with open(module_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Strip module-level docstring
    content = strip_module_docstring(content)

    # Remove internal diskcomp imports (inlined by bundler)
    content = remove_internal_imports(content)

    # Remove stdlib imports (hoisted to consolidated header block)
    content = remove_stdlib_imports(content)

    return content.rstrip()  # Remove trailing whitespace


def build_single_file():
    """Build diskcomp.py from modules in dependency order."""
    project_root = Path(__file__).parent
    diskcomp_dir = project_root / "diskcomp"
    output_file = project_root / "diskcomp.py"

    # Collect all stdlib imports (accumulated across all modules)
    per_module_imports = {}  # module_name -> set_of_names | None
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

        # Accumulate stdlib imports into shared dict
        collect_stdlib_imports(content, per_module_imports)

        # Process module (strips imports — they go in header)
        processed = read_and_process_module(module_path)
        module_codes.append((module_name, processed))

        print("✓")

    # Build sorted, consolidated import lines (one per stdlib module)
    all_import_lines = []
    for mod, names in sorted(per_module_imports.items()):
        if names is None:
            all_import_lines.append(f"import {mod}")
        else:
            all_import_lines.append(f"from {mod} import {', '.join(sorted(names))}")
    sorted_imports = sorted(all_import_lines)

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
