# Phase 4: Guided Deletion - Research

**Researched:** 2026-03-22
**Domain:** File deletion orchestration, safe workflows, undo recovery
**Confidence:** HIGH

## Summary

Phase 4 implements two distinct deletion workflows triggered by an existing report file, with comprehensive safety mechanisms. The delete operation is **always a separate, deliberate command** (never chained to scan), reads deletion candidates from a CSV/JSON report, and logs every deletion before execution for auditability. Mode A enforces per-file confirmation; Mode B requires explicit "type DELETE" acknowledgment before batch execution. Read-only filesystem detection prevents accidents on protected drives.

**Primary recommendation:** Implement deletion as a standalone `--delete-from report.csv` entry point in CLI, add a Deletion orchestrator module that handles Mode A (interactive per-file) and Mode B (workflow batch) workflows, add UndoEntry dataclass and UndoLog writer, and wire health check read-only detection into deletion warnings.

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Deletion is always a **standalone command** — `python3 -m diskcomp --delete-from report.csv`
- **D-02:** No auto-chaining after scan. Scan produces a report; deletion is a separate, deliberate step.
- **D-03:** Mode is selected at CLI time or via a prompt after loading the report (DEL-04 runtime selection)
- **D-04:** Each file prompt shows: both paths (keep_path + other_path), file size, and "SHA256 verified match" confirmation
- **D-05:** Running total of space freed is shown after each deletion (updates in-line)
- **D-06:** Per-file options are: **y** (delete), **n** (keep/skip this file), **skip** (defer, come back later), **abort** (stop entire workflow)
- **D-07:** No "delete all remaining" shortcut — every file requires individual confirmation in Mode A
- **D-08:** Flow is: dry-run preview → summary → "type DELETE to confirm" → execute (as per DEL-03)
- **D-09:** Progress shown during execution with running space-freed total (DEL-07)
- **D-10:** On abort mid-execution: report how many files were deleted before abort, print undo log path, exit cleanly — no automatic restore attempt
- **D-11:** **Hard delete** — files are permanently removed (no trash/recycle bin). Zero dependencies, fully cross-platform.
- **D-12:** Undo log is written **before** each file is deleted — JSON format with path, size_mb, hash, deleted_at timestamp
- **D-13:** Undo log is written **next to the report file** — `diskcomp-undo-YYYYMMDD-HHMMSS.json` in the same directory
- **D-14:** `--undo [log-file]` reads the undo log and shows what was deleted (audit view) — it does NOT restore files (hard delete is permanent)
- **D-15:** `--undo` output should be clear that restore is not possible: "These files were permanently deleted."
- **D-16:** Ctrl+C / abort during Mode B shows: "Aborted. N files deleted (X MB freed) before abort. Undo log: path/to/undo.json. Remaining N files were not deleted." Then exits cleanly.
- **D-17:** Partial progress is acceptable — undo log always reflects what was actually deleted up to the abort point
- **D-18:** If `--delete-from` is invoked on a report where the other drive is read-only or NTFS-on-macOS, warn the user and skip deletion for those files (DEL-08). Fix instructions from Phase 3 can be referenced.

### Claude's Discretion

- Exact progress bar implementation (use existing UIHandler from Phase 2 — Rich or ANSI)
- How Mode A presents the "skip" queue (save for later in session, or just note in log)
- Exact formatting of the Mode B dry-run preview
- Exit codes (0 for clean completion/abort, 1 for error)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DEL-01 | Deletion only starts from an existing report — never from scan results directly | Report reader module required; CLI `--delete-from` flag validates file exists |
| DEL-02 | Mode A (interactive): presents each duplicate, user confirms y/n/skip/abort per file | Deletion orchestrator handles per-file loop with confirmation prompts |
| DEL-03 | Mode B (workflow): dry-run preview → summary → "type DELETE to confirm" → execute | Workflow orchestrator collects files, shows summary, checks confirmation string match |
| DEL-04 | User selects deletion mode at runtime, or can skip deletion entirely | CLI prompt after report load: "Delete files? (interactive/batch/skip)" |
| DEL-05 | Undo log written before any file is deleted: path, size, hash, timestamp | UndoEntry dataclass + UndoLog writer (atomic writes like ReportWriter) |
| DEL-06 | `--undo` flag reads undo log and restores files from trash/recycle bin where possible | Audit view only per D-14/D-15; no restore attempted (hard delete is permanent) |
| DEL-07 | Progress shown during deletion with running total of space freed | UIHandler callbacks similar to scan/hash; progress bar tracks MB freed |
| DEL-08 | NTFS/read-only filesystem detection — warns user and skips deletion if drive is read-only | Reuse health.py get_fix_instructions() and is_writable checks |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| os (stdlib) | 3.8+ | Hard file deletion via os.remove() | Zero dependencies, cross-platform, consistent with codebase decisions |
| json (stdlib) | 3.8+ | Undo log serialization and `--undo` audit reads | Used already in reporter.py for JSON reports |
| csv (stdlib) | 3.8+ | Report reading (existing report.csv) | Used already in reporter.py for CSV reading |

