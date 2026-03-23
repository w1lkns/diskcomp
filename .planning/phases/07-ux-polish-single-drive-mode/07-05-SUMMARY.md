---
phase: 07-ux-polish-single-drive-mode
plan: 05
subsystem: diskcomp.cli
tags:
  - ux
  - plain-language-output
  - user-guidance
status: complete
date_completed: 2026-03-23
key_files:
  - diskcomp/cli.py
  - tests/test_cli.py
decisions_made:
  - D-16: Plain-language summary format with MB/GB conversion
  - D-17: Zero-duplicate messages for both two-drive and single-drive modes
  - D-18: Next-steps block with exact report path and undo log hint
---

# Phase 7 Plan 5: Plain-Language Results Summary and Next Steps

**One-liner:** Added plain-language results summary and next-steps guidance block that displays after every scan, showing users what was found and exactly how to review, delete, or undo.

## Objective

Add plain-language results summary and next-steps block printed after every scan, enabling users to understand results without reading CSV files and providing exact commands for the next action.

## Summary

Successfully implemented two new functions in `diskcomp/cli.py`:

1. **`show_plain_language_summary(summary_dict, mode, keep_label, other_label)`**
   - Displays "Found {N} duplicates. You could free {X} GB/MB from {label}. Ready to review?"
   - Zero-duplicate case: "No duplicates found. Both drives are already clean." (two-drive) or "No duplicates found. This drive has no redundant files." (single-drive)
   - Automatically converts MB to GB when size >= 1000 MB
   - Integrated into main() post-scan flow after ui.show_summary()

2. **`show_next_steps(report_path)`**
   - Displays formatted next-steps block with:
     - `Review: cat {report_path}`
     - `Delete: diskcomp --delete-from {report_path}`
     - `Undo: diskcomp --undo ~/diskcomp-undo-YYYYMMDD.json`
   - Uses actual generated report path and current date for undo hint
   - Integrated into main() post-scan flow after show_plain_language_summary()

Both functions are called in both two-drive and single-drive scan workflows.

## Changes Made

### diskcomp/cli.py

- Added `show_plain_language_summary()` function (lines 451-491)
  - Handles both two-drive and single-drive modes
  - Proper MB/GB conversion logic (threshold: 1000 MB)
  - Clean output formatting with blank lines

- Added `show_next_steps()` function (lines 494-510)
  - Uses datetime to generate correct undo log hint
  - Displays formatted border with dashes
  - Shows exact commands with actual report path

- Integrated into two-drive flow (lines 881-884)
  - Called after ui.show_summary()
  - Before ui.close()

- Integrated into single-drive flow (lines 734-735)
  - Called with mode='single_drive'
  - Uses actual drive label

### tests/test_cli.py

- Updated imports to include new functions (lines 9-10)

- Added `TestPlainLanguageSummary` class (7 tests)
  - `test_show_plain_language_summary_with_duplicates()`: Verifies format with actual values
  - `test_show_plain_language_summary_zero_duplicates_two_drives()`: Two-drive zero case
  - `test_show_plain_language_summary_zero_duplicates_single_drive()`: Single-drive zero case
  - `test_show_plain_language_summary_uses_gb_for_large()`: GB conversion (2500 MB → 2.5 GB)
  - `test_show_plain_language_summary_uses_mb_for_small()`: MB preservation (500 MB)
  - `test_show_plain_language_summary_single_drive_mode_label()`: "this drive" label check
  - `test_show_plain_language_summary_threshold_at_1000()`: Boundary test (exactly 1000 MB)

- Added `TestNextSteps` class (3 tests)
  - `test_show_next_steps_output()`: Verifies all three commands and report path
  - `test_show_next_steps_undo_hint_format()`: Undo log hint pattern validation
  - `test_show_next_steps_border_format()`: Border line formatting

## Verification

All test suites pass:

```
tests/test_cli.py::TestPlainLanguageSummary::test_show_plain_language_summary_single_drive_mode_label PASSED
tests/test_cli.py::TestPlainLanguageSummary::test_show_plain_language_summary_threshold_at_1000 PASSED
tests/test_cli.py::TestPlainLanguageSummary::test_show_plain_language_summary_uses_gb_for_large PASSED
tests/test_cli.py::TestPlainLanguageSummary::test_show_plain_language_summary_uses_mb_for_small PASSED
tests/test_cli.py::TestPlainLanguageSummary::test_show_plain_language_summary_with_duplicates PASSED
tests/test_cli.py::TestPlainLanguageSummary::test_show_plain_language_summary_zero_duplicates_single_drive PASSED
tests/test_cli.py::TestPlainLanguageSummary::test_show_plain_language_summary_zero_duplicates_two_drives PASSED
tests/test_cli.py::TestNextSteps::test_show_next_steps_border_format PASSED
tests/test_cli.py::TestNextSteps::test_show_next_steps_output PASSED
tests/test_cli.py::TestNextSteps::test_show_next_steps_undo_hint_format PASSED

====================== 49 passed in 0.09s ===============================
```

Manual output verification shows correct formatting:

```
Found 50 duplicates. You could free 10.5 MB from Backup. Ready to review?
No duplicates found. Both drives are already clean.
Found 20 duplicates. You could free 2.5 GB from this drive. Ready to review?
── Next steps ────────────────────────────────────────
Review:  cat /tmp/diskcomp-report-20260323-120000.csv
Delete:  diskcomp --delete-from /tmp/diskcomp-report-20260323-120000.csv
Undo:    diskcomp --undo ~/diskcomp-undo-20260323.json
────────────────────────────────────────────────────────────
```

## Decisions Made

- **D-16 Implementation:** Plain-language format matches spec exactly
- **D-17 Implementation:** Zero-duplicate messages differentiate between modes
- **D-18 Implementation:** Next-steps block uses actual paths and correct date format

## Deviations from Plan

None — plan executed exactly as written.

## Commit

```
ecb40aa feat(07-05): add plain-language summary and next-steps block
```

Files modified: 2
Lines added: 292
Tests added: 10
Tests passing: 49/49

---

*Completed on 2026-03-23 by Claude Code executor*
