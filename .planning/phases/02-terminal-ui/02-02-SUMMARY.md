---
phase: 02-terminal-ui
plan: 02
subsystem: scanning-display
tags: [callbacks, integration, ui-wiring, progress-tracking]
dependencies:
  requires: [02-01]
  provides: [callback-architecture, live-progress-foundation]
  affects: [CLI, Scanner, Hasher]
tech_stack:
  added: [time module for speed/ETA calculations]
  patterns: [callback-based architecture, factory pattern for UI]
key_files:
  created: [tests/test_ui_integration.py]
  modified: [diskcomp/scanner.py, diskcomp/hasher.py, diskcomp/cli.py]
decisions:
  - "Callback-based architecture keeps business logic independent from UI presentation"
  - "Speed/ETA calculated in hash_files() rather than UI layer (responsibility separation)"
  - "UI methods routed through factory (UIHandler) for Rich/ANSI switching"
  - "All files hashed together in one batch for unified progress tracking"
metrics:
  duration: ~15 minutes
  tasks_completed: 4/4
  test_coverage: 68 tests passing (7 skipped), 17 new integration tests
  files_created: 1
  files_modified: 3
  commits: 4
---

# Phase 02 Plan 02: Scanning Display Summary

**Objective:** Wire callback hooks into scanner and hasher, integrate with UI in CLI for live progress tracking.

**Result:** Complete callback architecture implemented, all integration tests passing, CLI now displays live progress with speed and ETA calculations during scanning and hashing.

## Execution Summary

### Task 1: Add on_folder_done callback to scanner.py ✓
- **Status:** Complete
- **Changes:**
  - Added `on_folder_done` parameter to `FileScanner.scan()` method signature
  - Parameter type: `Optional[Callable[[str, int], None]]` (folder_path, file_count)
  - Callback invoked after processing each folder's files when provided
  - Callback only called when `folder_files > 0` (no empty folders)
  - Updated docstring to document new parameter
  - Maintains backward compatibility: parameter defaults to None

- **Verification:**
  - Grep confirmed callback parameter present and invoked
  - Integration tests verify callback called with correct folder paths and counts
  - Backward compatibility test passes (scan without callback still works)

- **Commit:** `b8e082d` - feat(02-02): add on_folder_done callback to FileScanner.scan()

### Task 2: Add on_file_hashed callback to hasher.py ✓
- **Status:** Complete
- **Changes:**
  - New `hash_files()` method added for batch processing with callback
  - Signature: `hash_files(records: List[FileRecord], on_file_hashed: Optional[Callable[[int, int, float, int], None]])`
  - Callback parameters: (current_index [1-based], total, speed_mbps, eta_secs)
  - Speed calculation: `(total_bytes_hashed / elapsed_time) / (1024 * 1024)` → MB/s
  - ETA calculation: `remaining_bytes / bytes_per_sec` → seconds
  - Uses existing `hash_file_record()` for individual file processing
  - Handles per-file errors without breaking loop
  - Imported `time`, `Callable`, `List`, `Optional` from typing

- **Verification:**
  - Method exists and callable
  - Callback invoked 5 times for 5 files
  - Speed calculated as positive float
  - ETA calculated as non-negative integer
  - Index sequence correct (1-5)
  - Backward compatibility test passes (hash without callback)

- **Commit:** `117ce9c` - feat(02-02): add hash_files() method with progress callback

### Task 3: Integrate UI callbacks into cli.py ✓
- **Status:** Complete
- **Changes:**
  - Added `from diskcomp.ui import UIHandler` import
  - Instantiate UI at start of `main()` via `UIHandler.create()`
  - Pass `on_folder_done` lambda callback to both scanner.scan() calls
  - Call `ui.start_scan(path)` before each scan operation
  - Combined all files from both scans before hashing
  - Use `hasher.hash_files()` with `on_file_hashed` callback instead of list comprehension
  - Split hashed records back to keep/other after hashing
  - Use `ui.show_summary()` for final results display
  - Call `ui.close()` in success path and all exception handlers
  - Route warning/classification messages to stderr for clean output