### Supporting (Already Wired)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| diskcomp.types | (project) | New UndoEntry dataclass, DeletionResult return type | Consistency with existing @dataclass pattern |
| diskcomp.ui | (project) | Progress bar display for deletion progress | Reuse existing UIHandler (Rich/ANSI fallback) |
| diskcomp.health | (project) | get_fix_instructions() for read-only warnings | Integrate into deletion warnings (D-18) |
| diskcomp.reporter | (project) | ReportReader pattern for loading existing reports | New reader needed; write_csv/write_json already exist |

### Installation

```bash
# No new dependencies required
# Existing diskcomp package structure continues
```

## Architecture Patterns

### Recommended Project Structure

```
diskcomp/
├── types.py              # Add UndoEntry, DeletionResult dataclasses
├── cli.py                # Add --delete-from and --undo flag handling
├── deletion.py           # NEW: DeletionOrchestrator, UndoLog, deletion logic
├── reporter.py           # Already exists; may need ReportReader class added
└── health.py             # Already exists; reuse get_fix_instructions()
```

### Pattern 1: Report Reader

**What:** Load a CSV or JSON report to extract deletion candidates

**When to use:** Before initiating any deletion workflow, validate the report format and extract `DELETE_FROM_OTHER` rows

**Example:**
```python
# diskcomp/reporter.py (add to existing file)
class ReportReader:
    """
    Reads CSV or JSON reports and extracts deletion candidates.

    Reports from Phase 1–3 contain columns: action, keep_path, other_path, size_mb, hash
    This reader filters for action == 'DELETE_FROM_OTHER' entries.
    """

    @staticmethod
    def load_csv(file_path: str) -> List[dict]:
        """
        Load CSV report and extract deletion candidates.

        Args:
            file_path: Path to report CSV file

        Returns:
            List of dicts with keys: action, keep_path, other_path, size_mb, hash

        Raises:
            FileNotFoundError: If report file doesn't exist
            ValueError: If report format is invalid
        """
        import csv
        candidates = []
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('action') == 'DELETE_FROM_OTHER':
                    candidates.append(row)
        return candidates

    @staticmethod
    def load_json(file_path: str) -> List[dict]:
        """Load JSON report and extract DELETE_FROM_OTHER entries."""
        import json
        with open(file_path, 'r') as f:
            data = json.load(f)
        # JSON format has 'duplicates' key with list of items
        return [item for item in data.get('duplicates', [])
                if item.get('action') == 'DELETE_FROM_OTHER']

    @staticmethod
    def load(file_path: str) -> List[dict]:
        """Auto-detect format and load."""
        if file_path.endswith('.json'):
            return ReportReader.load_json(file_path)
        else:
            return ReportReader.load_csv(file_path)
```

### Pattern 2: Deletion Orchestrator

**What:** Main deletion workflow state machine, handles both Mode A (interactive per-file) and Mode B (batch with confirmation)

**When to use:** After report is loaded and user selects deletion mode, orchestrator drives the workflow end-to-end

