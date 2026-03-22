---
phase: 01-core-engine-report
plan: 02
subsystem: Core Engine — Hashing & Reporting
tags: [hashing, deduplication, reporting, atomic-writes]
dependency_graph:
  requires: [01-01]
  provides: [duplicate-classification, csv-reporting, json-reporting]
  affects: [02-cli, 03-deletion]
tech_stack:
  patterns: [chunked-reading, atomic-writes, dataclass-contracts]
  added:
    - hashlib (stdlib)
    - csv (stdlib)
    - json (stdlib)
    - tempfile (stdlib)
    - datetime (stdlib)
key_files:
  created:
    - diskcomp/hasher.py
    - diskcomp/reporter.py
decisions:
  - "FileHasher uses 8KB chunks (balance between memory and I/O efficiency)"
  - "Atomic writes via temp file → rename pattern (crash-safe on most filesystems)"
  - "SHA256 used for cryptographic collision resistance (no false positives)"
  - "Size converted to MB in reports for readability"
metrics:
  duration: "~15 minutes"
  tasks_completed: 2
  files_created: 2
  lines_of_code: 432
  test_coverage: "100% of acceptance criteria"
---

# Phase 01 Plan 02: Hashing & Reporting Summary

**Build SHA256 hashing engine and CSV/JSON report writer for deduplication.**

## One-liner

FileHasher uses chunked reading to efficiently compute SHA256 hashes for large files; DuplicateClassifier identifies byte-for-byte duplicates across two drives and outputs CSV/JSON reports with atomic writes for crash safety.

## Objective

Complete CORE-03, CORE-04, and RPT-01 through RPT-05 requirements: hash files to identify byte-for-byte duplicates, classify files as DUPLICATE/UNIQUE, and generate timestamped CSV/JSON reports with atomic writes.

## Completed Tasks

| Task | Name | Commit | Status |
|------|------|--------|--------|
| 1 | Create SHA256 hashing module (hasher.py) | e51f974 | Complete |
| 2 | Create reporter module with classification and reporting (reporter.py) | ffcafb1 | Complete |

## Task Details

### Task 1: FileHasher (hasher.py)

**What was built:** SHA256 hashing engine with chunked reading for memory efficiency.

**FileHasher class features:**
- `__init__(chunk_size=8192)` — Initialize with configurable chunk size (default 8KB)
- `hash_file(file_path)` — Compute SHA256 hash of a file, returns 64-char lowercase hex string
- `hash_file_record(record)` — Hash a FileRecord and return updated copy with hash or error

**Error handling:**
- Catches PermissionError → raises FileNotReadableError "Permission denied"
- Catches OSError → raises FileNotReadableError "Cannot read file"
- Catches IOError → raises FileNotReadableError "IO error"

**Example usage:**
```python
from diskcomp.hasher import FileHasher

hasher = FileHasher(chunk_size=8192)
hash_value = hasher.hash_file("/path/to/file.txt")
# Returns: "6ae8a75555209fd6c44157c0aed8016e763ff435a19cf186f76863140143ff72"

# Or with FileRecord:
record = FileRecord(path="/path/to/file.txt", rel_path="file.txt", size_bytes=1024)
updated = hasher.hash_file_record(record)
# Returns FileRecord with hash field populated or error field set
```

**Key design decisions:**
- Chunked reading (8KB default) prevents memory exhaustion on multi-GB files
- Streaming computation via hashlib.sha256() is more efficient than hashing entire file at once
- Returns lowercase hex digest (standard format)

### Task 2: DuplicateClassifier & ReportWriter (reporter.py)

**What was built:** Duplicate classification engine and atomic report writer.

#### DuplicateClassifier

**Features:**
- `__init__(keep_result, other_result)` — Initialize with two ScanResult objects
- `classify()` — Returns classification dict with duplicates, unique files, and summary statistics

**Classification logic:**
1. Build hash → file mappings for both drives
2. For each file in other drive:
   - If hash exists in keep: mark as DUPLICATE (action='DELETE_FROM_OTHER')
   - Else: mark as UNIQUE_IN_OTHER
3. For each file in keep drive not found in other: mark as UNIQUE_IN_KEEP

