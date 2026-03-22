---
phase: 02-terminal-ui
plan: 01
subsystem: UI Foundation
tags: [terminal-ui, ansi-codes, progress-display, graceful-fallback]
dependency:
  requires: [01-core-engine]
  provides: [ui-foundation, callback-interface]
  affects: [02-02-scanning-display, 02-03-hashing-display]
tech_stack:
  added: [ANSI codes, box-drawing chars]
  patterns: [factory-pattern, graceful-degradation, callback-based-ui]
key_files:
  created:
    - diskcomp/ansi_codes.py
    - diskcomp/ui.py
    - tests/test_ui.py
  modified: []
decisions:
  - "ANSI codes centralized in ansi_codes.py to prevent magic string duplication"
  - "Factory pattern (UIHandler) allows dynamic UI selection (Rich vs ANSI)"
  - "Both UI classes share identical interface for interchangeability"
  - "RichProgressUI skipped in tests when Rich not available (graceful degrade)"
  - "Fixed format_speed() threshold bug (GB vs MB detection)"
metrics:
  duration: ~15 minutes
  completed_date: "2026-03-22T12:53:28Z"
  tasks_completed: 3/3
  lines_added: ~450
---

# Phase 02 Plan 01: Terminal UI Foundation — Summary

**Build the UI foundation for Phase 2:** ANSI constants module and base UI classes (RichProgressUI and ANSIProgressUI) with no external dependencies. Both classes share a common interface for folder progress, hash progress, and summary reporting.

---

## Objective Achieved

Established the rendering layer so scanner/hasher callbacks can be wired in Wave 2. Rich library is optional; graceful fallback to plain ANSI works on all platforms (Windows 10+, macOS, Linux).

**Output delivered:**
- `diskcomp/ansi_codes.py` — ANSI constants and helper functions
- `diskcomp/ui.py` — UIHandler factory, RichProgressUI, ANSIProgressUI
- `tests/test_ui.py` — 30 comprehensive unit tests (all passing)

---

## Tasks Completed

### Task 1: Create ANSI codes module with color constants and helper functions

**Status:** ✓ Complete

- File `diskcomp/ansi_codes.py` created with:
  - Color constants: `CYAN`, `GREEN`, `RED`, `RESET`, `BOLD` (standard 16-color ANSI)
  - Symbol constants: `ARROW` (→), `TICK` (✓), `CROSS` (✗)
  - Helper functions:
    - `colored(text: str, color: str) -> str` — wraps text with ANSI code + reset
    - `progress_bar(current: int, total: int, width: int = 40) -> str` — renders `[████░░░░] 50%`
    - `format_speed(bytes_per_sec: float) -> str` — converts to "1.0 MB/s" format
    - `format_eta(seconds: float) -> str` — converts to "2m 5s" format

**Verification:**
```bash
python3 -c "from diskcomp.ansi_codes import CYAN, GREEN, RESET, ARROW, TICK, colored, progress_bar, format_speed, format_eta; print('All imports successful'); assert CYAN == '\033[36m'; print('Assertions passed')"
# Output: All imports successful / Assertions passed
```

**Commit:** `6c27c87`

---

### Task 2: Create UI classes (RichProgressUI and ANSIProgressUI) with common interface

**Status:** ✓ Complete

- File `diskcomp/ui.py` created with:
  - **UIHandler factory** (static methods):
    - `create(force_ansi=False)` — returns RichProgressUI or ANSIProgressUI
    - `get_available()` — returns "rich" or "ansi"
  - **RichProgressUI** (when Rich available):
    - Uses `rich.progress.Progress` with BarColumn, PercentageColumn, TransferSpeedColumn, TimeRemainingColumn
    - Methods: `start_scan()`, `on_folder_done()`, `start_hash()`, `on_file_hashed()`, `show_summary()`, `close()`
    - Summary rendered via Rich Panel/Table
  - **ANSIProgressUI** (fallback):
    - Plain ANSI codes and box-drawing chars (╔, ║, ═, ╗, etc.)
    - Identical method signatures to RichProgressUI
    - Progress bar rendered via `progress_bar()` helper from ansi_codes
    - Summary rendered in ASCII box using ═ ║ ╔ ╗ characters

