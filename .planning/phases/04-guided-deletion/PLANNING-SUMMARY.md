# Phase 04: Guided Deletion — Planning Complete

**Date:** 2026-03-22
**Status:** ✓ Planning Complete — 3 executable plans created

## Overview

Phase 4 implements safe, auditable file deletion with two user-selectable modes and a permanent undo log. All 8 requirements (DEL-01 through DEL-08) are mapped to specific tasks across 3 plans organized in 3 execution waves.

**Core Principle:** The user must always feel in control. No file is ever deleted without explicit confirmation, and every deletion is recorded in an audit log for permanent reference.

## Plans Created

### Plan 01: Foundation (Wave 1)
**Title:** Types, Report Reader, Undo Log
**Duration:** ~20-30 min
**Parallelizable:** Yes (no dependencies)

Creates the data contracts and utility classes:
- **UndoEntry & DeletionResult dataclasses** in types.py — type-safe deletion state
- **ReportReader class** in reporter.py — loads CSV/JSON reports, filters for deletion candidates
- **UndoLog writer** in new deletion.py — accumulates and atomically writes deletion audit entries

**Requirements covered:** DEL-01, DEL-05

---

### Plan 02: Orchestration (Wave 2)
**Title:** Deletion Workflows (Mode A & B) + UI Extensions
**Duration:** ~30-40 min
**Dependencies:** Plan 01

Implements the two deletion state machines:
- **DeletionOrchestrator.interactive_mode()** — per-file y/n/skip/abort prompts with running totals
- **DeletionOrchestrator.batch_mode()** — dry-run preview → type-to-confirm → execute with progress
- **UIHandler extensions** — start_deletion(), on_file_deleted() for both Rich and ANSI

**Requirements covered:** DEL-02, DEL-03, DEL-04, DEL-05, DEL-07, DEL-09

---

### Plan 03: CLI Integration (Wave 3)
**Title:** --delete-from and --undo flags + Tests
**Duration:** ~20-30 min
**Dependencies:** Plans 01 & 02

Wires deletion into the command-line interface:
- **--delete-from flag** — loads report, filters candidates, prompts for mode, executes deletion
- **--undo flag** — displays audit log (read-only, no restoration attempted)
- **Read-only detection** — checks drive writability, warns and skips protected files
- **Integration tests** — validates both workflows, error cases, user interaction

**Requirements covered:** DEL-01, DEL-04, DEL-06, DEL-08

---

## Wave Structure

```
Wave 1 (Parallel, no deps)
├─ 04-01: Types + Reader + UndoLog
│
Wave 2 (Depends on Wave 1, partially parallel)
├─ 04-02: Orchestrator + UIHandler
│
Wave 3 (Depends on Waves 1 & 2)
└─ 04-03: CLI Integration + Tests
```

**Execution path:** Execute Wave 1 → Wave 2 → Wave 3 sequentially. All tasks within each wave can run in parallel (no file conflicts).

---

## Requirement Traceability

| Req | Description | Plan | Task | Status |
|-----|-------------|------|------|--------|
| DEL-01 | Deletion only from existing report | 01 | 2 | ✓ ReportReader validates file |
| DEL-01 | (continued) | 03 | 3 | ✓ --delete-from flag checks file |
| DEL-02 | Mode A interactive per-file | 02 | 1 | ✓ interactive_mode() implementation |
| DEL-03 | Mode B workflow with confirmation | 02 | 1 | ✓ batch_mode() implementation |
| DEL-04 | Runtime mode selection | 02 | 1 | ✓ Prompt in orchestrator |
| DEL-04 | (continued) | 03 | 3 | ✓ CLI mode prompt |
| DEL-05 | Undo log written before deletion | 01 | 3 | ✓ UndoLog.add() before remove() |
| DEL-05 | (continued) | 02 | 1 | ✓ Orchestrator calls undo_log |
| DEL-06 | --undo reads audit log | 03 | 2 | ✓ _show_undo_log() function |
| DEL-07 | Progress shown with running total | 02 | 2 | ✓ UIHandler methods |
| DEL-08 | Read-only detection & skip | 03 | 3 | ✓ _check_deletion_readiness() |
| DEL-09 | Mode B progress during execution | 02 | 1 | ✓ batch_mode() with callbacks |

**Coverage:** 8/8 requirements addressed. All locked decisions (D-01 through D-18) implemented.

---

## Key Design Decisions (from CONTEXT.md)

### Hard Delete + Audit Log
- **D-11:** Files permanently removed (os.remove), no trash/recycle bin
- **D-14, D-15:** --undo is audit view only, "These files were permanently deleted"
- **Rationale:** Cross-platform recycle bin APIs unreliable; permanent deletion + audit trail is the safe model

### Mode A: Per-File Confirmation
- **D-06, D-07:** y / n / skip / abort options, no "delete all remaining" shortcut
- **Rationale:** Safety-critical — every file requires explicit confirmation

### Mode B: Type-to-Confirm
- **D-08:** Dry-run preview → summary → "type DELETE to proceed"
- **Rationale:** Prevents accidental deletion; requires deliberate acknowledgment

### Undo Log Semantics
- **D-12:** Entries logged AFTER successful deletion
- **D-17:** Partial progress acceptable — undo log reflects what was actually deleted
- **Rationale:** Audit trail always truthful, crash-safe via atomic JSON writes

