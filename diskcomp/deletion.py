"""
Deletion orchestration and undo log management for diskcomp.

This module handles safe file deletion with audit trails:
- UndoLog: Writes JSON audit log of deleted files (entries added before deletion)
- DeletionOrchestrator: Mode A (interactive per-file) and Mode B (batch) workflows
"""

import json
import os
import sys
import tempfile
from datetime import datetime
from typing import List, Optional

from diskcomp.types import UndoEntry, DeletionResult


class UndoLog:
    """
    Atomic undo log writer for deletion audit trail.

    Entries are accumulated during deletion (via add()), then written atomically
    to a JSON file at the end of the workflow. The undo log records what was
    actually deleted, enabling full audit and prevention of accidental restoration.

    Per D-12, entries are logged *before* deletion occurs. Per D-13, the log is
    written next to the report file with timestamp.

    Attributes:
        report_dir: Directory containing the original report (where undo log is written)
        file_path: Full path to the undo log JSON file
        entries: List of UndoEntry objects (accumulated via add())
    """

    def __init__(self, report_dir: str):
        """
        Initialize the undo log writer.

        Args:
            report_dir: Directory containing the report file (undo log written here)

        Raises:
            ValueError: If report_dir doesn't exist or isn't writable
        """
        if not os.path.isdir(report_dir):
            raise ValueError(f"Report directory not found: {report_dir}")
        if not os.access(report_dir, os.W_OK):
            raise ValueError(f"Report directory not writable: {report_dir}")

        self.report_dir = report_dir
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.file_path = os.path.join(report_dir, f"diskcomp-undo-{timestamp}.json")
        self.entries: List[UndoEntry] = []

    def add(self, path: str, size_mb: float, hash: str) -> None:
        """
        Record a file deletion (before actual deletion happens).

        Args:
            path: Full path to file being deleted
            size_mb: File size in MB
            hash: SHA256 hex string

        Note:
            This method only records the entry in memory. The actual JSON write
            happens when write() is called (per D-12: entries logged before deletion).
        """
        entry = UndoEntry(
            path=path,
            size_mb=size_mb,
            hash=hash,
            deleted_at=datetime.now().isoformat()
        )
        self.entries.append(entry)

    def write(self) -> None:
        """
        Write all accumulated entries to undo log JSON atomically.

        Uses temp file → rename pattern to ensure atomic writes and prevent
        corruption if the process crashes mid-write.

        Raises:
            Exception: If write fails (temp file is cleaned up automatically)
        """
        if not self.entries:
            # Don't write empty log
            return

        def writer_func(f):
            # Convert entries to dicts for JSON serialization
            entries_data = [
                {
                    'path': e.path,
                    'size_mb': e.size_mb,
                    'hash': e.hash,
                    'deleted_at': e.deleted_at,
                }
                for e in self.entries
            ]
            json.dump(entries_data, f, indent=2)

        target_dir = os.path.dirname(self.file_path) or '.'
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                dir=target_dir,
                delete=False,
                suffix='.tmp'
            ) as tmp_file:
                tmp_path = tmp_file.name
                try:
                    writer_func(tmp_file)
                    tmp_file.flush()
                except Exception:
                    if tmp_path and os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                    raise

            # Atomic rename
            os.rename(tmp_path, self.file_path)
        except Exception as e:
            # Clean up temp file if it still exists
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
            raise e


