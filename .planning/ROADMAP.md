# Roadmap: diskcomp

**Created:** 2026-03-22
**Milestone:** v1.0 — Shareable, safe, cross-platform drive comparison tool

---

## Phase 1 — Core Engine + Report

**Goal:** A working scanner that hashes two drives and outputs a reliable CSV report. The foundation everything else builds on.

**Requirements covered:** CORE-01 through CORE-06, RPT-01 through RPT-05

**Deliverables:**
- `diskcomp/scanner.py` — cross-platform drive walker, noise filter, file collector
- `diskcomp/hasher.py` — SHA256 engine with chunked reading, error handling
- `diskcomp/reporter.py` — CSV and JSON output, atomic write, timestamped filename
- `diskcomp/cli.py` — argparse CLI with `--keep`, `--other`, `--dry-run`, `--limit`, `--output`, `--format`
- `diskcomp/__main__.py` — entry point
- Basic `print()`-based progress (no UI library yet)
- Test: both drives produce correct duplicate/unique classification

**Done when:** `python3 -m diskcomp --keep /Volumes/A --other /Volumes/B` produces a correct CSV report on macOS, Linux, and Windows.

---

## Phase 2 — Terminal UI

**Goal:** Replace raw prints with a beautiful, cross-platform terminal experience. Rich when available, ANSI fallback when not.

**Requirements covered:** UI-01 through UI-05

**Deliverables:**
- `diskcomp/ui.py` — UI abstraction layer (rich renderer + ANSI fallback)
- Per-folder scanning ticks (cyan → green ✓ on completion)
- Live hash progress bar: `[████░░░░] 62.3%  1,204/1,938  12.4 MB/s  ETA 3m22s`
- Final summary banner with duplicate/unique counts and space breakdown
- Windows terminal compatibility (handles no-color mode, narrow terminals)
- `--no-color` flag for CI/piped output

**Done when:** The tool looks polished in macOS Terminal, iTerm2, Windows Terminal, and a basic Linux tty.

---

## Phase 3 — Drive Health + Pre-scan Setup

**Goal:** Before touching a single file, the user knows exactly what they're working with. No surprises mid-scan.

**Requirements covered:** HLTH-01 through HLTH-05, SETUP-01 through SETUP-04

**Deliverables:**
- `diskcomp/health.py` — space summary, filesystem detection, read speed test, SMART integration
- Interactive drive picker: lists all mounted drives with size + filesystem, user selects keep/other
- Pre-scan health report printed before hashing starts
- SMART data via `smartctl` subprocess if available; skip with notice if not
- Read speed test: 128MB sequential read benchmark
- Cross-platform filesystem warnings (e.g., "NTFS on macOS is read-only — deletion will be skipped")
- `diskcomp/platform.py` — OS abstraction for drive enumeration (macOS `diskutil`, Linux `/proc/mounts`, Windows `wmic`)

**Done when:** Running `diskcomp` with no arguments launches interactive setup, shows full health report, and only proceeds to scan after user confirmation.

---

## Phase 4 — Guided Deletion Workflow

**Goal:** Turn the report into action — safely. Two modes, undo log, zero surprises.

**Requirements covered:** DEL-01 through DEL-08

**Deliverables:**
- `diskcomp/deleter.py` — deletion engine with undo log, read-only detection, progress display
- Mode A (`--delete interactive`): per-file y/n/skip/abort prompt
- Mode B (`--delete workflow`): dry-run → summary → "type DELETE to confirm" → execute
- Undo log: `~/diskcomp-undo-YYYYMMDD-HHMMSS.json` written before first deletion
- `diskcomp undo --log ~/diskcomp-undo-*.json` — restore from undo log
- Read-only filesystem detection with clear error and skip behavior
- Space freed counter updated in real-time during deletion

**Done when:** A user can safely delete confirmed duplicates from a report, see a running tally of space freed, and restore any deleted file from the undo log.

---

## Phase 5 — Packaging + Distribution

**Goal:** Anyone can install and run diskcomp in under 60 seconds.

**Requirements covered:** DIST-01 through DIST-04

**Deliverables:**
- `diskcomp.py` — single-file build script that bundles all modules into one portable file
- `pyproject.toml` — pip-installable package with `diskcomp` CLI entry point
- `build_single.py` — script that generates the single-file `diskcomp.py` from source modules
- `README.md` — install options (pip vs single file), quick start, full usage reference, screenshots
- `.github/workflows/release.yml` — GitHub Actions: test on Mac/Linux/Windows, build single file, publish to PyPI on tag
- `tests/` — pytest suite covering scanner, hasher, reporter, deleter on all platforms

**Done when:** `pip install diskcomp` works, `python3 diskcomp.py --help` works, CI passes on all three platforms.

---

## Milestone Summary

| Phase | Name | Requirements | Status |
|-------|------|-------------|--------|
| 1 | Core Engine + Report | CORE + RPT | ○ Pending |
| 2 | Terminal UI | UI | ○ Pending |
| 3 | Drive Health + Setup | HLTH + SETUP | ○ Pending |
| 4 | Guided Deletion | DEL | ○ Pending |
| 5 | Packaging + Distribution | DIST | ○ Pending |

**v1.0 complete when:** All 5 phases done, CI green on macOS + Linux + Windows, README published, PyPI package live.

---
*Roadmap created: 2026-03-22*
