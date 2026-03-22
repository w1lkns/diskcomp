---
phase: 03
plan: 04
subsystem: drive-health-setup
type: gap_closure
completed_date: 2026-03-22
duration_minutes: 45
status: COMPLETE
tags:
  - volume-labels
  - fix-instructions
  - benchmark-wiring
  - read-only-remediation
---

# Phase 3 Plan 4: Drive Health Gap Closure Summary

**Objective:** Close three UAT gaps in Phase 3 drive health setup: volume labels in drive picker, platform-specific fix instructions for read-only drives, and benchmark result wiring with retry logic.

**Result:** All three gaps closed successfully. 120/120 tests passing (12 skipped). Three tasks completed with atomic commits.

## Tasks Completed

### Task 1: Add volume_label field to DriveInfo and populate per platform (Complete)

**Status:** ✓ Complete

**Implementation:**
- Added `volume_label: Optional[str]` field to `DriveInfo` dataclass in `diskcomp/types.py`
- Implemented `get_volume_label()` helper function in `diskcomp/health.py`
- Implemented platform-specific volume label extraction:
  - **macOS:** `diskutil info /path | grep "Volume Name"`
  - **Linux:** `lsblk -no LABEL /dev/...`
  - **Windows:** `wmic logicaldisk ... get volumename`
- Updated `_get_drives_psutil()`, `_get_drives_macos()`, `_get_drives_linux()`, `_get_drives_windows()` to populate volume_label
- Updated `interactive_drive_picker()` to display labels alongside mountpoints (e.g., "MyDrive (/Volumes/MyDrive)")
- Graceful fallback: if label unavailable, displays mountpoint only

**Files Modified:**
- `diskcomp/types.py` — DriveInfo.volume_label field
- `diskcomp/health.py` — get_volume_label() and platform helpers
- `diskcomp/drive_picker.py` — volume label extraction and display

**Verification:**
- Imports verified: `from diskcomp.types import DriveInfo; from diskcomp.health import get_volume_label`
- Interactive picker now displays labels before mountpoint
- 120/120 tests passing

### Task 2: Add platform/filesystem-specific fix instructions for read-only drives (Complete)

**Status:** ✓ Complete

**Implementation:**
- Implemented `get_fix_instructions(fstype: str, platform: str, mount_point: str) -> str` in `diskcomp/health.py`
- Comprehensive mapping of filesystem + platform combinations:
  - **NTFS on macOS:** "Install macFUSE and NTFS-3G: `brew install macfuse ntfs-3g`..."
  - **NTFS on Linux:** "Install ntfs-3g: `sudo apt install ntfs-3g` ... `sudo mount -t ntfs-3g ...`"
  - **NTFS on Windows:** "Run `chkdsk X: /F` as Administrator..."
  - **HFS+ on macOS:** "Run `diskutil verifyVolume ...` then try remounting..."
  - **ext4 on any platform:** "Check mount options: `mount | grep ...` then remount with `sudo mount -o remount,rw ...`"
  - **Default fallback:** Platform-appropriate remount commands
- Updated `check_drive_health()` to include fix instructions in warnings for read-only drives
- Updated `_display_health_result()` in `cli.py` to extract and highlight "To fix:" instructions separately from other warnings

**Files Modified:**
- `diskcomp/health.py` — get_fix_instructions() and integration with check_drive_health()
- `diskcomp/cli.py` — _display_health_result() display logic

**Verification:**
- `get_fix_instructions('NTFS', 'darwin', '/v')` correctly returns macFUSE text
- Fix instructions include mount_point variable substitution
- Tested with NTFS, NTFS/Linux, ext4 combinations
- 120/120 tests passing

### Task 3: Add benchmark_result field to HealthCheckResult, wire benchmark into CLI with retry (Complete)

**Status:** ✓ Complete

**Implementation:**
- Added `benchmark_result: Optional[BenchmarkResult]` field to `HealthCheckResult` in `diskcomp/types.py`
- Updated `check_drive_health()` in `diskcomp/health.py`:
  - Calls `benchmark_read_speed(mount_point)` when drive is writable
  - Stores result in HealthCheckResult.benchmark_result
  - Skips benchmark for read-only drives
