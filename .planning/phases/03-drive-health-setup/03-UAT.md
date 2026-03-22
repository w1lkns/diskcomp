---
status: complete
phase: 03-drive-health-setup
source: [03-01-SUMMARY.md, 03-02-SUMMARY.md, 03-03-SUMMARY.md]
started: 2026-03-22T00:00:00Z
updated: 2026-03-22T00:00:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

[testing complete]

## Tests

### 1. Drive Space Summary Display
expected: Running `python3 -m diskcomp --keep /path1 --other /path2` shows a space summary for each drive before the scan starts — total GB, used GB, and free GB. The health info is printed in a human-readable format, not raw data.
result: pass

### 2. Filesystem Type Detection
expected: The health output before the scan includes the filesystem type (e.g., APFS, ext4, NTFS) for each drive. On macOS with an NTFS drive, a warning is shown about NTFS write compatibility issues.
result: pass

### 3. Read-Only Detection
expected: If a drive is mounted read-only, the health display shows a warning indicating the drive is read-only. If the keep drive is read-only, the scan is blocked and an error is shown. If the other drive is read-only, a warning appears but the scan still proceeds.
result: issue
reported: "warning and block is shown but no instructions on how to fix it — user wants actionable guidance like how to remount writable on macOS, install a dependency (e.g. NTFS driver), or manually change permissions"
severity: major

### 4. Read Speed Benchmark
expected: The health check display includes a read speed measurement (in MB/s) for each drive. If the benchmark fails or is unavailable, it degrades gracefully — no crash, just omits or shows N/A for that field.
result: issue
reported: "should offer a retry option if the benchmark fails, and show an alert explaining what went wrong rather than silently showing N/A or omitting the result"
severity: major

### 5. SMART Data (Optional/Graceful)
expected: If smartctl is installed, SMART data is shown. If it's not installed or unavailable, the health display skips it without crashing or showing an error — it's simply omitted.
result: pass

### 6. Drive Enumeration Lists Drives
expected: Running `python3 -m diskcomp` with no arguments shows a numbered list of all mounted drives, with size and filesystem info for each. No crash if psutil is unavailable — it falls back to subprocess-based enumeration.
result: pass

### 7. Interactive Keep/Other Drive Selection
expected: After the drive list is shown, the user is prompted to select which drive to keep (by number), then which drive to compare (by number). Invalid inputs (letters, out-of-range numbers) show an error and re-prompt until a valid selection is made.
result: issue
reported: "drive list should also show the drive's name/volume label alongside the number, path, and size so users can identify drives more easily"
severity: major

### 8. Minimum Drives Validation
expected: If only one drive is mounted (or no drives are detected), the interactive picker exits gracefully with a user-friendly message like "Need at least 2 drives" rather than crashing or showing a Python traceback.
result: pass

### 9. No-Args Mode Launches Interactive Picker
expected: Running `python3 -m diskcomp` with no `--keep` or `--other` arguments automatically enters interactive mode — it lists drives and prompts for selection. It does NOT immediately error about missing required arguments.
result: pass

### 10. Health Info Shown Before Scan (Non-Interactive)
expected: Running with `--keep` and `--other` flags still shows the health summary (space, filesystem, warnings) before the scan starts. Health checks run in both interactive and non-interactive modes.
result: pass

### 11. User Confirmation Prompt
expected: After health info is displayed, the user sees a prompt like "Start scan? (y/n):" before the scan begins. Answering "n" cancels gracefully (exit 0, no scan runs). Answering "y" proceeds to the scan.
result: pass

### 12. Non-Writable Keep Drive Blocks Scan
expected: If the keep drive is not writable (e.g., mounted read-only), the scan is blocked after the health check — main() returns exit code 1 and the scan never starts. A clear error message explains why.
result: pass

## Summary

total: 12
passed: 9
issues: 3
pending: 0
skipped: 0

## Gaps

- truth: "When a read-only drive is detected, the user should see actionable instructions on how to fix it — e.g., how to remount writable on macOS, install an NTFS driver (like macFUSE + NTFS-3G), or manually change permissions"
  status: failed
  reason: "User reported: warning and block is shown but no instructions on how to fix it"
  severity: major
  test: 3
  root_cause: "health.py:175-176 generates generic static warning with no remediation; cli.py:135-139 prints warnings without platform/fs-specific fix guidance; no mapping exists between filesystem type + platform and actionable fix steps"
  fix: "Add get_fix_instructions(fstype, platform, mount_point) helper in health.py; embed fix steps in warning text; update cli.py to display them"
  artifacts: [diskcomp/health.py, diskcomp/cli.py]
  missing: [platform+fs to fix-instructions mapping, remount/NTFS-3G/macFUSE guidance]

- truth: "When a read speed benchmark fails, show an alert explaining what went wrong and offer a retry option rather than silently omitting the result or showing N/A"
  status: failed
  reason: "User reported: should offer a retry option if the benchmark fails, and show an alert explaining what went wrong rather than silently showing N/A or omitting the result"
  severity: major
  test: 4
  root_cause: "benchmarker.py exists but benchmark_read_speed() is NEVER called in the CLI flow; display_health_checks() only calls check_drive_health(); HealthCheckResult has no benchmark field; no UI for error display or retry"
  fix: "Add benchmark_result field to HealthCheckResult; invoke benchmark_read_speed() in display_health_checks(); add retry prompt on failure; show error message when benchmark fails"
  artifacts: [diskcomp/benchmarker.py, diskcomp/cli.py, diskcomp/types.py]
  missing: [benchmark invocation in CLI, retry prompt UI, error display, HealthCheckResult.benchmark_result field]

- truth: "The interactive drive list should show the drive's volume label/name alongside the number, mountpoint, and size so users can identify drives by name"
  status: failed
  reason: "User reported: drive list should also show the drive's name/volume label alongside the number, path, and size so users can identify drives more easily"
  severity: major
  test: 7
  root_cause: "DriveInfo dataclass (types.py:82-101) has no volume_label field; _get_drives_macos() parses plist but never extracts VolumeName; _get_drives_linux() uses df which provides no label; _get_drives_windows() uses wmic but doesn't query volume name; interactive_drive_picker() only displays mountpoint"
  fix: "Add volume_label: Optional[str] to DriveInfo; add label retrieval per platform (diskutil info on macOS, blkid/lsblk on Linux, wmic volumename on Windows); update interactive_drive_picker() display"
  artifacts: [diskcomp/types.py, diskcomp/drive_picker.py]
  missing: [DriveInfo.volume_label field, per-platform label retrieval, display in picker]
