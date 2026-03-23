# diskcomp

## What This Is

diskcomp is a cross-platform CLI tool for finding and safely deleting duplicate files — either across two drives (keep one, delete from the other) or within a single drive (remove redundant copies). It scans with SHA256 hashing, generates CSV/JSON reports, runs pre-scan drive health checks, and offers a guided deletion workflow with per-file confirmation, batch mode, and a full audit log. Designed to be shared publicly — zero mandatory dependencies, works on macOS, Windows, and Linux.

## Core Value

The user must always feel in control: no file is ever deleted without explicit confirmation, and every action is reversible via an undo log.

## Requirements

### Validated

- [x] Cross-platform scanner: walk two drives, SHA256 hash files ≥1KB, skip OS noise — *Validated in Phase 1: Core Engine + Report*
- [x] Report output: CSV with action, paths, sizes, hashes — *Validated in Phase 1: Core Engine + Report*

### Active

_(All requirements validated — see below)_

### Validated (continued)

- [x] Terminal UI: live progress bar, per-folder completion ticks, speed + ETA display — *Validated in Phase 2: Terminal UI + Progress*
- [x] Drive health checks: space summary, filesystem detection, read speed test, SMART data (optional) — *Validated in Phase 3: Drive Health + Pre-Scan*
- [x] Pre-scan questions: ask user which drive to keep, confirm before any destructive step — *Validated in Phase 3: Drive Health + Pre-Scan*
- [x] Guided deletion — Mode A: interactive per-file confirmation (pick which copy to delete) — *Validated in Phase 4 + Phase 7*
- [x] Guided deletion — Mode B: batch workflow with preview, undo log, and abort-at-any-time — *Validated in Phase 4: Guided Deletion*
- [x] User picks deletion mode at runtime (or skips deletion entirely) — *Validated in Phase 4: Guided Deletion*
- [x] Single-file distribution: `diskcomp.py` with zero mandatory deps — *Validated in Phase 5: Packaging + Distribution*
- [x] pip package: `pip install diskcomp` entry point — *Validated in Phase 5: Packaging + Distribution*
- [x] Two-pass size-filter optimization before hashing — *Validated in Phase 6: Performance*
- [x] Read speed benchmark displayed during health checks — *Validated in Phase 6: Performance*
- [x] Single-drive mode (`--single`): find internal duplicates on one drive — *Validated in Phase 7: UX Polish*
- [x] Load previous report from menu or `--delete-from` (skip re-scanning) — *Validated in Phase 7: UX Polish*
- [x] Interactive deletion shows both copies numbered for user to choose which to delete — *Validated in Phase 7: UX Polish*
- [x] Single-drive summary table: no spurious "Unique in Keep" row — *Validated in Phase 7: UX Polish*

### Out of Scope

- Cloud storage comparison — out of v1, different problem domain
- GUI / web interface — CLI-first, keep scope tight
- Automatic scheduled scans — this is a manual, deliberate tool
- Auto-deletion without confirmation — safety non-negotiable

## Context

- Born from a real use case: comparing a 1TB HFS+ drive vs a 319GB NTFS drive on macOS
- macOS mounts NTFS read-only — deletion requires cross-platform abstraction layer
- SMART data requires `smartmontools` (external) — must degrade gracefully if absent
- `rich` library gives best cross-platform terminal UI — optional dep with ASCII fallback
- Windows drive letters (C:\, D:\) vs Unix mount points (/Volumes/X) need abstraction
- Target users: non-developers who download a single .py file and run it

## Constraints

- **Compatibility**: Python 3.8+ — widest OS support, ships with macOS/Linux, available on Windows
- **Dependencies**: Zero mandatory deps — `rich` and `smartmontools` are optional enhancements
- **Safety**: Every destructive action requires explicit confirmation; dry-run always available
- **Distribution**: Single `diskcomp.py` + pip package; both must stay in sync

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| SHA256 for dedup | Cryptographically collision-resistant; slower than size/name but no false positives | Validated — zero false positives across all test suites; Phase 6 will add size-filter pre-pass to recover speed |
| Zero mandatory deps | Widest reach — users shouldn't need to pip install just to run a script | Validated — ships as single `diskcomp.py` with no required deps; pip package also zero-dep |
| rich as optional dep | Beautiful UI when available; graceful ASCII fallback when not | Validated — both paths tested and working; CI runs without rich installed |
| Undo log over recycle bin | Cross-platform recycle bin APIs are unreliable; log-then-delete is simpler and auditable | Validated — JSON undo log works on macOS, Linux, and Windows; no platform-specific code needed |

---
*Last updated: 2026-03-23 after Phase 7 completion — single-drive mode, load-report flow, interactive copy-picker, UX polish*