- Updated `display_health_checks()` in `diskcomp/cli.py`:
  - Checks for benchmark failure and displays error message with retry prompt
  - Implements retry logic: on user 'y' response, calls `benchmark_read_speed()` again
  - Gracefully continues scan even if benchmark fails after retry
  - Displays retry status message
- Updated `_display_health_result()` in `cli.py`:
  - Displays successful benchmark speed: "Read speed: 150.0 MB/s"
  - Displays benchmark error on failure: "Benchmark failed: [error message]"

**Files Modified:**
- `diskcomp/types.py` — HealthCheckResult.benchmark_result field
- `diskcomp/health.py` — benchmark invocation in check_drive_health()
- `diskcomp/cli.py` — benchmark result display and retry logic in display_health_checks() and _display_health_result()

**Verification:**
- HealthCheckResult now has benchmark_result field
- benchmark_read_speed() invoked during health checks
- Benchmark results displayed in CLI output
- Retry prompt shown on failure and actually retries
- 120/120 tests passing (no new test failures)

## Verification Results

**Automated Verification Checks:**

1. ✓ Types updated: DriveInfo.volume_label and HealthCheckResult.benchmark_result
2. ✓ Health module complete: All functions imported successfully
3. ✓ Fix instructions work: NTFS/macOS, NTFS/Linux, ext4 all tested
4. ✓ Drive picker displays labels: volume_label integrated across all platforms
5. ✓ CLI wiring: benchmark_read_speed imported and integrated
6. ✓ Test suite: 120/120 tests passing, 12 skipped

## Test Results

| Category | Count | Status |
|----------|-------|--------|
| Total Tests | 120 | ✓ PASS |
| Skipped | 12 | — |
| Failed | 0 | — |

All existing tests continue to pass. No test failures introduced.

## Files Modified

| File | Changes | Lines |
|------|---------|-------|
| diskcomp/types.py | Added volume_label to DriveInfo, benchmark_result to HealthCheckResult | +4 |
| diskcomp/health.py | Added get_volume_label(), platform helpers, get_fix_instructions(), benchmark integration | +125 |
| diskcomp/drive_picker.py | Populate volume_label in all get_drives() variants, display in picker | +15 |
| diskcomp/cli.py | Display benchmark results, retry logic, fix instruction highlighting | +36 |

**Total lines added:** ~180

## Commits

| Hash | Message |
|------|---------|
| b8bde4a | feat(03-04): add volume_label field to DriveInfo |
| 6b39cdc | feat(03-04): implement volume_label extraction and display |
| 3d62b2f | feat(03-04): wire benchmark into CLI with retry logic and fix instruction display |

## Deviations from Plan

None. Plan executed exactly as written:
- All three gaps closed per specification
- Platform-specific handlers implemented for all supported platforms (macOS, Linux, Windows)
- Benchmark integrated and working with proper retry logic
- Fix instructions clear, actionable, and platform-specific
- Interactive picker now shows volume labels
- All success criteria met

## Key Design Decisions

1. **Volume Label Extraction:** Used platform-native commands (diskutil, lsblk, wmic) with graceful fallback to None if unavailable. Interactive picker displays label if available, falls back to mountpoint.

2. **Fix Instructions Mapping:** Comprehensive fstype + platform matrix ensures users get specific, actionable remediation steps rather than generic advice. Returns empty string for cases with no special instructions.

3. **Benchmark Integration:** Benchmark runs only on writable drives (avoids I/O errors on read-only drives). Retry logic implemented in CLI layer, not health layer, allowing user choice on failure.

4. **Error Handling:** All platform-specific helpers gracefully return None/empty on error, preventing crash and allowing CLI to proceed without blocking.

## Known Stubs

None. No placeholder code or intentional gaps left in implementation.

## Next Action

Phase 3 complete! All drive health, setup, and interactive mode work end-to-end. Ready for Phase 4 (Guided Deletion) to implement confirmation workflow for safe file deletion.

---

**Completed:** 2026-03-22
**Executor:** Claude Sonnet 4.6
**Phase:** 03-drive-health-setup
**Plan:** 04 (gap_closure)