**Example:**
```python
# diskcomp/deletion.py (new file)
@dataclass
class DeletionResult:
    """Result of deletion workflow."""
    mode: str  # 'interactive' or 'batch'
    files_deleted: int
    space_freed_mb: float
    files_skipped: int
    aborted: bool
    undo_log_path: Optional[str]
    errors: List[str] = field(default_factory=list)

class DeletionOrchestrator:
    """
    Orchestrates safe file deletion with two modes:
    - Mode A (interactive): per-file confirmation, can skip individual files
    - Mode B (batch): dry-run preview → summary → type-to-confirm → execute
    """

    def __init__(self, candidates: List[dict], ui, report_path: str):
        """
        Args:
            candidates: List of dicts with {other_path, size_mb, hash, ...} to delete
            ui: UIHandler instance for progress display
            report_path: Path to original report (undo log written next to it)
        """
        self.candidates = candidates
        self.ui = ui
        self.report_dir = os.path.dirname(report_path)
        self.undo_log = UndoLog(self.report_dir)

    def interactive_mode(self) -> DeletionResult:
        """
        Mode A: Present each file, ask y/n/skip/abort.

        For each file:
        - Show: keep_path, other_path, size_mb, SHA256 hash verification
        - Prompt: (y)es, (n)o, (skip) for later, (abort) all
        - Update running total of space freed after each deletion
        - Build undo log as deletions occur
        """
        files_deleted = 0
        space_freed = 0.0
        skipped = []

        for i, candidate in enumerate(self.candidates):
            other_path = candidate['other_path']
            size_mb = float(candidate['size_mb'])
            file_hash = candidate['hash']

            # Prompt user
            prompt = f"\n[{i+1}/{len(self.candidates)}] Delete?"
            prompt += f"\n  Path: {other_path}"
            prompt += f"\n  Size: {size_mb} MB"
            prompt += f"\n  Hash: {file_hash[:16]}... (verified match)"
            prompt += f"\nSpace freed so far: {space_freed:.2f} MB"
            prompt += "\n(y)es, (n)o, (skip), (abort)? "

            choice = input(prompt).strip().lower()

            if choice == 'abort':
                return DeletionResult(
                    mode='interactive',
                    files_deleted=files_deleted,
                    space_freed_mb=space_freed,
                    files_skipped=len(skipped),
                    aborted=True,
                    undo_log_path=self.undo_log.file_path
                )
            elif choice == 'skip':
                skipped.append(candidate)
            elif choice in ['y', 'yes']:
                # Delete and log before removal
                self.undo_log.add(
                    path=other_path,
                    size_mb=size_mb,
                    hash=file_hash
                )
                os.remove(other_path)
                files_deleted += 1
                space_freed += size_mb
                print(f"  Deleted. Space freed: {space_freed:.2f} MB", file=sys.stderr)
            # else: choice == 'no', continue to next

        # Write final undo log
        self.undo_log.write()

        return DeletionResult(
            mode='interactive',
            files_deleted=files_deleted,
            space_freed_mb=space_freed,
            files_skipped=len(skipped),
            aborted=False,
            undo_log_path=self.undo_log.file_path
        )

    def batch_mode(self) -> DeletionResult:
        """
        Mode B: dry-run preview → summary → type DELETE to confirm → execute.

        1. Show dry-run summary (file count, total MB, sample files)
        2. Print "Type DELETE to proceed, or Ctrl+C to abort"
        3. On confirmation match, execute deletions with progress bar
        4. Write undo log as files are deleted
        """
        # 1. Dry-run preview
        total_mb = sum(float(c['size_mb']) for c in self.candidates)
        print(f"\n=== Deletion Preview (Batch Mode) ===", file=sys.stderr)
        print(f"Files to delete: {len(self.candidates)}", file=sys.stderr)
        print(f"Space to free: {total_mb:.2f} MB", file=sys.stderr)

        if len(self.candidates) <= 5:
            print("\nFiles:", file=sys.stderr)
            for c in self.candidates:
                print(f"  - {c['other_path']} ({c['size_mb']} MB)", file=sys.stderr)
        else:
            print("\nFirst 5 files:", file=sys.stderr)
            for c in self.candidates[:5]:
                print(f"  - {c['other_path']} ({c['size_mb']} MB)", file=sys.stderr)
            print(f"  ... and {len(self.candidates) - 5} more", file=sys.stderr)

        # 2. Confirmation prompt
        confirm = input(f"\nType DELETE to proceed, or Ctrl+C to abort: ").strip()
        if confirm != "DELETE":
            return DeletionResult(
                mode='batch',
                files_deleted=0,
                space_freed_mb=0.0,
                files_skipped=len(self.candidates),
                aborted=True,
                undo_log_path=None
            )

        # 3. Execute deletions with progress
        files_deleted = 0
        space_freed = 0.0

        self.ui.start_deletion(len(self.candidates))

        for i, candidate in enumerate(self.candidates):
            try:
                other_path = candidate['other_path']
                size_mb = float(candidate['size_mb'])
                file_hash = candidate['hash']

                # Log before deletion
                self.undo_log.add(
                    path=other_path,
                    size_mb=size_mb,
                    hash=file_hash
                )

                # Delete
                os.remove(other_path)
                files_deleted += 1
                space_freed += size_mb

                # Update progress
                self.ui.on_file_deleted(i+1, len(self.candidates), space_freed)
            except Exception as e:
                # Log error but continue
                pass

        self.ui.close()
        self.undo_log.write()

        return DeletionResult(
            mode='batch',
            files_deleted=files_deleted,
            space_freed_mb=space_freed,
            files_skipped=len(self.candidates) - files_deleted,
            aborted=False,
            undo_log_path=self.undo_log.file_path
        )
```