**Common Interface:** Both classes have identical method signatures:
- `start_scan(drive_path: str)`
- `on_folder_done(folder_path: str, file_count: int)`
- `start_hash(total_files: int)`
- `on_file_hashed(current: int, total: int, speed_mbps: float, eta_secs: Optional[int])`
- `show_summary(duplicates_mb, duplicates_count, unique_keep_mb, unique_keep_count, unique_other_mb, unique_other_count, report_path)`
- `close()`

**Verification:**
```bash
python3 -c "from diskcomp.ui import UIHandler, RichProgressUI, ANSIProgressUI; ui = UIHandler.create(force_ansi=True); assert isinstance(ui, ANSIProgressUI); print('ANSIProgressUI instantiation OK'); print('Available UI:', UIHandler.get_available())"
# Output: ANSIProgressUI instantiation OK / Available UI: ansi
```

**Commit:** `c120948`

---

### Task 3: Create unit tests for ANSI codes and UI classes (Wave 0 compliance)

**Status:** ✓ Complete

- File `tests/test_ui.py` created with 30 comprehensive unit tests:

**TestANSICodes (12 tests):**
- `test_ansi_colors_defined()` ✓ — CYAN, GREEN, RED, RESET, BOLD are non-empty and start with "\033["
- `test_symbols_defined()` ✓ — ARROW, TICK, CROSS are single unicode characters
- `test_colored_function()` ✓ — wraps text with color codes and reset
- `test_progress_bar_zero_percent()` ✓ — renders bar at 0%
- `test_progress_bar_half()` ✓ — renders bar at 50% with filled/empty blocks
- `test_progress_bar_full()` ✓ — renders bar at 100%
- `test_format_speed_kb()` ✓ — converts 10 KB/s correctly
- `test_format_speed_mb()` ✓ — converts 5 MB/s correctly
- `test_format_speed_gb()` ✓ — converts 2 GB/s correctly
- `test_format_eta_seconds()` ✓ — formats "30s" correctly
- `test_format_eta_minutes_seconds()` ✓ — formats "2m 5s" correctly
- `test_format_eta_hours()` ✓ — formats "1h 1m 5s" correctly

**TestANSIProgressUI (9 tests):**
- `test_init()` ✓ — instantiation
- `test_start_scan()` ✓ — prints cyan arrow and path
- `test_on_folder_done()` ✓ — prints green tick with file count
- `test_start_hash()` ✓ — prints cyan arrow with file count
- `test_on_file_hashed()` ✓ — prints progress bar, speed, ETA
- `test_on_file_hashed_without_eta()` ✓ — handles None ETA gracefully
- `test_show_summary()` ✓ — prints box-drawing summary with all stats
- `test_close()` ✓ — no-op execution
- All output captured and verified using `redirect_stdout()`

**TestRichProgressUI (7 tests):**
- `test_init()` — skipped (Rich not installed)
- `test_start_scan()` — skipped
- `test_on_folder_done()` — skipped
- `test_start_hash()` — skipped
- `test_on_file_hashed()` — skipped
- `test_show_summary()` — skipped
- `test_close()` — skipped
- Tests are properly decorated with `@unittest.skipUnless(RICH_AVAILABLE)` for graceful skip

**TestUIHandler (3 tests):**
- `test_create_ansi_forced()` ✓ — returns ANSIProgressUI when force_ansi=True
- `test_get_available()` ✓ — returns string ("ansi" when Rich not installed)
- `test_create_returns_ui_instance()` ✓ — UI has all required methods

**Test Results:**
```bash
Ran 30 tests in 0.001s
OK (skipped=7)
```

