---
phase: 07-ux-polish-single-drive-mode
plan: 04
subsystem: CLI/UX
tags: [first-run-wizard, menu, help-guide, interactive-mode]
status: complete
dependency_graph:
  requires: [07-01, 07-02, 07-03]
  provides: [show_first_run_menu, show_help_guide, menu-routing-in-main]
  affects: [interactive-mode-experience, user-onboarding]
tech_stack:
  added: []
  patterns: [input-retry-loop, menu-routing, function-composition]
key_files:
  created: []
  modified:
    - diskcomp/cli.py (show_first_run_menu, show_help_guide, main menu routing)
    - tests/test_cli.py (10 new tests for menu and help, 3 updated TestInteractiveMode tests)
decisions:
  - D-07: Menu options are 1) Compare two drives, 2) Clean up a single drive, 3) Help, 4) Quit
  - D-08: Option 1 routes to existing interactive_drive_picker() flow (two-drive mode)
  - D-09: Option 2 breaks out of menu for single-drive flow (Plan 06 implementation)
  - D-10: Option 3 displays help guide with safety facts and returns to menu
  - D-11: Option 4 exits cleanly with code 0 and "Goodbye!" message
  - Menu displays after startup banner when in interactive mode (no-args)
  - Invalid input triggers retry loop, showing error and menu again
metrics:
  duration: "~30 minutes"
  completed_date: "2026-03-23"
  tests_added: 10
  tests_updated: 3
  total_cli_tests: 39
---

# Phase 7 Plan 4: First-Run Wizard Menu Summary

**Objective:** Implement first-run wizard menu-driven entry point for diskcomp that displays 4 options and routes to appropriate flows.

**One-liner:** Menu-driven wizard entry point with 4 options (compare drives, cleanup single drive, help, quit) and plain-English help guide for non-technical users.

## What Was Built

Implemented a first-run wizard menu displayed when diskcomp runs in interactive mode (no command-line arguments). The menu provides a numbered list of 4 options:

1. **Compare two drives** — Routes to existing `interactive_drive_picker()` flow for two-drive duplicate detection
2. **Clean up a single drive** — Breaks out of menu to single-drive cleanup flow (Plan 06)
3. **Help** — Displays quick help guide and returns to menu for another selection
4. **Quit** — Exits cleanly with code 0

## Implementation Details

### Functions Added

**`show_first_run_menu()` in diskcomp/cli.py**
- Displays menu text with 4 options
- Loops on invalid input (0, 5, 'x', etc.), showing error message and menu again
- Returns one of: `'two_drives'`, `'single_drive'`, `'help'`, `'quit'`
- Handles whitespace in user input via `.strip()`

**`show_help_guide()` in diskcomp/cli.py**
- Displays quick help text with:
  - "About diskcomp" paragraph explaining file duplication and dedup purpose
  - "Two modes" section describing both compare-drives and single-drive cleanup
  - "Three safety facts" section covering:
    1. No files deleted without explicit confirmation
    2. Undo log records all deletions with restore option
    3. Read-only drives (backups) are handled safely
  - "More info" footer directing users to `diskcomp --help`

### Menu Wiring in `main()`

- Menu is shown after `show_startup_banner()` in interactive mode (when `is_interactive_mode=True`)
- Menu loop:
  - Displays menu and prompts for selection
  - Routes on selection:
    - `'quit'` → prints "Goodbye!" and returns 0
    - `'help'` → calls `show_help_guide()` and continues loop (back to menu)
    - `'two_drives'` → breaks out to existing two-drive flow
    - `'single_drive'` → breaks out to single-drive flow (Plan 06)

### Tests

10 new tests added to `tests/test_cli.py`:

**TestFirstRunMenu class (7 tests):**
- `test_show_first_run_menu_option_1()` — Verifies '1' returns 'two_drives'
- `test_show_first_run_menu_option_2()` — Verifies '2' returns 'single_drive'
- `test_show_first_run_menu_option_3()` — Verifies '3' returns 'help'
- `test_show_first_run_menu_option_4()` — Verifies '4' returns 'quit'
- `test_show_first_run_menu_invalid_then_valid()` — Verifies retry loop: ['0', '5', 'x', '1'] calls input() 4 times
- `test_show_first_run_menu_whitespace_stripped()` — Verifies '  2  ' is handled correctly
- `test_show_first_run_menu_displays_menu()` — Verifies menu text is printed (contains all 4 options)

**TestHelpGuide class (3 tests):**
- `test_show_help_guide_output()` — Verifies "diskcomp", "Two modes", "safety" all appear in output
- `test_show_help_guide_includes_safety_facts()` — Verifies "explicit confirmation", "undo log", "read-only" appear
- `test_show_help_guide_includes_all_modes()` — Verifies "two drives" and "single drive" both mentioned

### Test Fixes

Updated 3 existing tests in `TestInteractiveMode` class to mock `show_first_run_menu`:
- `test_main_no_args_calls_interactive_picker()` — Added `@patch('diskcomp.cli.show_first_run_menu')` and set `mock_menu.return_value = 'two_drives'` to prevent menu loop hang
- `test_main_with_args_skips_interactive()` — Added menu mock and assertion that it's NOT called when flags provided
- `test_main_interactive_picker_fails()` — Added menu mock returning 'two_drives' to route to picker test

## Verification

All tests pass:
- 10 new tests in TestFirstRunMenu + TestHelpGuide: PASSED
- 3 updated TestInteractiveMode tests: PASSED
- Full CLI test suite: 39/39 PASSED
- Menu displays correctly with all 4 options
- Invalid input ('0', '5', 'x') triggers retry with error message
- Menu loops back after help is shown
- Quit option exits with code 0

## Files Modified

- **diskcomp/cli.py** (342 lines → ~415 lines):
  - Added `show_first_run_menu()` function (30 lines)
  - Added `show_help_guide()` function (33 lines)
  - Modified `main()` to display banner, then show menu with routing (22 lines)

- **tests/test_cli.py** (381 lines → ~545 lines):
  - Added TestFirstRunMenu class with 7 tests (85 lines)
  - Added TestHelpGuide class with 3 tests (35 lines)
  - Updated 3 existing TestInteractiveMode tests with menu mocks (15 lines changes)

## Known Issues

None. All success criteria met and tests passing.

## Decisions Made

All decisions from plan frontmatter (D-07 through D-11) implemented:
- Menu options hardcoded as described (no aliases)
- Menu shows after banner in interactive mode only
- Invalid input triggers retry (no silent fallback)
- Help option loops back to menu (no exit)
- Quit option exits cleanly

## What's Next

Plan 05 (Single-Drive Dedup) and Plan 06 (Single-Drive Flow) will implement the `'single_drive'` branch of the menu routing. Plan 05 will implement the core single-drive deduplication logic, and Plan 06 will wire it into the CLI flow that the menu breaks out to.