### Pattern 3: UndoLog Writer

**What:** Write deletion record to JSON before each file deletion, enable `--undo` audit view

**When to use:** Before removing each file (in both modes), serialize deletion metadata

**Example:**
```python
# diskcomp/deletion.py (add to file)
@dataclass
class UndoEntry:
    """Single file deletion record."""
    path: str
    size_mb: float
    hash: str
    deleted_at: str  # ISO timestamp

class UndoLog:
    """
    Atomic undo log writer.

    Entries are appended as deletions occur. File is written atomically
    (same temp → rename pattern as ReportWriter) when finalized.
    """

    def __init__(self, report_dir: str):
        """
        Args:
            report_dir: Directory next to report file
        """
        self.report_dir = report_dir
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.file_path = os.path.join(report_dir, f"diskcomp-undo-{timestamp}.json")
        self.entries: List[UndoEntry] = []

    def add(self, path: str, size_mb: float, hash: str):
        """Record a file deletion (before actual deletion)."""
        self.entries.append(UndoEntry(
            path=path,
            size_mb=size_mb,
            hash=hash,
            deleted_at=datetime.now().isoformat()
        ))

    def write(self):
        """Write undo log atomically."""
        def writer_func(f):
            json.dump(
                [asdict(e) for e in self.entries],
                f,
                indent=2
            )

        target_dir = os.path.dirname(self.file_path) or '.'
        with tempfile.NamedTemporaryFile(
            mode='w', dir=target_dir, delete=False, suffix='.tmp'
        ) as tmp_file:
            tmp_path = tmp_file.name
            try:
                writer_func(tmp_file)
                tmp_file.flush()
            except Exception:
                os.unlink(tmp_path)
                raise
        os.rename(tmp_path, self.file_path)
```

### Pattern 4: CLI Integration

**What:** Add `--delete-from` and `--undo` flags, implement deletion entry point

**When to use:** When user invokes `diskcomp --delete-from report.csv` or `diskcomp --undo log.json`

