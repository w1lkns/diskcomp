---
phase: 07-ux-polish-single-drive-mode
plan: 03
subsystem: CLI/UX
tags: [banner, interactive-mode, startup]
requires: []
provides: [startup-banner-function, interactive-mode-detection]
affects: [main(), diskcomp/cli.py, test_cli.py]
tech_stack:
  added: [importlib.metadata]
  patterns: [ASCII art banner, fallback version handling]
key_files:
  created: []
  modified:
    - diskcomp/cli.py
    - tests/test_cli.py
key_decisions:
  - D-04: Banner shown only in interactive (no-args) mode
  - D-05: Tagline exact copy - "Find duplicates. Free space. Stay safe."
  - D-06: Version from importlib.metadata with "1.1.0" fallback for single-file builds
requirements_completed: []
duration: 4 min
completed: 2026-03-23T10:55:09Z
---

# Phase 07 Plan 03: ASCII Startup Banner Summary

Add ASCII startup banner displayed only in interactive (no-args) mode showing logo, tagline, and version.

## What Was Built

**Task 1: Implement show_startup_banner() and integrate into main()**

1. **show_startup_banner() function** (diskcomp/cli.py, lines 287-314)
   - Prints ASCII art "diskcomp" logo with proper formatting
   - Displays exact tagline: "Find duplicates. Free space. Stay safe."
   - Reads version from `importlib.metadata.version('diskcomp')`
   - Falls back to hardcoded "1.1.0" for single-file builds or uninstalled state
   - Adds blank line after banner for clean output

2. **Interactive mode detection** (diskcomp/cli.py, lines 334-342)
   - Detects no-args interactive mode by checking: `not args.keep and not args.other and not args.delete_from and not args.undo`
   - Calls `show_startup_banner()` only when in interactive mode
   - Banner NOT shown when any direct flags are provided

3. **Test coverage** (tests/test_cli.py, TestStartupBanner class, 6 tests)
   - `test_show_startup_banner_output`: Verifies banner contains logo, tagline, and version
   - `test_show_startup_banner_exact_tagline`: Verifies exact D-05 tagline
   - `test_main_shows_banner_no_args`: Verifies banner called in interactive mode
   - `test_main_no_banner_with_keep_flag`: Verifies banner NOT shown with --keep
   - `test_main_no_banner_with_delete_from_flag`: Verifies banner NOT shown with --delete-from
   - `test_main_no_banner_with_undo_flag`: Verifies banner NOT shown with --undo

## Verification

```bash
$ python3 -m pytest tests/test_cli.py::TestStartupBanner -xvs
# Result: 6 passed (100%)

$ python3 -m pytest tests/test_cli.py -x
# Result: 21 passed (100% - all CLI tests including new banner tests)
```

**Manual verification:**
- Banner displays correctly with proper ASCII art
- Tagline matches spec exactly: "Find duplicates. Free space. Stay safe."
- Version displays as "v0.1.0" (from package metadata)
- --help flag does not show banner (argparse intercepts)
- --keep flag suppresses banner (verified by test mocks)

## Files Modified

| File | Changes |
|------|---------|
| `diskcomp/cli.py` | Added `show_startup_banner()` function (28 lines); Added interactive mode detection in `main()` (10 lines) |
| `tests/test_cli.py` | Added import for `show_startup_banner`; Added `TestStartupBanner` class with 6 tests (137 lines) |

## Deviations from Plan

None - plan executed exactly as written.

## Implementation Details

### Banner Function Logic
- Uses try/except to gracefully handle missing `importlib.metadata`
- Fallback version "1.1.0" provides safe default for single-file distributions
- Banner string built with f-string for clean version substitution
- `.strip()` removes leading/trailing whitespace from multi-line string
- Separate `print()` adds blank line for visual separation

### Interactive Mode Detection
- Checks all flag attributes that indicate non-interactive usage
- Placement right after `parse_args()` ensures decision is made early
- Boolean logic is clear and easy to extend if new flags added

### Test Strategy
- Direct tests of `show_startup_banner()` verify output content
- Mocked tests of `main()` verify when banner is called
- Flag-based tests confirm banner suppression in non-interactive modes
- All tests pass with zero failures

## Success Criteria Met

✓ Banner ASCII art displays correctly (logo centered, not malformed)
✓ Tagline exact: "Find duplicates. Free space. Stay safe."
✓ Version reads from importlib.metadata or defaults to "1.1.0"
✓ Banner shown only on `python -m diskcomp` (no args), not on `python -m diskcomp --help` or with flags
✓ Tests pass; no stdout pollution in non-interactive modes
✓ Code follows project conventions

## Self-Check: PASSED

- ✓ `diskcomp/cli.py` exists with `show_startup_banner()` at line 287
- ✓ `diskcomp/cli.py` main() includes interactive mode detection at lines 334-342
- ✓ `tests/test_cli.py` imports `show_startup_banner` at line 7
- ✓ `tests/test_cli.py` contains TestStartupBanner class with 6 tests
- ✓ All 21 tests in test_cli.py pass
- ✓ Git commit `bfd8273` contains both files with changes
- ✓ Banner displays correctly with version and tagline
