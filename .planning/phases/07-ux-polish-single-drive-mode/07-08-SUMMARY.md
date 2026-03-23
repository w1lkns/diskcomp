---
phase: 07-ux-polish-single-drive-mode
plan: 08
subsystem: ui
tags: [health-checks, ntfs, cross-platform, user-education]

requires:
  - phase: 07-03
    provides: "Foundation for UX polish sprint"

provides:
  - NTFS-on-macOS/Linux callout in health check output with fix instructions
  - README 'Known Limitations' section documenting NTFS read-only limitation
  - Comprehensive test coverage for NTFS warning on all platforms

affects: [user-facing documentation, future filesystem handling enhancements]

tech-stack:
  added: []
  patterns:
    - "Platform-specific filesystem warnings in health check display"
    - "Leveraging get_fix_instructions() for actionable remediation guidance"

key-files:
  created: []
  modified:
    - diskcomp/cli.py (_display_health_result function)
    - README.md (added 'Known Limitations' section)
    - tests/test_cli.py (4 new NTFS-specific tests)

key-decisions:
  - Display explicit NTFS callout only on macOS/Linux (not Windows where NTFS is writable)
  - Use sys.platform check to determine whether to show warning
  - Include fix instructions from get_fix_instructions() for actionable guidance

patterns-established:
  - "Filesystem-specific warnings shown in _display_health_result() after basic filesystem/writable status"
  - "Use of get_fix_instructions() for platform-specific remediation text"
  - "Comprehensive platform-specific testing for health check warnings"

requirements-completed: []

duration: 8 min
completed: 2025-03-23
---

# Phase 7 Plan 8: NTFS Read-Only Limitation Callout Summary

**NTFS drives now show explicit read-only warning on macOS/Linux with fix instructions in health check output; README documents known limitations**

## Performance

- **Duration:** 8 min
- **Started:** 2025-03-23T11:42:00Z
- **Completed:** 2025-03-23T11:50:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added NTFS-on-macOS/Linux specific warning callout in _display_health_result()
- Warning format: "⚠ NTFS on darwin/linux: This drive is read-only. Files cannot be deleted from it here." followed by fix instructions
- NTFS callout correctly omitted on Windows (NTFS is writable there)
- README updated with new "Known Limitations" section documenting NTFS read-only limitation with workaround instructions
- 4 new tests verify callout appears correctly on macOS/Linux but not on Windows or for non-NTFS filesystems

## Task Commits

Each task was committed atomically:

1. **Task 1: Add NTFS-on-macOS/Linux callout in health check output (D-19)** - `cd58a96` (feat)
   - Modified _display_health_result() to detect NTFS + (darwin or linux)
   - Display explicit warning with fix instructions from get_fix_instructions()
   - Added 4 comprehensive tests for NTFS warning on all platforms

2. **Task 2: Add 'Known Limitations' section to README (D-20)** - `cd58a96` (feat)
   - Added "Known Limitations" section documenting NTFS-on-macOS/Linux read-only limitation
   - Included workaround with installation instructions for ntfs-3g and Tuxera
   - Cross-references health check warning in README

**Plan metadata:** included in `cd58a96` (feat: complete 07-08 plan)

## Files Created/Modified

- `diskcomp/cli.py` - Added NTFS-on-macOS/Linux callout in _display_health_result(); updated import to include get_fix_instructions
- `README.md` - Added "Known Limitations" section with NTFS read-only limitation documentation and fix instructions
- `tests/test_cli.py` - Added 4 new tests: test_display_health_result_ntfs_on_macos, test_display_health_result_ntfs_on_linux, test_display_health_result_ntfs_on_windows, test_display_health_result_ext4_on_macos

## Decisions Made

- Decision D-19: Display NTFS warning only on macOS/Linux (sys.platform in ['darwin', 'linux']), not on Windows where NTFS is natively writable
- Decision D-20: Use README "Known Limitations" section (not buried in Advanced Usage) for prominent user education
- Test strategy: Mock sys.platform to verify correct behavior on all platforms in a single test run

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all tasks completed without blockers.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

NTFS limitation handling complete and well-documented. Users on macOS/Linux will see clear warning and actionable fix instructions during health checks. Ready for next UX polish tasks.

---

*Phase: 07-ux-polish-single-drive-mode*
*Plan: 08*
*Completed: 2025-03-23*