**Example:**
```python
# diskcomp/cli.py (add to parse_args)
parser.add_argument(
    '--delete-from',
    type=str,
    default=None,
    help='Delete duplicates from an existing report CSV/JSON file'
)

parser.add_argument(
    '--undo',
    type=str,
    default=None,
    help='View audit log of deleted files (permanent; restore not possible)'
)

# In main() function, after parse_args:
if args.undo:
    # Audit view only
    _show_undo_log(args.undo)
    return 0

if args.delete_from:
    # Deletion workflow
    if not os.path.isfile(args.delete_from):
        print(f"Error: Report file not found: {args.delete_from}", file=sys.stderr)
        return 1

    # Load candidates
    from diskcomp.reporter import ReportReader
    try:
        candidates = ReportReader.load(args.delete_from)
    except Exception as e:
        print(f"Error reading report: {e}", file=sys.stderr)
        return 1

    if not candidates:
        print("No files marked for deletion in this report.", file=sys.stderr)
        return 0

    # Check read-only drives
    other_paths = [c['other_path'] for c in candidates]
    _check_deletion_readiness(other_paths)

    # Prompt for mode
    mode_choice = input("Deletion mode? (interactive/batch/skip): ").strip().lower()
    if mode_choice == 'skip':
        print("Deletion skipped.", file=sys.stderr)
        return 0

    mode = 'interactive' if mode_choice.startswith('i') else 'batch'

    # Orchestrate
    ui = UIHandler.create()
    orchestrator = DeletionOrchestrator(candidates, ui, args.delete_from)

    try:
        if mode == 'interactive':
            result = orchestrator.interactive_mode()
        else:
            result = orchestrator.batch_mode()

        print(f"\nDeleted: {result.files_deleted} files ({result.space_freed_mb:.2f} MB)", file=sys.stderr)
        if result.undo_log_path:
            print(f"Undo log: {result.undo_log_path}", file=sys.stderr)

        if result.aborted:
            print(f"Aborted. {len(self.candidates) - result.files_deleted} files remain.", file=sys.stderr)

    except KeyboardInterrupt:
        print(f"\n^C Aborted. {result.files_deleted} files deleted before abort.", file=sys.stderr)
        print(f"Undo log: {result.undo_log_path}", file=sys.stderr)
        return 0

    return 0
```

### Anti-Patterns to Avoid

- **Auto-chaining deletion after scan:** D-02 explicitly forbids this. Deletion must always be manual.
- **Silent skipping of files without logging:** Every skipped file (from Mode A or read-only drives) must be visible in the undo log or output.
- **Using os.remove() without validation:** Always verify file hash against report before deletion to prevent accidental removal of wrong files.
- **Undo log written after deletions:** D-12 requires undo log entry **before** each deletion. If process crashes mid-deletion, undo log must be complete for what was actually deleted.
- **Mixing deletion modes:** Don't let user switch mid-workflow. Commit to one mode per invocation.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Report parsing | Custom CSV parser | csv (stdlib) + ReportReader class | Handles quoting, escaping, multi-line fields correctly |
| Progress display | Custom progress bar | UIHandler (existing) + Rich/ANSI fallback | Already wired in Phase 2; Rich handles real-time updates |
| File deletion recovery | Custom trash/recycle bin logic | Hard delete + undo audit log | Cross-platform trash APIs unreliable; permanent deletion + audit is the approved pattern |
| Atomic file writes | Direct file writes | tempfile + rename pattern | Prevents partial/corrupted undo log on crash (ReportWriter pattern proven) |
| Read-only detection | Custom subprocess calls | health.py get_fix_instructions() | Already handles cross-platform read-only checks and remount guidance |

**Key insight:** Deletion is deceptively simple (os.remove is one line), but the safety workflow around it is complex. The user's core requirement is "no surprises and always reversible via audit" — this comes from orchestration, not file operations.

## Common Pitfalls

### Pitfall 1: Hard Delete Without Undo Log Written First

**What goes wrong:** Deletion proceeds, then undo log write fails (permission, disk full). Audit trail is incomplete.

**Why it happens:** Sequencing — write after delete to save on disk if deletion fails, but violates D-12.

**How to avoid:** Always write UndoEntry before os.remove(). If deletion fails, log the error but undo entry is already recorded. Undo log is a **pre-flight checklist**, not a post-flight report.

**Warning signs:** Testing in batch mode — delete a file, then kill the process before undo log write completes. Result: file gone, undo log missing or partial.

### Pitfall 2: Forgetting to Check Read-Only Status Before Deletion

**What goes wrong:** User selects `--delete-from` report on a drive with read-only "other" files. Deletion silently fails for some files, user thinks all were deleted.

**Why it happens:** D-18 asks to warn, but doesn't enforce skip. Different implementations interpret "warn and skip" as "proceed and fail silently."

**How to avoid:** In DeletionOrchestrator.__init__(), check each candidate's other_path against health check results (or re-check os.access()). Build a **deleted**, **skipped_readonly**, **skipped_error** partition upfront. Only add deletable files to workflow.

