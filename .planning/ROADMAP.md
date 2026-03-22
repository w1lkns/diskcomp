# Roadmap: diskcomp

**Created:** 2026-03-22
**Milestone:** v1.0 — Shareable, safe, cross-platform drive comparison tool

## Phases

- [x] **Phase 1: Core Engine + Report** - Scanner, SHA256 hashing, CSV/JSON output, CLI ✓ COMPLETE
- [ ] **Phase 2: Terminal UI** - Rich progress bars, per-folder ticks, ANSI fallback
- [ ] **Phase 3: Drive Health + Setup** - Drive picker, health checks, SMART, filesystem detection
- [ ] **Phase 4: Guided Deletion** - Mode A/B deletion, undo log, read-only detection
- [ ] **Phase 5: Packaging + Distribution** - Single .py, pip, GitHub Actions CI

## Phase Details

### Phase 1: Core Engine + Report
**Goal**: A working scanner that hashes two drives and outputs a reliable CSV report. The foundation everything else builds on. `python3 -m diskcomp --keep /Volumes/A --other /Volumes/B` produces a correct CSV report on macOS, Linux, and Windows.
**Depends on**: Nothing (first phase)
**Requirements**: [CORE-01, CORE-02, CORE-03, CORE-04, CORE-05, CORE-06, RPT-01, RPT-02, RPT-03, RPT-04, RPT-05]
**Success Criteria** (what must be TRUE):
  1. Running `python3 -m diskcomp --keep /path/A --other /path/B` exits 0 and writes a CSV report
  2. SHA256 hashes correctly classify files as DUPLICATE or UNIQUE regardless of filename/path
  3. Scanner skips OS noise files (.DS_Store, Thumbs.db, $RECYCLE.BIN) on all platforms
  4. `--dry-run` flag walks and counts files without hashing
  5. CSV report is written atomically and includes action, keep_path, other_path, size_mb, hash columns
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md — Types + Scanner (cross-platform filesystem walker with noise filtering) ✓ COMPLETE
- [x] 01-02-PLAN.md — Hasher + Reporter (SHA256 hashing and CSV/JSON output) ✓ COMPLETE
- [x] 01-03-PLAN.md — CLI + Tests (argparse interface and comprehensive test suite) ✓ COMPLETE

### Phase 2: Terminal UI
**Goal**: Replace raw prints with a beautiful, cross-platform terminal experience. Rich when available, ANSI fallback when not.
**Depends on**: Phase 1
**Requirements**: [UI-01, UI-02, UI-03, UI-04, UI-05]
**Success Criteria** (what must be TRUE):
  1. Per-folder progress shows cyan arrow while scanning, green tick + file count on completion
  2. Live hash progress bar shows percentage, files done/total, MB/s speed, and ETA
  3. Tool works with `rich` when installed and falls back to plain ANSI when not
  4. Final summary banner shows duplicates count + MB, unique count + MB, report path
**Plans**: TBD

### Phase 3: Drive Health + Setup
**Goal**: Before touching a single file, the user knows exactly what they're working with. No surprises mid-scan.
**Depends on**: Phase 2
**Requirements**: [HLTH-01, HLTH-02, HLTH-03, HLTH-04, HLTH-05, SETUP-01, SETUP-02, SETUP-03, SETUP-04]
**Success Criteria** (what must be TRUE):
  1. Space summary (used/free/total) shown per drive before scan starts
  2. Filesystem type detected and cross-platform warnings shown (e.g., NTFS read-only on macOS)
  3. Interactive mode lists all mounted drives with size/filesystem for user to pick keep/other
  4. Read speed benchmark runs 128MB test and flags slow/failing drives
  5. Running `diskcomp` with no args launches interactive setup and proceeds only after user confirmation
**Plans**: TBD

### Phase 4: Guided Deletion
**Goal**: Turn the report into action — safely. Two modes, undo log, zero surprises.
**Depends on**: Phase 3
**Requirements**: [DEL-01, DEL-02, DEL-03, DEL-04, DEL-05, DEL-06, DEL-07, DEL-08]
**Success Criteria** (what must be TRUE):
  1. Deletion only starts from an existing report file, never from scan results directly
  2. Mode A (interactive): user confirms y/n/skip/abort per file
  3. Mode B (workflow): dry-run preview → summary → "type DELETE to confirm" → execute
  4. Undo log written before any file is deleted; `--undo` flag restores deleted files
  5. Read-only filesystem detection warns and skips deletion on protected drives
**Plans**: TBD

### Phase 5: Packaging + Distribution
**Goal**: Anyone can install and run diskcomp in under 60 seconds.
**Depends on**: Phase 4
**Requirements**: [DIST-01, DIST-02, DIST-03, DIST-04]
**Success Criteria** (what must be TRUE):
  1. `pip install diskcomp` installs a `diskcomp` CLI entry point that works
  2. `python3 diskcomp.py --help` works with zero dependencies
  3. CI passes on macOS, Linux, and Windows
  4. README covers install options, usage examples, and safety model
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Core Engine + Report | 3/3 | Complete    | 2026-03-22 |
| 2. Terminal UI | 0/TBD | Not started | - |
| 3. Drive Health + Setup | 0/TBD | Not started | - |
| 4. Guided Deletion | 0/TBD | Not started | - |
| 5. Packaging + Distribution | 0/TBD | Not started | - |

---
*Roadmap created: 2026-03-22*
*Plans finalized: 2026-03-22*