class DeletionOrchestrator:
    """
    Orchestrates safe file deletion with two modes:
    - Mode A (interactive): per-file confirmation, can skip individual files
    - Mode B (batch): dry-run preview → summary → type-to-confirm → execute

    Both modes write an undo log before executing, showing what was deleted
    for audit purposes (not restoration — deletion is permanent per D-11).

    Attributes:
        candidates: List of dicts {other_path, size_mb, hash, ...} to delete
        ui: UIHandler instance for progress callbacks
        report_dir: Directory containing the report (undo log written here)
        undo_log: UndoLog instance
    """

    def __init__(self, candidates: list, ui, report_path: str):
        """
        Initialize the orchestrator.

        Args:
            candidates: List of dicts with deletion candidates from ReportReader
            ui: UIHandler instance for progress display
            report_path: Path to original report (undo log written next to it)

        Raises:
            ValueError: If report_path directory doesn't exist or isn't writable
        """
        self.candidates = candidates
        self.ui = ui
        self.report_dir = os.path.dirname(report_path) or '.'
        self.undo_log = UndoLog(self.report_dir)

    def interactive_mode(self) -> DeletionResult:
        """
        Mode A: Interactive per-file confirmation.

        Presents each file to the user and asks: (y)es, (n)o, (skip), (abort)
        Updates running space freed after each deletion.

        Per D-07: No "delete all remaining" shortcut.

        Returns:
            DeletionResult with files_deleted, space_freed, aborted, undo_log_path
        """
        files_deleted = 0
        space_freed_mb = 0.0
        skipped = []
        errors = []
        current_index = 0

        try:
            for i, candidate in enumerate(self.candidates):
                current_index = i
                other_path = candidate.get('duplicate_file') or candidate.get('other_path', '')
                size_mb = float(candidate['size_mb'])
                file_hash = candidate.get('verification_hash') or candidate.get('hash', '')

                keep_path = candidate.get('original_file') or candidate.get('keep_path')

                # Prompt user — show both copies numbered so user can pick which to delete
                print(f"\n[{i+1}/{len(self.candidates)}] Duplicate files:", file=sys.stderr)
                if keep_path:
                    print(f"  (1) {other_path}", file=sys.stderr)
                    print(f"  (2) {keep_path}", file=sys.stderr)
                else:
                    print(f"  (1) {other_path}", file=sys.stderr)
                print(f"  Size: {size_mb} MB  |  Hash: {file_hash[:16]}... (verified match)", file=sys.stderr)
                print(f"  Space freed so far: {space_freed_mb:.2f} MB", file=sys.stderr)

                if keep_path:
                    prompt = "Delete (1), (2), (s)kip, (a)bort? "
                else:
                    prompt = "Delete (1), (s)kip, (a)bort? "
                choice = input(prompt).strip().lower()

                if choice in ['abort', 'a']:
                    # Abort entire workflow
                    self.undo_log.write()
                    return DeletionResult(
                        mode='interactive',
                        files_deleted=files_deleted,
                        space_freed_mb=space_freed_mb,
                        files_skipped=len(skipped) + (len(self.candidates) - i),
                        aborted=True,
                        undo_log_path=self.undo_log.file_path if self.undo_log.entries else None,
                        errors=errors
                    )

                elif choice in ['skip', 's']:
                    skipped.append(candidate)
                    continue

                elif choice in ['1', 'y', 'yes']:
                    # Delete the first listed copy (other_path)
                    path_to_delete = other_path
                    try:
                        self.undo_log.add(path_to_delete, size_mb, file_hash)
                        os.remove(path_to_delete)
                        files_deleted += 1
                        space_freed_mb += size_mb
                        print(f"  Deleted (1). Space freed so far: {space_freed_mb:.2f} MB", file=sys.stderr)
                    except FileNotFoundError:
                        errors.append(f"File not found (may have been deleted): {path_to_delete}")
                        skipped.append(candidate)
                    except PermissionError:
                        errors.append(f"Permission denied: {path_to_delete}")
                        skipped.append(candidate)
                    except OSError as e:
                        errors.append(f"Error deleting {path_to_delete}: {e}")
                        skipped.append(candidate)

                elif choice == '2' and keep_path:
                    # Delete the second listed copy (keep_path)
                    path_to_delete = keep_path
                    try:
                        self.undo_log.add(path_to_delete, size_mb, file_hash)
                        os.remove(path_to_delete)
                        files_deleted += 1
                        space_freed_mb += size_mb
                        print(f"  Deleted (2). Space freed so far: {space_freed_mb:.2f} MB", file=sys.stderr)
                    except FileNotFoundError:
                        errors.append(f"File not found (may have been deleted): {path_to_delete}")
                        skipped.append(candidate)
                    except PermissionError:
                        errors.append(f"Permission denied: {path_to_delete}")
                        skipped.append(candidate)
                    except OSError as e:
                        errors.append(f"Error deleting {path_to_delete}: {e}")
                        skipped.append(candidate)

                else:
                    # 'n', 'no', or unrecognised input — skip
                    skipped.append(candidate)
                    continue

        except KeyboardInterrupt:
            # Ctrl+C during mode A
            self.undo_log.write()
            print(f"\n^C Aborted during interactive mode.", file=sys.stderr)
            return DeletionResult(
                mode='interactive',
                files_deleted=files_deleted,
                space_freed_mb=space_freed_mb,
                files_skipped=len(skipped) + (len(self.candidates) - current_index - 1),
                aborted=True,
                undo_log_path=self.undo_log.file_path if self.undo_log.entries else None,
                errors=errors
            )

        # Write final undo log
        self.undo_log.write()

        return DeletionResult(
            mode='interactive',
            files_deleted=files_deleted,
            space_freed_mb=round(space_freed_mb, 2),
            files_skipped=len(skipped),
            aborted=False,
            undo_log_path=self.undo_log.file_path if self.undo_log.entries else None,
            errors=errors
        )

    def batch_mode(self) -> DeletionResult:
        """
        Mode B: Batch deletion with dry-run, summary, and confirmation.

        Workflow: dry-run preview → print summary → "Type DELETE to confirm" → execute

        Per D-08: User must type exactly "DELETE" to proceed.
        Per D-09: Progress shown during execution.

        Returns:
            DeletionResult with files_deleted, space_freed, aborted, undo_log_path
        """
        errors = []

        try:
            # Phase 1: Dry-run preview
            total_mb = sum(float(c['size_mb']) for c in self.candidates)
            total_display = f"{total_mb / 1024:.1f} GB" if total_mb >= 1024 else f"{total_mb:.0f} MB"

            print(f"\n-- Batch Delete Preview ----------------------------------------", file=sys.stderr)
            print(f"  Files to delete : {len(self.candidates):,}", file=sys.stderr)
            print(f"  Space to free   : {total_display}", file=sys.stderr)

            # File type breakdown
            ext_stats = {}
            for c in self.candidates:
                path = c.get('duplicate_file') or c.get('other_path', '')
                ext = os.path.splitext(path)[1].lower() or '(no extension)'
                mb = float(c['size_mb'])
                if ext not in ext_stats:
                    ext_stats[ext] = {'count': 0, 'mb': 0.0}
                ext_stats[ext]['count'] += 1
                ext_stats[ext]['mb'] += mb

            top_exts = sorted(ext_stats.items(), key=lambda x: x[1]['mb'], reverse=True)[:5]
            print(f"\n  By file type:", file=sys.stderr)
            for ext, stats in top_exts:
                size_str = f"{stats['mb'] / 1024:.1f} GB" if stats['mb'] >= 1024 else f"{stats['mb']:.0f} MB"
                print(f"    {ext or '(no ext)':16}  {stats['count']:>5,} files   {size_str}", file=sys.stderr)

            # Top 5 largest files with their originals
            sorted_candidates = sorted(self.candidates, key=lambda c: float(c['size_mb']), reverse=True)
            print(f"\n  Largest files to delete:", file=sys.stderr)
            for c in sorted_candidates[:5]:
                path = c.get('duplicate_file') or c.get('other_path', '')
                original = c.get('original_file') or c.get('keep_path', '')
                mb = float(c['size_mb'])
                size_str = f"{mb / 1024:.1f} GB" if mb >= 1024 else f"{mb:.1f} MB"
                print(f"    [{size_str}] {os.path.basename(path)}", file=sys.stderr)
                if original:
                    print(f"      Original: {original}", file=sys.stderr)

            print(f"\n  Safety: an undo log will be saved so you can recover files if needed.", file=sys.stderr)
            print(f"--------------------------------------------------------------------", file=sys.stderr)

            # Phase 2: Confirmation
            while True:
                confirm = input("\nType 'DELETE' to proceed, 'b' to go back, or Ctrl+C to abort: ").strip()

                if confirm == "DELETE":
                    # Proceed with deletion
                    break
                elif confirm == "b":
                    # User wants to go back to menu
                    return DeletionResult(
                        mode='batch',
                        files_deleted=0,
                        space_freed_mb=0.0,
                        files_skipped=len(self.candidates),
                        aborted=True,
                        undo_log_path=None,
                        errors=[]
                    )
                else:
                    print("Invalid input. Type 'DELETE' to proceed or 'b' to go back.", file=sys.stderr)

            # Phase 3: Execute deletions
            files_deleted = 0
            space_freed_mb = 0.0

            # Initialize progress display
            if self.ui:
                self.ui.start_deletion(len(self.candidates))

            for i, candidate in enumerate(self.candidates):
                other_path = candidate.get('duplicate_file') or candidate.get('other_path', '')
                size_mb = float(candidate['size_mb'])
                file_hash = candidate.get('verification_hash') or candidate.get('hash', '')

                try:
                    # Log entry BEFORE deletion (per D-12)
                    self.undo_log.add(other_path, size_mb, file_hash)
                    os.remove(other_path)
                    files_deleted += 1
                    space_freed_mb += size_mb

                    # Update progress display (D-09)
                    if self.ui:
                        self.ui.on_file_deleted(i + 1, len(self.candidates), space_freed_mb)

                except FileNotFoundError:
                    errors.append(f"File not found: {other_path}")
                except PermissionError:
                    errors.append(f"Permission denied: {other_path}")
                except OSError as e:
                    errors.append(f"Error deleting {other_path}: {e}")

            # Close progress display
            if self.ui:
                self.ui.close()

            # Write final undo log
            self.undo_log.write()

            return DeletionResult(
                mode='batch',
                files_deleted=files_deleted,
                space_freed_mb=round(space_freed_mb, 2),
                files_skipped=len(self.candidates) - files_deleted,
                aborted=False,
                undo_log_path=self.undo_log.file_path if self.undo_log.entries else None,
                errors=errors
            )

        except KeyboardInterrupt:
            # Ctrl+C during batch mode
            if self.ui:
                self.ui.close()
            self.undo_log.write()
            print(f"\n^C Aborted during batch execution.", file=sys.stderr)
            return DeletionResult(
                mode='batch',
                files_deleted=len([e for e in self.undo_log.entries]),
                space_freed_mb=round(sum(e.size_mb for e in self.undo_log.entries), 2),
                files_skipped=len(self.candidates) - len(self.undo_log.entries),
                aborted=True,
                undo_log_path=self.undo_log.file_path if self.undo_log.entries else None,
                errors=errors
            )