**Warning signs:** Mode B dry-run shows 50 files, but undo log has 30. Check stderr for read-only warnings.

### Pitfall 3: Missing Per-File Hash Verification

**What goes wrong:** Report lists file path + hash, but deletion just trusts the path. File was moved or replaced; wrong file deleted.

**Why it happens:** D-04 says to show "SHA256 verified match," but easy to skip actual verification in code.

**How to avoid:** Before os.remove(), compute hash of the file on disk and compare against report's hash. Only proceed if match. If hash mismatch, skip and log warning.

**Warning signs:** Integration test: create a file, run scan, modify the file, run `--delete-from` report → should skip the file because hash no longer matches.

### Pitfall 4: Undo Log Showing Files That Were Never Deleted

**What goes wrong:** Undo log lists 50 files deleted, but only 30 were actually removed (others were skipped/errored).

**Why it happens:** UndoLog.add() called for every candidate, regardless of deletion success.

**How to avoid:** Call undo_log.add() **only after** os.remove() succeeds. Wrap in try/except and skip log entry if deletion fails.

**Warning signs:** User runs `--undo log.json`, sees 50 entries, but disk still has 20 of those files.

## Code Examples

Verified patterns from existing codebase:

### Atomic File Write Pattern (from ReportWriter)

```python
# Source: diskcomp/reporter.py
def _write_atomic(self, file_path: str, content_writer) -> None:
    """
    Write content to a file atomically using temp → rename pattern.
    """
    target_dir = os.path.dirname(file_path) or '.'
    try:
        with tempfile.NamedTemporaryFile(
            mode='w',
            dir=target_dir,
            delete=False,
            suffix='.tmp'
        ) as tmp_file:
            tmp_path = tmp_file.name
            try:
                content_writer(tmp_file)
                tmp_file.flush()
            except Exception:
                os.unlink(tmp_path)
                raise
        os.rename(tmp_path, file_path)
```

**Deletion.py should use identical pattern for UndoLog.write()** to maintain consistency.

### UIHandler Progress Pattern (from Phase 2)

```python
# Source: diskcomp/ui.py
def start_hash(self, total_files: int):
    """Start hash progress display."""
    if not self.progress_context:
        self.progress_context = self.progress.__enter__()
    self.hash_task_id = self.progress_context.add_task(
        "[cyan]Hashing files...",
        total=total_files
    )

def on_file_hashed(self, current: int, total: int, speed_mbps: float, eta_secs: Optional[int] = None):
    """Update hash progress after hashing a file."""
    if self.progress_context and self.hash_task_id is not None:
        self.progress_context.update(
            self.hash_task_id,
            completed=current
        )
```

**Deletion.py should add similar methods to UIHandler:**
- `start_deletion(total_files)` — initialize progress task
- `on_file_deleted(current, total, space_freed_mb)` — update progress with running MB total

### Health Check Fix Instructions (from Phase 3)

```python
# Source: diskcomp/health.py
def get_fix_instructions(fstype: str, platform: str, mount_point: str) -> str:
    """Return platform and filesystem-specific remediation instructions."""
    fstype_upper = fstype.upper()

    if fstype_upper == 'NTFS' and platform == 'darwin':
        return "Install macFUSE and NTFS-3G: `brew install macfuse ntfs-3g`..."
    # ... more cases
```

