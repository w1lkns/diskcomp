# Phase 4: Guided Deletion - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Turn an existing scan report into safe file deletion. Two deletion modes, an undo log for auditability, and abort-at-any-time safety. Scanning is Phase 1–3 territory — deletion only operates on a saved report file, never on live scan results.

</domain>

<decisions>
## Implementation Decisions

### Deletion entry point
- **D-01:** Deletion is always a **standalone command** — `python3 -m diskcomp --delete-from report.csv`
- **D-02:** No auto-chaining after scan. Scan produces a report; deletion is a separate, deliberate step.
- **D-03:** Mode is selected at CLI time or via a prompt after loading the report (DEL-04 runtime selection)

### Mode A per-file interaction
- **D-04:** Each file prompt shows: both paths (keep_path + other_path), file size, and "SHA256 verified match" confirmation
- **D-05:** Running total of space freed is shown after each deletion (updates in-line)
- **D-06:** Per-file options are: **y** (delete), **n** (keep/skip this file), **skip** (defer, come back later), **abort** (stop entire workflow)
- **D-07:** No "delete all remaining" shortcut — every file requires individual confirmation in Mode A

### Mode B workflow
- **D-08:** Flow is: dry-run preview → summary → "type DELETE to confirm" → execute (as per DEL-03)
- **D-09:** Progress shown during execution with running space-freed total (DEL-07)
- **D-10:** On abort mid-execution: report how many files were deleted before abort, print undo log path, exit cleanly — no automatic restore attempt

### Undo / recovery model
- **D-11:** **Hard delete** — files are permanently removed (no trash/recycle bin). Zero dependencies, fully cross-platform.
- **D-12:** Undo log is written **before** each file is deleted — JSON format with path, size_mb, hash, deleted_at timestamp
- **D-13:** Undo log is written **next to the report file** — `diskcomp-undo-YYYYMMDD-HHMMSS.json` in the same directory
- **D-14:** `--undo [log-file]` reads the undo log and shows what was deleted (audit view) — it does NOT restore files (hard delete is permanent)
- **D-15:** `--undo` output should be clear that restore is not possible: "These files were permanently deleted."

### Abort behavior
- **D-16:** Ctrl+C / abort during Mode B shows: "Aborted. N files deleted (X MB freed) before abort. Undo log: path/to/undo.json. Remaining N files were not deleted." Then exits cleanly.
- **D-17:** Partial progress is acceptable — undo log always reflects what was actually deleted up to the abort point

### Read-only / NTFS protection
- **D-18:** If `--delete-from` is invoked on a report where the other drive is read-only or NTFS-on-macOS, warn the user and skip deletion for those files (DEL-08). Fix instructions from Phase 3 can be referenced.

### Claude's Discretion
- Exact progress bar implementation (use existing UIHandler from Phase 2 — Rich or ANSI)
- How Mode A presents the "skip" queue (save for later in session, or just note in log)
- Exact formatting of the Mode B dry-run preview
- Exit codes (0 for clean completion/abort, 1 for error)

</decisions>

<specifics>
## Specific Ideas

- The abort output mockup user approved: `"^C Aborted. 12 files deleted before abort. Undo log: ~/diskcomp-report-undo.json. Remaining 30 files were not deleted."`
- `--undo` is explicitly an **audit trail**, not a recovery tool — make this clear in the output
- Mode A must feel deliberate: no shortcuts that bypass per-file confirmation

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Deletion requirements
- `.planning/REQUIREMENTS.md` §Guided Deletion — DEL-01 through DEL-08, the complete requirement set for this phase
- `.planning/PROJECT.md` §Key Decisions — "Undo log over recycle bin" rationale (cross-platform recycle bin APIs unreliable)

### Existing code to build on
- `diskcomp/reporter.py` — Report format: rows with action (`DELETE_FROM_OTHER`, `UNIQUE_IN_OTHER`, `UNIQUE_IN_KEEP`), keep_path, other_path, size_mb, hash
- `diskcomp/types.py` — Existing dataclasses (FileRecord, ScanResult, DriveInfo, HealthCheckResult, BenchmarkResult)
- `diskcomp/cli.py` — Existing CLI structure, argparse setup, UIHandler wiring — deletion flag goes here
- `diskcomp/ui.py` — UIHandler factory (Rich vs ANSI), reuse for deletion progress display
- `diskcomp/health.py` — `get_fix_instructions()` — available for referencing NTFS/read-only fix guidance in deletion warnings

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `UIHandler` (ui.py): Factory pattern returns RichProgressUI or ANSIProgressUI — use for deletion progress bar
- `reporter.py` CSV/JSON reader: Need to add a report *reader* (currently only writes) — planner should plan this
- `health.py` `get_fix_instructions()`: Can surface NTFS fix guidance when deletion is blocked by read-only

### Established Patterns
- Zero mandatory dependencies — deletion module must use stdlib only (os.remove, json, csv)
- @dataclass contracts in types.py — new deletion types (UndoEntry, DeletionResult) should follow this pattern
- Graceful error handling: never crash, return results even on warnings — maintain this in deletion
- Atomic writes: existing reporter uses temp file → rename — use same pattern for undo log writes

### Integration Points
- `cli.py` `parse_args()`: Add `--delete-from` and `--undo` flags here
- `cli.py` `main()`: New branch — if `--delete-from` present, enter deletion workflow instead of scan
- Report CSV: Deletion reads `action == 'DELETE_FROM_OTHER'` rows from the existing report format
- Undo log: New JSON file; `--undo` flag reads it

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-guided-deletion*
*Context gathered: 2026-03-22*
