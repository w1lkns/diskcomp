---
phase: 07-ux-polish-single-drive-mode
plan: 07
subsystem: CLI
tags: [post-scan-flow, deletion-workflow, user-experience]
completed_date: 2026-03-23
duration_minutes: 25
tasks_completed: 1
files_created: 0
files_modified: 2
commits: 1
commit_hash: 82e2ef2
key_files:
  created: []
  modified:
    - diskcomp/cli.py (show_action_menu function, main() integration)
    - tests/test_cli.py (10 new tests)
decisions: []
depends_on: [07-05, 07-06]
provides:
  - Post-scan action menu (D-23)
  - Conditional menu display (D-24)
  - Streamlined deletion workflow
---

# Phase 07 Plan 07: Post-Scan Action Menu Summary

Post-scan action menu implementation enabling users to delete immediately after reviewing scan results, without exiting and re-running CLI.

## One-liner

Post-scan action menu (interactive/batch/exit) with conditional display only when duplicates found, integrated into both two-drive and single-drive modes.

## What Was Built

### 1. `show_action_menu()` Function (D-23)

- Displays readable menu with 3 options:
  1. Review and delete interactively (per-file confirmation)
  2. Batch delete (dry-run preview + type DELETE confirmation)
  3. Exit (report saved, no deletion)
- Input validation: accepts 1-3, retries on invalid
- Returns: 'interactive', 'batch', or 'exit'

### 2. Main Flow Integration

**Two-drive mode flow:**
- After `show_plain_language_summary()` and `show_next_steps()`
- Conditional: only shown if `summary['duplicate_count'] > 0` (D-24)
- Routes to `DeletionOrchestrator` via `ReportReader.load()`
- Action 1: calls `orchestrator.interactive_mode()`
- Action 2: calls `orchestrator.batch_mode()`
- Action 3: exits cleanly with no deletion

**Single-drive mode flow:**
- Same post-scan placement and conditional logic
- Identical menu and routing behavior

### 3. Test Coverage

**Unit tests (6):**
- test_show_action_menu_option_1: returns 'interactive'
- test_show_action_menu_option_2: returns 'batch'
- test_show_action_menu_option_3: returns 'exit'
- test_show_action_menu_invalid_then_valid: retries on invalid input
- test_show_action_menu_whitespace_stripped: handles input whitespace
- test_show_action_menu_displays_menu: menu text displays correctly

**Integration tests (4):**
- test_main_action_menu_interactive: 2-drive mode, action 1 path
- test_main_action_menu_batch: 2-drive mode, action 2 path
- test_main_action_menu_exit: 2-drive mode, action 3 path (no deletion)
- test_main_no_action_menu_zero_duplicates: D-24 validation (menu skipped)

**Regression testing:**
- All 64 existing tests pass (no regressions)

## Design Decisions

1. **Conditional display (D-24):** Menu only shown if `duplicate_count > 0`. Avoids unnecessary prompt when there's nothing to delete.

2. **Early local imports:** `ReportReader` and `DeletionOrchestrator` imported within the action menu block (not at module top) to maintain minimal coupling and reduce import overhead for other code paths.

3. **Consistent output:** Uses `file=sys.stderr` for deletion results to align with existing error/status output patterns.

4. **No exit code change on action 3:** Exit path returns 0 (success) same as action 1/2, consistent with the philosophy that finding/reporting duplicates is the core success metric.

## What Wasn't Changed

- `DeletionOrchestrator` interface: reused as-is (no modifications needed)
- `ReportReader` interface: reused as-is (load() method sufficient)
- Existing deletion workflows: untouched (interactive/batch modes unchanged)
- Health checks, scanning, hashing, classification: all unchanged

## Deviations from Plan

None. Plan executed exactly as written.

- Function signature matches spec
- Menu display matches D-23 requirements
- Integration placement correct (post-summary, post-next-steps)
- Conditional logic correct (D-24)
- Both two-drive and single-drive modes covered
- Test coverage meets or exceeds spec

## Known Stubs

None. No empty values, placeholders, or incomplete wiring.

## Test Results

```
============================== 64 passed in 0.11s ===============================
```

All action-menu-specific tests:
- test_show_action_menu_option_1: PASSED
- test_show_action_menu_option_2: PASSED
- test_show_action_menu_option_3: PASSED
- test_show_action_menu_invalid_then_valid: PASSED
- test_show_action_menu_whitespace_stripped: PASSED
- test_show_action_menu_displays_menu: PASSED
- test_main_action_menu_interactive: PASSED
- test_main_action_menu_batch: PASSED
- test_main_action_menu_exit: PASSED
- test_main_no_action_menu_zero_duplicates: PASSED

## Files Modified

### diskcomp/cli.py
- Added `show_action_menu()` function (30 lines)
- Integrated into two-drive main() flow (33 lines)
- Integrated into single-drive main() flow (33 lines)

### tests/test_cli.py
- Added TestActionMenu class with 6 unit tests
- Added TestActionMenuIntegration class with 4 integration tests
- Updated imports to include `show_action_menu`

## Commit Info

**Hash:** 82e2ef2
**Message:** feat(07-07): add post-scan action menu

## What's Next

Plan 07-08 (if it exists) will likely focus on additional UX polish or edge-case handling. The action menu provides a solid foundation for immediate post-scan deletion without requiring a separate CLI invocation.

