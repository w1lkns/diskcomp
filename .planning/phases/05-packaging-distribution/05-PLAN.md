---
phase: 05-packaging-distribution
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - pyproject.toml
  - build_single.py
  - .github/workflows/ci.yml
  - README.md
  - .gitignore
autonomous: true
requirements:
  - DIST-01
  - DIST-02
  - DIST-03
  - DIST-04
user_setup: []

must_haves:
  truths:
    - "pip install -e . succeeds and creates diskcomp CLI command"
    - "python3 diskcomp.py --help works with zero dependencies"
    - "diskcomp.py is generated from diskcomp/ package modules in correct dependency order"
    - "CI passes on macOS + Linux + Windows × Python 3.8, 3.10, 3.12 (9 matrix combos)"
    - "README documents both install paths and covers safety model"
  artifacts:
    - path: "pyproject.toml"
      provides: "Package metadata, entry point definition, optional dependencies, build backend config"
      exports: "[project], [project.scripts], [project.optional-dependencies]"
    - path: "build_single.py"
      provides: "Dev script to generate diskcomp.py from package modules in dependency order"
      exports: "main() function, MODULES_IN_ORDER constant"
    - path: "diskcomp.py"
      provides: "Auto-generated single-file executable with all modules inlined, zero dependencies"
      note: "Generated artifact, never edited manually, added to .gitignore"
    - path: ".github/workflows/ci.yml"
      provides: "GitHub Actions matrix testing: 3 OS × 3 Python versions = 9 jobs"
      exports: "test job with matrix strategy"
    - path: "README.md"
      provides: "Public-facing documentation with install paths, usage, badges, safety model"
      exports: "CI status badge, PyPI version badge, install sections"
  key_links:
    - from: "pyproject.toml"
      to: "diskcomp.cli:main"
      via: "[project.scripts] entry point"
      pattern: "diskcomp = diskcomp.cli:main"
    - from: "build_single.py"
      to: "diskcomp.py"
      via: "script execution generates artifact"
      pattern: "python build_single.py"
    - from: ".github/workflows/ci.yml"
      to: "pyproject.toml"
      via: "CI installs package from pyproject.toml"
      pattern: "pip install -e ."
    - from: "README.md"
      to: "pyproject.toml"
      via: "Badge URLs reference GitHub Actions workflow"
      pattern: "github.com/.../workflows/ci.yml/badge.svg"

---

<objective>
Make diskcomp installable and shareable in under 60 seconds via two parallel paths:
1. `pip install diskcomp` — installs a working `diskcomp` CLI command
2. `python3 diskcomp.py` — single-file executable, zero mandatory dependencies

CI validates cross-platform compatibility (macOS, Linux, Windows × Python 3.8, 3.10, 3.12).
README makes it public-facing and user-friendly.
No PyPI publish this phase — machinery only.

Purpose: Package Phase 1-4 work into shareable, installable form.
Output: pyproject.toml, build_single.py, diskcomp.py (generated), .github/workflows/ci.yml, README.md, updated .gitignore
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/REQUIREMENTS.md
@.planning/ROADMAP.md
@.planning/05-packaging-distribution/05-CONTEXT.md
@.planning/05-packaging-distribution/RESEARCH.md

@diskcomp/__init__.py — version string, author, public API exports
@diskcomp/cli.py — main() function entry point
@diskcomp/types.py — base dataclasses, no internal deps
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create pyproject.toml with metadata and entry point (per D-04, D-05)</name>
  <files>pyproject.toml</files>
  <action>
Create pyproject.toml at project root with:
- [build-system]: requires = ["hatchling"], build-backend = "hatchling.build" (per RESEARCH.md, D-02 standard stack)
- [project]: name="diskcomp", version="0.1.0" (from diskcomp/__init__.py), description, author "Wilkins Morales", license MIT, requires-python=">=3.8", classifiers for 3.8/3.10/3.12
- [project.urls]: Repository, Issues pointing to GitHub
- [project.scripts]: diskcomp = "diskcomp.cli:main" — entry point that creates /usr/local/bin/diskcomp command
- [project.optional-dependencies]: rich = ["rich>=13.0.0"] (per D-05, for graceful fallback in ui.py)
- readme = "README.md" for auto-publish to PyPI (future)
- keywords for discoverability

Module dependency order for reference (used in build_single.py):
  types.py → ansi_codes.py → scanner.py → hasher.py → reporter.py → benchmarker.py → health.py → drive_picker.py → ui.py → deletion.py → cli.py

