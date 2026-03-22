# Requirements: diskcomp

**Defined:** 2026-03-22
**Core Value:** The user must always feel in control — no file is ever deleted without explicit confirmation, and every action is reversible via an undo log.

## v1 Requirements

### Core Engine

- [ ] **CORE-01**: Scanner walks two user-specified drives recursively, collects files ≥1KB
- [ ] **CORE-02**: Scanner skips OS noise files (.DS_Store, Thumbs.db, $RECYCLE.BIN, etc.) on all platforms
- [ ] **CORE-03**: SHA256 hashing identifies byte-for-byte duplicates regardless of filename or path
- [ ] **CORE-04**: Results classify each WD-side file as DUPLICATE or UNIQUE
- [ ] **CORE-05**: `--dry-run` flag walks and counts files without hashing (fast sanity check)
- [ ] **CORE-06**: `--limit N` flag hashes only first N files per drive (testing mode)

### Terminal UI

- [ ] **UI-01**: Per-folder progress: cyan arrow while scanning, green tick + file count when done
- [ ] **UI-02**: Live hash progress bar with percentage, files done/total, MB/s speed, and ETA
- [ ] **UI-03**: Works with `rich` if installed; falls back to plain ANSI if not
- [ ] **UI-04**: Graceful output on Windows terminal (cmd.exe, PowerShell, Windows Terminal)
- [ ] **UI-05**: Final summary banner: duplicates count + MB, unique count + MB, report path

### Drive Health

- [ ] **HLTH-01**: Space summary per drive (used / free / total) shown before scan
- [ ] **HLTH-02**: Filesystem type detection (NTFS, HFS+, APFS, exFAT, ext4) with cross-platform warnings
- [ ] **HLTH-03**: Read speed benchmark — 128MB sequential read test to flag slow/failing drives
- [ ] **HLTH-04**: SMART data display via smartmontools if available; gracefully skipped if not installed
- [ ] **HLTH-05**: Health check failures are warnings, not blockers — user can proceed after review

### Pre-scan Setup

- [ ] **SETUP-01**: Interactive mode asks user to confirm which drive is "keep" and which is "other"
- [ ] **SETUP-02**: Drive detection: lists all mounted drives with size/filesystem for user to pick from
- [ ] **SETUP-03**: Non-interactive mode accepts `--keep /path` and `--other /path` flags
- [ ] **SETUP-04**: Abort with clear message if specified drives are not mounted or not readable

### Report Output

- [ ] **RPT-01**: CSV report with columns: action, keep_path, other_path, size_mb, hash
- [ ] **RPT-02**: JSON report format available via `--format json`
- [ ] **RPT-03**: Default report path is `~/diskcomp-report-YYYYMMDD-HHMMSS.csv`
- [ ] **RPT-04**: Custom report path via `--output /path/to/report.csv`
- [ ] **RPT-05**: Report written atomically (temp file → rename) to prevent partial writes on crash

### Guided Deletion

- [ ] **DEL-01**: Deletion only starts from an existing report — never from scan results directly
- [ ] **DEL-02**: Mode A (interactive): presents each duplicate, user confirms y/n/skip/abort per file
- [ ] **DEL-03**: Mode B (workflow): dry-run preview → summary → "type DELETE to confirm" → execute
- [ ] **DEL-04**: User selects deletion mode at runtime, or can skip deletion entirely
- [ ] **DEL-05**: Undo log written before any file is deleted: path, size, hash, timestamp
- [ ] **DEL-06**: `--undo` flag reads undo log and restores files from trash/recycle bin where possible
- [ ] **DEL-07**: Progress shown during deletion with running total of space freed
- [ ] **DEL-08**: NTFS/read-only filesystem detection — warns user and skips deletion if drive is read-only

### Distribution

- [ ] **DIST-01**: `diskcomp.py` — single-file script, zero mandatory dependencies, runs with `python3 diskcomp.py`
- [ ] **DIST-02**: `pip install diskcomp` — installs `diskcomp` CLI entry point
- [ ] **DIST-03**: `pyproject.toml` with metadata, optional deps (`rich`, `smartmontools` note)
- [ ] **DIST-04**: README with install options, usage examples, and screenshots

## v2 Requirements

### Filtering

- **FILT-01**: `--min-size` / `--max-size` flags to narrow scan scope
- **FILT-02**: `--include` / `--exclude` glob patterns for file types
- **FILT-03**: `--since DATE` to scan only files modified after a date

### Reporting

- **RPT-V2-01**: HTML report with sortable table and folder tree visualization
- **RPT-V2-02**: Diff view: side-by-side folder structure showing what's on each drive

### Multi-drive

- **MULTI-01**: Compare more than two drives simultaneously
- **MULTI-02**: N-way dedup: find files that exist on 3+ drives

## Out of Scope

| Feature | Reason |
|---------|--------|
| GUI / web interface | CLI-first; GUI adds significant complexity for v1 |
| Cloud storage | Different access patterns, auth, rate limits — separate tool |
| Scheduled/automatic scans | This is a deliberate, manual workflow by design |
| Auto-deletion without confirmation | Safety non-negotiable — would undermine core value |
| File sync (rsync-style) | Different product category |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CORE-01 through CORE-06 | Phase 1 | Pending |
| UI-01 through UI-05 | Phase 2 | Pending |
| HLTH-01 through HLTH-05 | Phase 3 | Pending |
| SETUP-01 through SETUP-04 | Phase 3 | Pending |
| RPT-01 through RPT-05 | Phase 1 | Pending |
| DEL-01 through DEL-08 | Phase 4 | Pending |
| DIST-01 through DIST-04 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 34 total
- Mapped to phases: 34
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-22*
*Last updated: 2026-03-22 after initial definition*
