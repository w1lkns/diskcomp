# Phase 7: UX Polish + Single-Drive Mode - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Make diskcomp feel like a product, not a script. Three improvements: (1) a first-run wizard that greets new users with a numbered menu before asking anything technical, (2) plain-language output after every scan so users understand results without reading CSV, and (3) a `--single <path>` mode that finds duplicates within one drive and hands off to the existing safe deletion workflow. No new deletion safety model — all existing guarantees (undo log, dry-run, per-file confirmation) carry over unchanged.

</domain>

<decisions>
## Implementation Decisions

### Single-Drive Dedup

- **D-01:** `--single <path>` scans one drive, groups files by SHA256 hash, and marks all but one copy per group as DELETE. The **alphabetically first path** (lexicographic sort) is the "keep" — deterministic, reproducible, no extra I/O.
- **D-02:** Single-drive results feed directly into the existing guided deletion workflow (same `DeletionOrchestrator`, same undo log, same interactive/batch modes). No new deletion code needed.
- **D-03:** Size filter (`filter_by_size_collision`) does not apply in single-drive mode — there is only one drive. Instead, use a simpler group-by-size-first pass within the single drive: skip sizes that appear only once, hash only size-collision candidates. Same speedup principle, different implementation.

### Startup Banner

- **D-04:** Banner shown in interactive (no-args) mode only — not when flags are passed directly (e.g. `--keep` / `--other` / `--single`). No banner on `--help`.
- **D-05:** Tagline: **"Find duplicates. Free space. Stay safe."**
- **D-06:** Banner includes: ASCII art `diskcomp` logo + tagline + version string (read from `importlib.metadata` with fallback to hardcoded `"1.1.0"` for single-file builds).

### First-Run Wizard

- **D-07:** Main menu options: `1) Compare two drives`, `2) Clean up a single drive`, `3) Help`, `4) Quit`.
- **D-08:** Selecting `1) Compare two drives` passes through to the existing `interactive_drive_picker()` → health checks → scan flow. No new layer.
- **D-09:** Selecting `2) Clean up a single drive` prompts for a single path, runs health check, then scan + single-drive dedup.
- **D-10:** Selecting `3) Help` displays a wizard-style quick guide (plain English: what diskcomp does, the 2 modes, 3 safety facts), then returns to the main menu.
- **D-11:** Selecting `4) Quit` exits cleanly with code 0.

### --min-size Flag

- **D-12:** Accepted formats: case-insensitive suffix (`500KB`, `10mb`, `1GB`, `1.5MB`) or plain integer (bytes: `1024`). Units: B, KB, MB, GB.
- **D-13:** CLI flag (`--min-size abc`): print a clear error message and exit 1. No silent fallback.
- **D-14:** Interactive wizard prompt ("Skip files smaller than? [1KB]"): on invalid input, show an error and **prompt again** (retry loop, not exit). Only exits on valid input or blank (uses default).
- **D-15:** `--min-size 0` is valid — sets no floor (hash all files regardless of size). Existing 1KB default is used when flag is absent.

### Plain-Language Results Summary

- **D-16:** After every scan (two-drive and single-drive), before mentioning the CSV path, show: `"Found {N} duplicates. You could free {X} GB from {drive_label}. Ready to review?"`. Use MB if < 1 GB.
- **D-17:** If 0 duplicates found: `"No duplicates found. Both drives are already clean."` (two-drive) or `"No duplicates found. This drive has no redundant files."` (single-drive).

### Post-Scan Next Steps

- **D-18:** After every scan that produces a report, print a "Next steps" block with the actual generated report filename:
  ```
  ── Next steps ──────────────────────────────────────────
  Review:  cat {report_path}
  Delete:  diskcomp --delete-from {report_path}
  Undo:    diskcomp --undo {undo_log_path_hint}
  ────────────────────────────────────────────────────────
  ```
  Undo log path hint: show the default location pattern (e.g. `~/diskcomp-undo-YYYYMMDD.json`).

### NTFS + README

- **D-19:** In health check output, when fstype is NTFS and platform is macOS/Linux, show a named callout: `"⚠ NTFS on macOS: This drive is read-only. Files cannot be deleted from it here."` with fix instructions already implemented by Phase 3 (`get_fix_instructions()`).
- **D-20:** README: add a "Known Limitations" section noting NTFS-on-macOS read-only limitation and linking to fix instructions.

### Preserved Decisions (from prior phases)

- **D-21:** `--keep` / `--other` flag names retained as-is. No aliases added.
- **D-22:** Pre-deletion summary (duplicates found, MB recoverable) already shown via `show_summary()` in the UI — this phase ensures it's shown before any deletion prompt, not just in the report.