Version and author hardcoded from diskcomp/__init__.py; do NOT use dynamic version discovery (keep it simple).
Hatchling auto-detects diskcomp/ package structure — no setup.py needed.
  </action>
  <verify>
    <automated>python3 -c "import tomllib; f=open('pyproject.toml','rb'); c=tomllib.load(f); assert c['build-system']['build-backend']=='hatchling.build'; assert c['project']['name']=='diskcomp'; assert c['project']['version']=='0.1.0'; assert c['project']['scripts']['diskcomp']=='diskcomp.cli:main'; assert 'rich' in c['project']['optional-dependencies']; print('✓ pyproject.toml valid')"</automated>
  </verify>
  <done>pyproject.toml exists at project root with valid TOML syntax, hatchling build backend, entry point definition, and optional dependencies</done>
</task>

<task type="auto">
  <name>Task 2: Create build_single.py script to generate diskcomp.py (per D-01, D-02, D-03)</name>
  <files>build_single.py</files>
  <action>
Create build_single.py at project root. This is a dev utility that reads diskcomp/ modules in dependency order and writes diskcomp.py with all modules inlined.

Module concatenation order (from CONTEXT.md dependency graph):
  1. types.py — base dataclasses, no internal deps
  2. ansi_codes.py — ANSI constants, no internal deps
  3. scanner.py — imports types
  4. hasher.py — imports types
  5. reporter.py — imports types
  6. benchmarker.py — stdlib only
  7. health.py — imports types, benchmarker
  8. drive_picker.py — imports types, health
  9. ui.py — imports ansi_codes (rich is optional with try/except)
  10. deletion.py — imports types
  11. cli.py — imports all of the above

Algorithm:
  For each module in order:
    - Read module file
    - Extract all stdlib imports (os, sys, json, csv, hashlib, datetime, typing, dataclasses) — collect into set
    - Skip lines matching: from diskcomp.xxx import / import diskcomp.xxx
    - Keep all class, def, CONSTANT definitions
    - Keep if __name__ == "__main__": guards (do NOT strip)
    - Skip leading module docstring from bundled modules (keep only code)

  Deduplicate stdlib imports, sort alphabetically, write to diskcomp.py with:
    1. Shebang: #!/usr/bin/env python3
    2. Comment header: # Auto-generated by build_single.py — do not edit directly
    3. All deduplicated stdlib imports (sorted)
    4. Blank line
    5. All module code inlined sequentially

Critical gotchas (from RESEARCH.md):
  - Do NOT leave relative imports (from diskcomp.xxx) — classes/funcs will be in global scope of bundled file
  - DO preserve try/except blocks for optional imports (rich in ui.py) — these are already correct
  - DO preserve if __name__ == "__main__": guards in cli.py
  - DO strip module-level docstrings but preserve code

Write the script to handle all 11 modules. Test by running: python build_single.py && python diskcomp.py --help
  </action>
  <verify>
    <automated>python3 build_single.py && python3 diskcomp.py --help | head -5</automated>
  </verify>
  <done>build_single.py exists at project root, is executable, generates diskcomp.py without errors, and the generated diskcomp.py responds to --help</done>
</task>

<task type="auto">
  <name>Task 3: Generate diskcomp.py and verify standalone execution (per D-01)</name>
  <files>diskcomp.py</files>
  <action>
Run build_single.py to generate diskcomp.py:
  python3 build_single.py

Verify the generated diskcomp.py:
  - Has shebang line: #!/usr/bin/env python3
  - Has comment: # Auto-generated by build_single.py — do not edit directly
  - Contains all 11 module definitions inlined (no import diskcomp.xxx statements)
  - Has stdlib imports at top (deduplicated, sorted)
  - Responds to --help: python3 diskcomp.py --help
  - Can run a dry-run scan: python3 diskcomp.py --dry-run /tmp /tmp (exits 0 or 1 gracefully)

Verify it has NO internal package imports (grep should return empty):
  grep -E "^from diskcomp|^import diskcomp" diskcomp.py

diskcomp.py is the generated artifact — add to .gitignore so it's never committed.
  </action>
  <verify>
    <automated>python3 diskcomp.py --help | grep -q "Compare two drives" && echo "✓ diskcomp.py --help works"</automated>
  </verify>
  <done>diskcomp.py generated and executable as standalone script; --help works; no internal package imports remain</done>
</task>

<task type="auto">
  <name>Task 4: Create .github/workflows/ci.yml with matrix testing (per D-07, D-08, D-09)</name>
  <files>.github/workflows/ci.yml</files>
  <action>
Create .github/workflows/ci.yml (directory .github/workflows/ must exist).

Matrix config (per D-07):
  - os: ubuntu-latest, macos-latest, windows-latest
  - python-version: "3.8", "3.10", "3.12"
  - 9 total job combinations
  - fail-fast: false (continue all tests even if one fails)

Trigger on (per D-09):
  - push to main branch
  - pull_request to main branch