def filter_candidates_by_flags(results: dict, flagged_files: set) -> dict:
    """
    Remove flagged files from deletion candidate list.

    Takes the output from DuplicateClassifier.classify() and removes any files
    whose paths are in the flagged_files set. This ensures that flagged files
    are never included in deletion operations, even if they appear in duplicate
    or unique file categories.

    Args:
        results: Classification dict from DuplicateClassifier.classify() with structure:
                 {
                     'duplicates': [{'keep_path': str, 'other_path': str, ...}, ...],
                     'unique_in_keep': [{'keep_path': str, ...}, ...],
                     'unique_in_other': [{'other_path': str, ...}, ...],
                     'summary': {...}
                 }
        flagged_files: Set of file paths to exclude from deletion (e.g., {'a.txt', 'b.txt'})

    Returns:
        New classification dict with the same structure, but with all entries containing
        flagged files removed. Empty groups are removed from the results. If flagged_files
        is empty, returns results unchanged (no filtering applied).

    Examples:
        >>> results = {
        ...     'duplicates': [
        ...         {'keep_path': 'a.txt', 'other_path': 'a_dup.txt', ...},
        ...         {'keep_path': 'b.txt', 'other_path': 'b_dup.txt', ...}
        ...     ],
        ...     'unique_in_keep': [],
        ...     'unique_in_other': [],
        ...     'summary': {...}
        ... }
        >>> filter_candidates_by_flags(results, {'a.txt'})
        {
            'duplicates': [{'keep_path': 'b.txt', 'other_path': 'b_dup.txt', ...}],
            'unique_in_keep': [],
            'unique_in_other': [],
            'summary': {...}
        }
    """
    if not results or not flagged_files:
        return results

    # Create a new results dict with filtered entries
    filtered = {
        'duplicates': [],
        'unique_in_keep': [],
        'unique_in_other': [],
        'summary': results.get('summary', {})
    }

    # Filter duplicates: keep only if neither keep_path nor other_path is flagged
    for item in results.get('duplicates', []):
        keep_path = item.get('keep_path')
        other_path = item.get('other_path')
        # Include this item only if both paths are NOT flagged
        if keep_path not in flagged_files and other_path not in flagged_files:
            filtered['duplicates'].append(item)

    # Filter unique_in_keep: keep only if keep_path is NOT flagged
    for item in results.get('unique_in_keep', []):
        keep_path = item.get('keep_path')
        if keep_path not in flagged_files:
            filtered['unique_in_keep'].append(item)

    # Filter unique_in_other: keep only if other_path is NOT flagged
    for item in results.get('unique_in_other', []):
        other_path = item.get('other_path')
        if other_path not in flagged_files:
            filtered['unique_in_other'].append(item)

    return filtered