**Output structure:**
```json
{
  "duplicates": [
    {
      "action": "DELETE_FROM_OTHER",
      "keep_path": "/Volumes/Keep/file.txt",
      "other_path": "/Volumes/Other/file.txt",
      "size_mb": 1.5,
      "hash": "abc123..."
    }
  ],
  "unique_in_keep": [...],
  "unique_in_other": [...],
  "summary": {
    "duplicate_count": 42,
    "duplicate_size_mb": 256.78,
    "unique_in_keep_count": 15,
    "unique_in_keep_size_mb": 8.5,
    "unique_in_other_count": 22,
    "unique_in_other_size_mb": 64.2
  }
}
```

#### ReportWriter

**Features:**
- `__init__(output_dir=None, output_path=None)` — Initialize with output directory or exact path
  - If output_path provided: use as-is
  - If output_dir provided: generate timestamped filename
  - Default: use home directory (~)
- `write_csv(classification, path=None)` — Write CSV report atomically
- `write_json(classification, path=None)` — Write JSON report atomically

**CSV columns:**
```
action,keep_path,other_path,size_mb,hash
DELETE_FROM_OTHER,/Volumes/Keep/file.txt,/Volumes/Other/file.txt,1.5,abc123...
UNIQUE_IN_KEEP,/Volumes/Keep/unique.txt,,0.25,def456...
UNIQUE_IN_OTHER,,/Volumes/Other/unique.txt,2.0,ghi789...
```

**Atomic write pattern:**
```python
# 1. Write to temp file: {path}.tmp
# 2. On success: os.rename({path}.tmp, {path}) — atomic on most OSes
# 3. On error: clean up temp file
```

This prevents partial writes if the process crashes mid-write.

**Example usage:**
```python
from diskcomp.reporter import DuplicateClassifier, ReportWriter

classifier = DuplicateClassifier(keep_result, other_result)
classification = classifier.classify()

writer = ReportWriter(output_dir="/tmp")
writer.write_csv(classification)  # Writes diskcomp-report-20260322-132812.csv
writer.write_json(classification)  # Writes diskcomp-report-20260322-132812.json
```

## Verification Results

All acceptance criteria passed:

✅ **hasher.py**
- FileHasher class exists with __init__(chunk_size=8192)
- hash_file() returns 64-character lowercase hex string (SHA256 digest)
- hash_file() raises FileNotReadableError on PermissionError, OSError, IOError
- hash_file_record() accepts FileRecord, updates hash, catches errors and sets error field
- Uses chunked reading (default 8KB chunks)
- Produces consistent results (same file = same hash every time)
- Tested with various file sizes and error conditions

✅ **reporter.py**
- DuplicateClassifier and ReportWriter classes exist
- DuplicateClassifier correctly identifies duplicates by hash
- Files classified as DUPLICATE, UNIQUE_IN_KEEP, UNIQUE_IN_OTHER
- ReportWriter generates timestamped filenames: diskcomp-report-YYYYMMDD-HHMMSS.{csv,json}
- CSV has correct columns: action, keep_path, other_path, size_mb, hash
- JSON format matches classification dict structure
- Both write methods use atomic temp → rename pattern
- Summary statistics correctly computed (counts and totals)
- Size conversion to MB works correctly (bytes / 1048576)

✅ **Integration**
- Scanner → Hasher pipeline works end-to-end
- FileRecord objects successfully flow through hasher and classifier
- Reports generated correctly from classification dicts
- All imports work without circular dependencies

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — both modules are complete and production-ready.

## Files Modified

- `diskcomp/hasher.py` — created (105 lines)
- `diskcomp/reporter.py` — created (327 lines)

## Requirements Fulfilled

- [x] CORE-03: Files hashed using SHA256, byte-for-byte duplicates identified
- [x] CORE-04: Files classified as DUPLICATE or UNIQUE
- [x] RPT-01: CSV reports with action, keep_path, other_path, size_mb, hash
- [x] RPT-02: JSON reports with same structure
- [x] RPT-03: Report filenames timestamped (YYYYMMDD-HHMMSS)
- [x] RPT-04: Custom output path supported (via output_path parameter)
- [x] RPT-05: Reports written atomically (temp → rename)

## Next Steps

Plan 03 will integrate these modules into a CLI interface, adding:
- `diskcomp/cli.py` — command-line interface with argparse
- Usage: `diskcomp /path/to/keep /path/to/other --output report.csv`
- Optional: `--json` flag for JSON output, `--output` for custom path
