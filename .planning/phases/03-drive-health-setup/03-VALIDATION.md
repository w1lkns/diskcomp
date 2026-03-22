---
phase: 3
slug: drive-health-setup
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-22
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | unittest (stdlib) |
| **Config file** | none — stdlib, no config needed |
| **Quick run command** | `python3 -m unittest discover tests/ -v` |
| **Full suite command** | `python3 -m unittest discover tests/ -v` |
| **Estimated runtime** | ~3 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m unittest discover tests/ -v`
- **After every plan wave:** Run `python3 -m unittest discover tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 3-01-01 | 01 | 1 | HLTH-01, HLTH-02 | unit | `python3 -m unittest tests.test_health -v` | ❌ W0 | ⬜ pending |
| 3-01-02 | 01 | 1 | HLTH-03 | unit | `python3 -m unittest tests.test_health -v` | ❌ W0 | ⬜ pending |
| 3-01-03 | 01 | 1 | HLTH-04, HLTH-05 | unit | `python3 -m unittest tests.test_health -v` | ❌ W0 | ⬜ pending |
| 3-02-01 | 02 | 2 | SETUP-01, SETUP-02 | unit | `python3 -m unittest tests.test_drive_picker -v` | ❌ W0 | ⬜ pending |
| 3-02-02 | 02 | 2 | SETUP-03, SETUP-04 | integration | `python3 -m unittest discover tests/ -v` | ❌ W0 | ⬜ pending |
| 3-03-01 | 03 | 3 | HLTH-01–05, SETUP-01–04 | integration | `python3 -m unittest discover tests/ -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_health.py` — unit tests for health.py (space summary, filesystem detection, SMART, read-only warnings) covering HLTH-01–05
- [ ] `tests/test_drive_picker.py` — unit tests for drive_picker.py (drive enumeration, interactive picker, input validation) covering SETUP-01, SETUP-02, SETUP-04
- [ ] `tests/test_benchmarker.py` — unit tests for benchmarker.py (read-speed benchmark with mocked tempfile) covering HLTH-03

*Existing infrastructure (tests/test_scanner.py, tests/test_hasher.py, tests/test_reporter.py, tests/test_ui.py) covers non-health behavior.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SMART data displayed when smartmontools installed | HLTH-04 | Requires real hardware + smartmontools | Install smartmontools, run `diskcomp --keep /Volumes/A --other /Volumes/B`, confirm SMART health shown |
| Interactive drive picker lists real mounted drives | SETUP-01 | Requires real mounted drives | Run `python3 -m diskcomp` (no args), confirm all drives listed with size/filesystem |
| NTFS read-only warning appears on macOS | HLTH-02 | Requires NTFS drive on macOS | Mount NTFS drive, run diskcomp, confirm "NTFS read-only on macOS" warning shown |
| Read benchmark on a real drive | HLTH-03 | Cannot simulate real I/O timing | Run benchmark on an actual HDD/SSD and confirm MB/s figure is realistic |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