### Claude's Discretion

- Exact ASCII art rendering (Python `textwrap` or hardcoded string — choose based on column width compatibility)
- Internal module structure for wizard logic (new `wizard.py` vs inline in `cli.py` — choose based on size)
- Exact wording of the wizard quick guide help text
- Unit test structure for single-drive dedup (new `test_single_drive.py` vs extend `test_integration.py`)

### Folded Todos

- **03-04-PLAN.md gap-closure TODO** (from ROADMAP.md): already complete (completed 2026-03-22, status: COMPLETE). No action needed in this phase.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Core pipeline files
- `diskcomp/cli.py` — `main()` orchestration, `parse_args()`, interactive mode detection, `display_health_checks()`, `_display_health_result()`
- `diskcomp/ui.py` — `UIHandler` factory, `RichProgressUI`, `ANSIProgressUI`, `show_summary()`
- `diskcomp/drive_picker.py` — `interactive_drive_picker()` (existing two-drive picker to reuse for "Compare two drives" wizard option)
- `diskcomp/hasher.py` — `FileHasher.hash_files()`, `filter_by_size_collision()` (two-drive version — DO NOT reuse for single-drive; implement a single-drive variant)
- `diskcomp/scanner.py` — `FileScanner.scan()`, `FileRecord` with `size_bytes`
- `diskcomp/health.py` — `check_drive_health()`, `get_fix_instructions()` (already handles NTFS-on-macOS)
- `diskcomp/deletion.py` — `DeletionOrchestrator` (reuse unchanged for single-drive deletion handoff)
- `diskcomp/reporter.py` — `ReportWriter`, `DuplicateClassifier`, `ReportReader`
- `diskcomp/types.py` — `FileRecord`, `UndoEntry`, `DeletionResult`

### Roadmap
- `.planning/ROADMAP.md` §Phase 7 — all 9 success criteria (two-drive wizard, single-drive, plain language summary, next steps, NTFS callout, startup banner, --min-size)

### No external specs — requirements fully captured in decisions above

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `interactive_drive_picker()` in `drive_picker.py` — called as-is for "Compare two drives" wizard option; no changes needed
- `DeletionOrchestrator` in `deletion.py` — accepts `List[dict]` candidates from `ReportReader`; single-drive dedup can generate the same format and pass it directly
- `get_fix_instructions(fstype, platform, path)` in `health.py` — already returns NTFS-on-macOS fix text; just needs to be surfaced more prominently in the health check output
- `show_summary()` in `ui.py` — already shows duplicate count + MB; plain-language wrapper goes on top of this
- `UIHandler.create()` — already handles Rich/ANSI selection; banner uses same print/console pattern

### Established Patterns
- `@dataclass` contracts in `types.py` — any new struct (e.g. `WizardSelection`) should follow this pattern
- Zero mandatory dependencies — wizard, banner, `--min-size` parser must use stdlib only
- Python 3.8+ — no walrus operator, no `dict | dict` merge syntax, no `match` statement
- `input()` prompt loops — existing pattern in `cli.py` (benchmark retry, deletion mode prompt) — reuse for `--min-size` retry in wizard
- Graceful error handling — never crash; all new paths must handle `KeyboardInterrupt` and fall back cleanly

### Integration Points
- `main()` in `cli.py` — wizard triggers when no args provided (`if not args.keep and not args.other and not args.delete_from and not args.undo`); banner shown at top of this branch
- Post-scan next steps block — inserted after `ui.show_summary()` call, before `ui.close()`
- `--single <path>` — new flag in `parse_args()`; handled as a separate branch in `main()` before the two-drive scan logic
- `--min-size <value>` — new flag in `parse_args()`; passed as `min_size_bytes` to `FileScanner.scan()` (already accepts `min_size_bytes` parameter)

</code_context>

<specifics>
## Specific Ideas

- Tagline exact copy: **"Find duplicates. Free space. Stay safe."**
- Plain-language summary format: `"Found {N} duplicates. You could free {X:.1f} GB from {drive_label}. Ready to review?"` — use `{X:.1f} MB` when < 1000 MB
- Next steps block uses actual generated report path (from `writer.output_path`)
- Startup banner only in no-args interactive mode (not `--keep`/`--other`/`--single`)
- Single-drive keep rule: alphabetically first path (lexicographic sort within each hash group)
- `--min-size` retry loop in interactive wizard; error+exit in CLI flag mode
- `--min-size 0` valid (no floor); absent = 1KB default

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 07-ux-polish-single-drive-mode*
*Context gathered: 2026-03-23*