Test steps:
  1. actions/checkout@v4 — check out code
  2. actions/setup-python@v5 with matrix.python-version, cache: pip
  3. pip install -e . — install package in editable mode (installs from pyproject.toml)
  4. python -m unittest discover tests/ — run full test suite
  5. python build_single.py && python diskcomp.py --help — verify single-file build works

No publish step (per D-08) — validation only.
No environment secrets needed — public repo.
  </action>
  <verify>
    <automated>python3 -c "import yaml; f=open('.github/workflows/ci.yml'); c=yaml.safe_load(f); assert 'matrix' in c['jobs']['test']['strategy']; assert len(c['jobs']['test']['strategy']['matrix']['os']) == 3; assert len(c['jobs']['test']['strategy']['matrix']['python-version']) == 3; print('✓ ci.yml valid')" 2>/dev/null || echo "YAML check skipped (pyyaml not installed), manual verify file exists"</automated>
  </verify>
  <done>.github/workflows/ci.yml exists with matrix strategy (3 OS × 3 Python versions), triggers on push+PR, runs tests and single-file build, no publish step</done>
</task>

<task type="auto">
  <name>Task 5: Create .gitignore entries for generated artifacts (per D-01)</name>
  <files>.gitignore</files>
  <action>
Add diskcomp.py to .gitignore (or create .gitignore if it doesn't exist).

diskcomp.py is a generated artifact from build_single.py — never commit to git.
Users who need it download from releases or GitHub raw URL.

If .gitignore exists, append:
  diskcomp.py

If .gitignore doesn't exist, create it with:
  diskcomp.py

Keep file minimal; add other entries if they already exist in project (venv/, __pycache__/, etc.).
  </action>
  <verify>
    <automated>grep -q "^diskcomp\.py$" .gitignore && echo "✓ diskcomp.py in .gitignore" || echo "ERROR: diskcomp.py not in .gitignore"</automated>
  </verify>
  <done>.gitignore updated to exclude diskcomp.py</done>
</task>

<task type="auto">
  <name>Task 6: Create README.md with install paths, usage, badges, and safety model (per D-10, D-11, D-12)</name>
  <files>README.md</files>
  <action>
Create README.md at project root with badges-first format and practical sections.

Structure:
  1. Title: "diskcomp"
  2. Badges row:
     - CI Status: https://github.com/{user}/diskcomp/workflows/CI/badge.svg (replace {user} with w1lkns)
     - PyPI Version: https://img.shields.io/pypi/v/diskcomp.svg
  3. One-liner: "Compare two drives and find duplicate files. Zero dependencies, cross-platform, with undo."

  4. ## Install
     Two parallel paths (per D-12):
     a) pip install diskcomp — requires pyproject.toml setup, creates diskcomp command
        pip install -e . (development)
        pip install diskcomp (future, after PyPI publish)
        pip install diskcomp[rich] (with optional Rich enhancement)
     b) Single-file: Download diskcomp.py from GitHub, run python3 diskcomp.py --help
        - Link: https://raw.githubusercontent.com/w1lkns/diskcomp/main/diskcomp.py
        - No dependencies required

  5. ## Quick Start
     Basic usage examples:
     - Interactive mode: python3 -m diskcomp (no args, prompts for drives)
     - Command-line: python3 -m diskcomp --keep /path/A --other /path/B
     - With flags: python3 -m diskcomp --keep /path/A --other /path/B --dry-run

  6. ## Usage & Flags
     Table of flags:
     - --keep PATH — path to "keep" drive (required or interactive mode)
     - --other PATH — path to "other" drive (required or interactive mode)
     - --dry-run — walk and count files without hashing
     - --limit N — hash only first N files per drive (testing)
     - --output PATH — custom report path
     - --format csv|json — report format
     - --delete-from REPORT — load existing report for deletion workflow
     - --undo LOG — view audit log of deleted files

  7. ## Safety Model
     User is always in control:
     - No automatic deletion (always asks for confirmation)
     - Undo log written before any file is deleted
     - Read-only filesystem detection prevents accidental writes
     - --dry-run mode for preview without side effects

  8. ## Optional Enhancements
     - Rich: pip install diskcomp[rich] for professional progress bars and styling
     - smartmontools: System package (macOS: brew install smartmontools, Linux: apt-get install smartmontools, Windows: wmic logicaldisk) — enables SMART data display

  9. ## Reports
     - CSV report: action, keep_path, other_path, size_mb, hash columns
     - JSON report: --format json for programmatic use
     - Atomic writes: temp → rename to prevent corruption

  10. License: MIT