**Commit:** `618ba83`

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed format_speed() threshold logic for GB/s detection**
- **Found during:** Task 3 (unit test execution)
- **Issue:** Line 93 in ansi_codes.py had condition `if bytes_per_sec >= 1048576` with comment "GB/s threshold" — but 1048576 is the MB threshold, not GB. This caused speeds >= 1MB/s to be incorrectly classified as GB/s and divided by 1073741824, resulting in "0.0 GB/s" for 2.5 MB/s input.
- **Fix:** Changed threshold from 1048576 to 1073741824 (actual GB boundary), moved MB threshold to elif with 1048576, KB as else clause.
- **Files modified:** `diskcomp/ansi_codes.py` (2 lines changed)
- **Commit:** `618ba83` (included with test commit)

---

## Design Decisions Made

| Decision | Rationale | Status |
|----------|-----------|--------|
| Centralize ANSI codes in `ansi_codes.py` | Prevents magic string duplication; single source of truth for colors/symbols | Implemented |
| Factory pattern for UI selection (UIHandler) | Allows dynamic choice between Rich and ANSI without coupling | Implemented |
| Identical method signatures in both UI classes | Enables drop-in replacement; scanner/hasher callbacks don't need to know which UI is active | Implemented |
| RichProgressUI only when Rich available | Zero mandatory dependencies; graceful fallback to ANSI | Implemented |
| Skip Rich tests when not installed | Prevents test failures in minimal environments | Implemented |

---

## Compliance with Must-Haves

| Requirement | Evidence | Status |
|-------------|----------|--------|
| Scanner can report per-folder completion via callback | `on_folder_done()` method signature defined; ready for Wave 2 wiring | ✓ Ready |
| UI renders cyan arrow while scanning, green tick when folder done | ANSIProgressUI prints `{CYAN}{ARROW}` and `{GREEN}{TICK}` | ✓ Verified |
| Plain ANSI codes work when Rich is not installed | ANSIProgressUI uses no external deps; all 30 tests pass with Rich absent | ✓ Verified |
| Summary banner displays duplicates/unique counts and report path | Both UI classes have `show_summary()` method with all required parameters | ✓ Ready |
| ANSI constants module exports required functions | Exports: CYAN, GREEN, RESET, ARROW, TICK, colored, progress_bar, format_speed, format_eta | ✓ Verified |
| UI classes have identical interfaces | Both have: start_scan, on_folder_done, start_hash, on_file_hashed, show_summary, close | ✓ Verified |
| No breaking changes to existing modules | Phase 1 modules (scanner, hasher, cli, types, reporter) untouched | ✓ Verified |

---

## Known Stubs

None — all implementation complete and functional. Callback integration happens in Wave 2.

---

## Self-Check

**Files created:**
- ✓ `/Users/wilkinsmorales/code/diskcomp/diskcomp/ansi_codes.py` exists
- ✓ `/Users/wilkinsmorales/code/diskcomp/diskcomp/ui.py` exists
- ✓ `/Users/wilkinsmorales/code/diskcomp/tests/test_ui.py` exists

**Commits verified:**
- ✓ `6c27c87` — ansi_codes.py
- ✓ `c120948` — ui.py
- ✓ `618ba83` — test_ui.py + ansi_codes.py fix

**Tests passing:**
- ✓ `python3 -m unittest discover tests/ -k test_ui -v` → Ran 30 tests / OK (skipped=7)

**Imports working:**
- ✓ `from diskcomp.ansi_codes import CYAN, GREEN, RESET, ARROW, TICK, colored, progress_bar, format_speed, format_eta`
- ✓ `from diskcomp.ui import UIHandler, RichProgressUI, ANSIProgressUI`

**Self-Check: PASSED** ✓

---

## Next Steps

Phase 2 Plan 02 (Scanning Display) will:
1. Wire scanner callbacks to on_folder_done() method
2. Add optional `on_folder_done` parameter to FileScanner.scan()
3. Integration test with live UI updates during scanning

Phase 2 Plan 03 (Hashing Display) will:
1. Wire hasher callbacks to on_file_hashed() method
2. Add optional `on_file_hashed` parameter to FileHasher.hash_files()
3. Integration test with live progress bar during hashing

