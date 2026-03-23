---
phase: 07-ux-polish-single-drive-mode
plan: 06
completed: 2026-03-23T12:40:00Z
status: complete
subsystem: single-drive-dedup-mode
tags: [implementation, feature-complete, tested]
dependency_graph:
  requires: [07-04, 07-05]
  provides: [07-07, 07-08, 07-09]
  affects: [deletion-workflow, report-generation]
tech_stack:
  added: [group_by_hash_single_drive, group_by_size_single_drive, --single flag]
  patterns: [D-01-keep-rule, D-03-size-filtering, D-23-action-menu]
key_files:
  created: []
  modified:
    - diskcomp/cli.py (+73 lines, single-drive branch)
    - diskcomp/hasher.py (+65 lines, two grouping functions)
    - tests/test_cli.py (+56 lines, 5 integration tests)
    - tests/test_hasher.py (+105 lines, 9 unit tests)
decisions:
  - Removed ui.update_status() call in single-drive branch (method doesn't exist on UIHandler)
  - Converted single_drive_result dict to classification dict with proper structure for ReportWriter
  - Reused DuplicateClassifier structure (duplicates/unique_in_keep/unique_in_other/summary) for consistency
metrics:
  duration_minutes: 35
  completed_date: 2026-03-23
  test_coverage: 73 tests pass (19 new for single-drive)
  files_modified: 4
---

# Phase 7 Plan 6: Single-Drive Dedup Mode Summary

Single-drive duplicate detection with --single flag, keeping alphabetically first path per hash group.

## Overview

Implemented single-drive mode that scans one drive for internal duplicates and feeds results into existing deletion workflow. Users can now clean up their own full drive without needing a second drive while maintaining same safe deletion and undo guarantees.

## What Was Built

### 1. CLI Flag and Routing (diskcomp/cli.py)

- **--single flag** in parse_args() accepts a directory path
- **Single-drive branch** in main() handles complete pipeline:
  - Validates path is a directory
  - Scans files with min-size filtering
  - Applies two-pass optimization (size filtering first)
  - Hashes only size-collision candidates
  - Groups by hash to identify duplicates
  - Generates CSV/JSON report
  - Displays plain-language summary and next steps
  - Returns proper exit code on success/error

### 2. Hash Grouping Functions (diskcomp/hasher.py)

**group_by_hash_single_drive(records)** → dict
- Groups all hashed FileRecords by SHA256 hash
- For each hash with 2+ copies:
  - Sorts records alphabetically by path
  - Keeps first path (alphabetically earliest)
  - Marks all others as DELETE_FROM_OTHER
- For each hash with 1 copy:
  - Marks as UNIQUE_IN_OTHER
- Returns dict with:
  - `duplicates`: list of {action, keep_path, other_path, size_mb, hash}
  - `unique`: list of {action, keep_path=None, other_path, size_mb, hash}
  - `summary`: {duplicate_count, duplicate_size_mb, unique_in_other_count, unique_in_other_size_mb}

**group_by_size_single_drive(records)** → (candidates, stats)
- Two-pass optimization (D-03): skip sizes appearing only once
- Counts occurrences of each file size
- Filters to only files whose size appears 2+ times
- Returns candidates list and stats dict with:
  - `total_scanned`: original file count
  - `candidate_count`: files with size collisions
  - `pct_skipped`: percentage of files skipped (0-100)

### 3. Integration with Existing Systems

- Classification dict converted to standard format compatible with ReportWriter.write_csv() and write_json()
- Results feed into DeletionOrchestrator (same undo log, same deletion modes)
- Plain-language summary uses single-drive-specific wording
- Next steps match two-drive workflow

### 4. Test Coverage

**Unit Tests (tests/test_hasher.py):**
- test_group_by_hash_single_drive_no_duplicates: All unique hashes
- test_group_by_hash_single_drive_with_duplicates: 3 copies, 1 kept
- test_group_by_hash_single_drive_keeps_alphabetically_first: Verify alphabetical sorting
- test_group_by_hash_single_drive_mixed: Mix of duplicates and unique
- test_group_by_hash_single_drive_sizes: Verify size_mb calculation
- test_group_by_size_single_drive_filters_singletons: Skip non-duplicatable sizes
- test_group_by_size_single_drive_no_duplicates: All unique sizes
- test_group_by_size_single_drive_all_same_size: All files same size
- test_group_by_size_single_drive_empty: Empty input handling

**Integration Tests (tests/test_cli.py):**
- test_parse_args_single_flag: Flag parsing
- test_parse_args_single_with_min_size: Combined with --min-size
- test_parse_args_single_with_format_json: Combined with --format
- test_main_single_drive_flag: Full workflow execution
- test_main_single_drive_invalid_path: Error handling for invalid paths

**Test Results:**
- All 73 tests pass (64 existing + 9 new)
- No regressions in two-drive mode
- Manual verification successful: `python3 -m diskcomp --single /tmp/test_diskcomp_single --min-size 1b --format json` correctly identifies duplicates and creates report

## Key Implementation Details

### Keep Rule (D-01)
Alphabetically first path in each hash group is retained:
```python
sorted_records = sorted(records_in_group, key=lambda r: r.path)
keep_rec = sorted_records[0]
```

### Two-Pass Optimization (D-03)
Size filtering before hashing saves time for large directories:
```python
candidates, size_stats = group_by_size_single_drive(scan_result.files)
# Only hash files whose size appears 2+ times
hashed_records = hasher.hash_files(candidates, ...)
```

### Workflow Integration
Single-drive results converted to standard classification dict:
```python
classification = {
    'duplicates': single_drive_result['duplicates'],
    'unique_in_keep': [],
    'unique_in_other': single_drive_result['unique'],
    'summary': single_drive_result['summary'],
}
writer.write_csv(classification)
```

## Deviations from Plan

### Removed ui.update_status() Call (Rule 1 - Bug)
- **Found during:** Implementation testing
- **Issue:** UIHandler doesn't have update_status() method
- **Fix:** Removed line 695 that called non-existent method; hashing progress reported via on_file_hashed callback
- **Files modified:** diskcomp/cli.py line 695
- **Commit:** 5eb7ca3

## Files Created/Modified

- **diskcomp/cli.py**: Added --single flag (2 lines), single-drive branch (73 lines)
- **diskcomp/hasher.py**: Added group_by_hash_single_drive (65 lines), group_by_size_single_drive (31 lines)
- **tests/test_cli.py**: Added TestSingleDriveMode class with 5 integration tests (56 lines)
- **tests/test_hasher.py**: Added TestGroupByHashSingleDrive and TestGroupBySizeSingleDrive classes with 9 unit tests (105 lines)

## Verification

### Automated Tests
```bash
cd /Users/wilkinsmorales/code/diskcomp && python3 -m pytest tests/test_hasher.py tests/test_cli.py -xvs
# Result: 73 passed
```

### Manual Verification
```bash
mkdir -p /tmp/test_diskcomp_single
echo "content1" > /tmp/test_diskcomp_single/file1.txt
echo "content2" > /tmp/test_diskcomp_single/file2.txt
echo "content1" > /tmp/test_diskcomp_single/file3.txt  # duplicate of file1

python3 -m diskcomp --single /tmp/test_diskcomp_single --min-size 1b --format json
# Output: Found 1 duplicates with DELETE_FROM_OTHER action for file3
# Report generated and summary displayed correctly
```

## Known Stubs

None. All functionality complete and integrated.

## Self-Check: PASSED

- [x] diskcomp/cli.py modified (--single flag + single-drive branch)
- [x] diskcomp/hasher.py modified (group_by_hash_single_drive + group_by_size_single_drive)
- [x] tests/test_cli.py modified (5 integration tests)
- [x] tests/test_hasher.py modified (9 unit tests)
- [x] All 73 tests passing
- [x] Manual verification successful
- [x] Commit hash 5eb7ca3 verified in git log