Per D-11: No asciinema recordings — text code blocks only (maintainable, doesn't need re-recording).
Per D-10: CI badge auto-updates, PyPI badge works even before publish.

Use GitHub's raw markdown syntax for badges; shields.io URLs work for PyPI version badge.
  </action>
  <verify>
    <automated>grep -q "^# diskcomp" README.md && grep -q "\[!\[CI\]" README.md && grep -q "pip install diskcomp" README.md && echo "✓ README.md has title, badges, and install section" || echo "Missing README sections"</automated>
  </verify>
  <done>README.md created with badges, install paths (pip + single-file), usage examples, flags reference, safety model, optional enhancements, and license section</done>
</task>

<task type="auto">
  <name>Task 7: Verify pip install -e . works and diskcomp CLI command is available (pre-CI check)</name>
  <files></files>
  <action>
Test the package setup before committing:

1. Install in editable mode:
   pip install -e .

2. Verify entry point created:
   which diskcomp (should show path to installed command)
   diskcomp --help (should print help text)

3. Verify optional dependency:
   pip install -e ".[rich]"
   python3 -c "from rich.progress import Progress; print('✓ Rich installed')"

4. Verify graceful fallback without Rich:
   pip uninstall -y rich
   python3 -m diskcomp --help (should work with ANSI fallback, no error)

5. Run full test suite to ensure nothing broke:
   python3 -m unittest discover tests/
   (should pass 179 tests without errors)

6. Verify single-file standalone:
   python3 build_single.py
   python3 diskcomp.py --help
   python3 diskcomp.py --dry-run /tmp /tmp (should run without error)

If any step fails, fix before proceeding to commit.
  </action>
  <verify>
    <automated>pip install -e . && diskcomp --help | grep -q "Compare two drives" && echo "✓ pip install -e . works and diskcomp command available"</automated>
  </verify>
  <done>Package installs successfully, diskcomp CLI command available, optional Rich dependency works, graceful fallback verified, all 179 tests pass, single-file build verified</done>
</task>

</tasks>

<verification>
After completing all tasks, verify the entire phase:

**Checkpoint 1: Package Installation (local)**
```
pip install -e .
diskcomp --help
→ Should print help text without errors
```

**Checkpoint 2: Single-File Execution**
```
python3 diskcomp.py --help
python3 diskcomp.py --dry-run /tmp /tmp
→ Should work without package imports, no dependencies except stdlib
```

**Checkpoint 3: Test Suite**
```
python3 -m unittest discover tests/
→ Should pass all 179 tests without errors
```

**Checkpoint 4: Optional Dependency**
```
pip install -e ".[rich]"
python3 -c "from rich.progress import Progress; print('✓')"
pip uninstall -y rich
python3 -m diskcomp --help
→ Should work both with and without Rich installed
```

**Checkpoint 5: Files Exist**
```
ls -1 pyproject.toml build_single.py diskcomp.py .github/workflows/ci.yml README.md
→ All 5 files should exist
```

**Checkpoint 6: Commit and Validate**
```
git add pyproject.toml build_single.py .github/workflows/ci.yml README.md .gitignore
git commit -m "build: packaging + distribution (pyproject.toml, build_single.py, CI matrix, README)"
→ Should commit without errors
```

**Checkpoint 7: CI Workflow Ready**
```
git push origin main
→ GitHub Actions should trigger 9 matrix jobs (3 OS × 3 Python versions)
→ All jobs should pass: install package, run tests, verify single-file build
```

All checkpoints must pass for phase completion.
</verification>

<success_criteria>
Phase 5 is complete when:
- [ ] pyproject.toml exists with valid metadata, entry point, and optional dependencies
- [ ] build_single.py generates diskcomp.py successfully (shebang + header + all modules inlined, no internal imports)
- [ ] diskcomp.py is executable: python3 diskcomp.py --help works, python3 diskcomp.py --dry-run /tmp /tmp works
- [ ] diskcomp.py is git-ignored (added to .gitignore)
- [ ] .github/workflows/ci.yml exists with 3 OS × 3 Python version matrix, tests on each combo
- [ ] CI passes on all 9 combinations (macOS + Linux + Windows × 3.8, 3.10, 3.12)
- [ ] README.md exists with badges, install paths (pip + single-file), usage, flags, safety model
- [ ] pip install -e . succeeds and creates diskcomp CLI command
- [ ] pip install -e ".[rich]" installs Rich, and uninstalling Rich doesn't break tool (graceful fallback)
- [ ] All 179 existing tests pass without modification
- [ ] Files committed to git and ready for release

Goal: Anyone can install diskcomp in under 60 seconds via `pip install diskcomp` (when published) or `python3 diskcomp.py` (download). Cross-platform CI validates it works everywhere.
</success_criteria>

<output>
After completion, create `.planning/phases/05-packaging-distribution/05-01-SUMMARY.md`

Summary should include:
- Files created: pyproject.toml, build_single.py, .github/workflows/ci.yml, README.md, .gitignore updated
- diskcomp.py generated and verified as standalone
- Package installs via pip with entry point
- CI matrix configured for 9 combinations
- All tests pass (179)
- No PyPI publish this phase (machinery only)
</output>