### Read-Only Protection
- **D-18:** Warn and skip files on read-only drives
- **Rationale:** Prevents errors on NTFS/macOS, external drives, protected filesystems

---

## File Changes Summary

| File | Change | Plan | Task |
|------|--------|------|------|
| diskcomp/types.py | Add UndoEntry, DeletionResult | 01 | 1 |
| diskcomp/reporter.py | Add ReportReader class | 01 | 2 |
| diskcomp/deletion.py | NEW: UndoLog, DeletionOrchestrator | 01, 02 | 3, 1 |
| diskcomp/ui.py | Add deletion progress methods | 02 | 2 |
| diskcomp/cli.py | Add --delete-from, --undo flags | 03 | 1, 2, 3 |
| tests/test_integration.py | Add deletion CLI tests | 03 | 4 |

---

## Success Criteria (Per Plan)

### Plan 01
- [ ] UndoEntry and DeletionResult importable
- [ ] ReportReader.load() auto-detects CSV/JSON, filters for DELETE_FROM_OTHER
- [ ] UndoLog.write() atomically writes entries to JSON
- [ ] All three components have passing tests

### Plan 02
- [ ] interactive_mode() handles y/n/skip/abort per file
- [ ] batch_mode() shows preview, requires "DELETE" confirmation, executes with progress
- [ ] Both modes return DeletionResult with accurate counts
- [ ] UIHandler.start_deletion() and on_file_deleted() update progress
- [ ] Keyboard interrupts handled gracefully

### Plan 03
- [ ] --delete-from flag accepts file path, validates, loads report
- [ ] Mode selection prompt asks (interactive/batch/skip)
- [ ] --undo flag reads log, displays audit, prints "permanently deleted" message
- [ ] Read-only detection warns and skips files on protected drives
- [ ] Integration tests cover all workflows, error cases, user input
- [ ] Help text clear and accurate for both flags

---

## Integration Points

**From Phase 3 (existing code):**
- health.py `check_drive_health()` — detect drive write permissions (D-18)
- health.py `get_fix_instructions()` — provide remediation guidance for read-only drives
- UIHandler from Phase 2 — reuse for deletion progress display

**To Phase 5:**
- diskcomp/deletion.py available for packaging as part of distribution

---

## Context Files for Executor

When executing these plans, the executor should read:
1. **/.planning/phases/04-guided-deletion/04-CONTEXT.md** — User decisions and phase boundary
2. **/.planning/phases/04-guided-deletion/04-RESEARCH.md** — Standard stack, architecture patterns, pitfalls
3. **diskcomp/types.py** — Existing @dataclass pattern (FileRecord, ScanResult, DriveInfo)
4. **diskcomp/reporter.py** — ReportWriter atomic write pattern, CSV/JSON formats
5. **diskcomp/ui.py** — UIHandler factory, existing progress methods (start_hash, on_file_hashed)
6. **diskcomp/health.py** — check_drive_health(), get_fix_instructions() functions

---

## Testing Strategy

**Per-plan testing:**
- Plan 01: Unit tests for dataclasses, ReportReader CSV/JSON parsing, UndoLog write
- Plan 02: Unit tests for both deletion modes with mocked user input, error handling, progress callbacks
- Plan 03: Integration tests for CLI flags, end-to-end workflows, error cases

**Wave testing:**
- Wave 1 complete: `pytest tests/test_deletion.py -xvs`
- Wave 2 complete: `pytest tests/test_deletion.py tests/test_ui.py -xvs` (includes deletion UI tests)
- Wave 3 complete: `pytest tests/test_integration.py::TestDeletionCLI -xvs` + `python3 -m diskcomp --help | grep -E "delete-from|undo"`

**Phase gate:** All 8 DEL requirements verified via tests and manual E2E testing before proceeding to Phase 5.

---

## Assumptions & Notes

1. **Hard delete is permanent** — No attempt to restore from trash/recycle bin. This is intentional and approved (per D-11, D-14).

2. **Undo log entries added AFTER deletion** — Unlike pre-deletion journaling, entries only exist for files actually deleted. If deletion fails, no log entry. This is a conscious choice for audit accuracy.

3. **UIHandler reused from Phase 2** — start_deletion() and on_file_deleted() follow same pattern as start_hash() and on_file_hashed(). No new UI library dependencies.

4. **read-only check uses health.py functions** — Avoids duplicating filesystem detection logic. _check_deletion_readiness() wraps check_drive_health() for each candidate.

5. **Mode selection is one-time** — User chooses mode at CLI, commits to it. Cannot switch mid-workflow (prevents confusion and edge cases).

---

## Next Action

```bash
/gsd:execute-phase 04-guided-deletion --wave 1
```

Then:
```bash
/gsd:execute-phase 04-guided-deletion --wave 2
/gsd:execute-phase 04-guided-deletion --wave 3
```

Or sequentially:
```bash
/gsd:execute-phase 04-guided-deletion
```

---

*Planning complete: 2026-03-22*
*Executor model: Claude Sonnet 4.6 (recommended)*
*Estimated total duration: 70-100 minutes (3 plans, 12 tasks, parallel waves)*