- **Verification:**
  - UIHandler import confirmed
  - CLI UI methods called in correct sequence
  - Mock UI tests verify:
    - `start_scan()` called 2× (keep + other)
    - `on_folder_done()` called during scanning
    - `start_hash()` called before hashing
    - `on_file_hashed()` called per file
    - `show_summary()` called with correct statistics
    - `close()` called at end

- **Commit:** `56e61ac` - feat(02-02): integrate UI callbacks into CLI scanner/hasher

### Task 4: Create integration tests for scanner/hasher callbacks and CLI UI flow ✓
- **Status:** Complete
- **Test Classes:**

  **TestScannerCallback (5 tests):**
  - `test_scanner_calls_folder_callback()` - Callback invoked with correct data
  - `test_scanner_callback_multiple_folders()` - Callback called per folder
  - `test_scanner_no_callback()` - Backward compatibility (no callback)
  - `test_scanner_callback_receives_correct_counts()` - File counts accurate
  - All passing ✓

  **TestHasherCallback (6 tests):**
  - `test_hasher_hash_files_method_exists()` - Method callable
  - `test_hasher_calls_file_callback()` - Callback invoked per file
  - `test_hasher_callback_speed_calculation()` - Speed positive/reasonable
  - `test_hasher_callback_eta_calculation()` - ETA non-negative integer
  - `test_hasher_callback_index_sequence()` - Indices sequential (1..N)
  - `test_hasher_no_callback()` - Backward compatibility (no callback)
  - All passing ✓

  **TestCLIUI (6 tests):**
  - `test_cli_ui_handler_created()` - UIHandler returns valid UI instance
  - `test_cli_ui_start_scan_called()` - start_scan() called 2× during scanning
  - `test_cli_ui_on_folder_done_called()` - on_folder_done() called during scan
  - `test_cli_ui_start_hash_called()` - start_hash() called before hashing
  - `test_cli_ui_on_file_hashed_called()` - on_file_hashed() called per file
  - `test_cli_ui_show_summary_called()` - show_summary() called with correct args
  - `test_cli_ui_close_called()` - close() called at end
  - All passing ✓

- **Test Coverage:**
  - Created 17 new integration tests
  - Full suite: 68 tests passing, 7 skipped (Rich unavailable)
  - No regressions in Phase 1 tests

- **Commit:** `8765a39` - test(02-02): add comprehensive integration tests for callbacks

## Deviations from Plan

None. Plan executed exactly as written.

## Success Criteria Met

- [x] Scanner.scan() accepts on_folder_done callback parameter
- [x] Callback invoked with (folder_path, file_count) after each folder
- [x] FileHasher.hash_files() method created with on_file_hashed callback
- [x] Callback parameters: (current_index, total, speed_mbps, eta_secs)
- [x] Speed calculated in MB/s (bytes / elapsed_time / 1024 / 1024)
- [x] ETA calculated in seconds (remaining_bytes / current_speed)
- [x] CLI instantiates UIHandler and passes callbacks
- [x] UI methods called: start_scan, on_folder_done, start_hash, on_file_hashed, show_summary, close
- [x] Integration tests created and passing (17 new tests)
- [x] Full test suite passing (68 tests, 7 skipped)
- [x] Backward compatibility maintained (code without callbacks still works)
- [x] No breaking changes to CLI interface

## Next Steps

Phase 2 Plan 03 (Drive Health & Pre-scan) will:
- Add SMART data collection and filesystem detection
- Add drive space summary display
- Add pre-scan confirmation workflow
- Integrate with UI for drive health visualization

## Self-Check: PASSED

All files exist:
- ✓ diskcomp/scanner.py (modified)
- ✓ diskcomp/hasher.py (modified)
- ✓ diskcomp/cli.py (modified)
- ✓ tests/test_ui_integration.py (created)

All commits exist:
- ✓ b8e082d - feat(02-02): add on_folder_done callback to FileScanner.scan()
- ✓ 117ce9c - feat(02-02): add hash_files() method with progress callback
- ✓ 56e61ac - feat(02-02): integrate UI callbacks into CLI scanner/hasher
- ✓ 8765a39 - test(02-02): add comprehensive integration tests for callbacks

All tests pass:
- ✓ python3 -m unittest discover tests/ -v → 68 OK (7 skipped)
