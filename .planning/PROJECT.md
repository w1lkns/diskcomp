# diskcomp

## What This Is

diskcomp is a cross-platform CLI tool for comparing two external drives and safely managing duplicate files. It scans both drives using SHA256 hashing, reports duplicates and unique files, runs drive health checks before scanning, and offers a guided deletion workflow with dry-run, per-file confirmation, and a full undo log. Designed to be shared publicly — zero mandatory dependencies, works on macOS, Windows, and Linux.

## Core Value

The user must always feel in control: no file is ever deleted without explicit confirmation, and every action is reversible via an undo log.

## Requirements

### Validated

- [x] Cross-platform scanner: walk two drives, SHA256 hash files ≥1KB, skip OS noise — *Validated in Phase 1: Core Engine + Report*
- [x] Report output: CSV with action, paths, sizes, hashes — *Validated in Phase 1: Core Engine + Report*

### Active

- [ ] Terminal UI: live progress bar, per-folder completion ticks, speed + ETA display
- [ ] Terminal UI: live progress bar, per-folder completion ticks, speed + ETA display
- [ ] Drive health checks: space summary, filesystem detection, read speed test, SMART data (optional)
- [ ] Pre-scan questions: ask user which drive to keep, confirm before any destructive step
- [ ] Guided deletion — Mode A: interactive per-file confirmation with dry-run
- [ ] Guided deletion — Mode B: full workflow with undo log and abort-at-any-time
- [ ] User picks deletion mode at runtime (or skips deletion entirely)
- [ ] Single-file distribution: `diskcomp.py` with zero mandatory deps
- [ ] pip package: `pip install diskcomp` entry point

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
| SHA256 for dedup | Cryptographically collision-resistant; slower than size/name but no false positives | — Pending |
| Zero mandatory deps | Widest reach — users shouldn't need to pip install just to run a script | — Pending |
| rich as optional dep | Beautiful UI when available; graceful ASCII fallback when not | — Pending |
| Undo log over recycle bin | Cross-platform recycle bin APIs are unreliable; log-then-delete is simpler and auditable | — Pending |

---
*Last updated: 2026-03-22 after Phase 1 completion*