**Deletion.py should call this when building read-only warnings:**
```python
other_health = check_drive_health(other_drive_root)
if not other_health.is_writable:
    fix = get_fix_instructions(other_health.fstype, sys.platform, other_drive_root)
    print(f"⚠️  Other drive is read-only. {fix}", file=sys.stderr)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Recycle bin / trash recovery | Hard delete + audit log | Phase 4 design | Simpler cross-platform, clear "permanent" semantics, audit trail always intact |
| Per-file deletion in Mode A | Interactive y/n/skip/abort loop | CONTEXT.md D-06/D-07 | Safer UX — no "delete all remaining" shortcut that could be activated by accident |
| Deletion output silent or minimal | Running total shown after each file (Mode A) and full progress bar (Mode B) | CONTEXT.md D-05/D-09 | User always knows how much space freed so far; no surprise at the end |

**Deprecated/outdated:**
- Auto-chaining deletion after scan: D-02 reverses earlier designs that would delete immediately after scan.
- Recycle bin / trash integration: Phase 4 design (D-11) chose hard delete for simplicity; recovery is audit-view only.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | unittest (stdlib) |
| Config file | none — see Wave 0 |
| Quick run command | `pytest tests/test_deletion.py::test_interactive_mode -x` |
| Full suite command | `pytest tests/test_deletion.py -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEL-01 | Report file required, error if missing | unit | `pytest tests/test_deletion.py::test_delete_from_missing_report -x` | ❌ Wave 0 |
| DEL-02 | Interactive mode shows each file with prompt | unit | `pytest tests/test_deletion.py::test_interactive_per_file -x` | ❌ Wave 0 |
| DEL-03 | Batch mode: dry-run → confirm → execute | unit | `pytest tests/test_deletion.py::test_batch_workflow -x` | ❌ Wave 0 |
| DEL-04 | Runtime mode selection prompt | integration | `pytest tests/test_integration.py::test_delete_mode_selection -x` | ❌ Wave 0 |
| DEL-05 | Running total shown after each deletion (Mode A) | integration | Manual: run interactive mode, verify space freed updates | ❌ Wave 0 |
| DEL-06 | `--undo` reads log, shows audit, no restore | unit | `pytest tests/test_deletion.py::test_undo_audit_view -x` | ❌ Wave 0 |
| DEL-07 | Progress bar during batch deletion | integration | Manual: run batch mode, verify progress bar appears | ❌ Wave 0 |
| DEL-08 | Read-only warning + skip | unit | `pytest tests/test_deletion.py::test_readonly_skip -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** Quick run command (1–2 requirements per test)
- **Per wave merge:** Full suite command (`test_deletion.py` + `test_integration.py` deletion tests)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_deletion.py` — covers REQ-DEL-01 through DEL-06 (undo log, report reader, orchestrator)
- [ ] `tests/test_integration.py` additions — covers DEL-04, DEL-07, DEL-08 (CLI integration, read-only detection, progress)
- [ ] Modifications to UIHandler in `diskcomp/ui.py` — add deletion progress methods (start_deletion, on_file_deleted)
- [ ] ReportReader class in `diskcomp/reporter.py` — load CSV/JSON reports, filter for DELETE_FROM_OTHER
- [ ] New dataclasses in `diskcomp/types.py` — UndoEntry, DeletionResult

*(If any gaps existed: "None — existing test infrastructure covers all phase requirements")*

## Sources

### Primary (HIGH confidence)
- CONTEXT.md (Phase 4 discussion) - Locked decisions (D-01 through D-18) and all CLI/workflow requirements
- REQUIREMENTS.md (DEL-01 through DEL-08) - Authoritative requirement set
- STATE.md (Phase 3 completion summary) - Existing codebase status, all 120 tests passing

### Secondary (HIGH confidence)
- diskcomp/types.py - Existing @dataclass pattern (FileRecord, ScanResult, DriveInfo, HealthCheckResult, BenchmarkResult)
- diskcomp/reporter.py - ReportWriter atomic write pattern (temp → rename), CSV/JSON formats
- diskcomp/cli.py - Parse_args structure, main() orchestration, UIHandler integration
- diskcomp/health.py - get_fix_instructions() function (available for read-only warnings)
- diskcomp/ui.py - UIHandler factory, RichProgressUI/ANSIProgressUI interface

### Tertiary (LOW confidence - no external sources needed)
- None — all context sourced from CONTEXT.md, REQUIREMENTS.md, and existing codebase

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — stdlib only, zero new dependencies; patterns from Phase 1–3 code verified
- Architecture: **HIGH** — DeletionOrchestrator, UndoLog, ReportReader are straightforward; integration points clear from existing CLI structure
- Pitfalls: **MEDIUM** — Based on common file deletion patterns, but this project has unique "permanent + audit" semantics (not trash-based), so some pitfalls are project-specific

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (30 days — stack is stable, but user may refine UX based on Phase 4 implementation)

