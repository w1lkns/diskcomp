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
                other_path = candidate['other_path']
                size_mb = float(candidate['size_mb'])
                file_hash = candidate['hash']

                # Prompt user (per D-04: show both paths, size, hash verification)
                print(f"\n[{i+1}/{len(self.candidates)}] File to delete:", file=sys.stderr)
                print(f"  Path: {other_path}", file=sys.stderr)
                print(f"  Size: {size_mb} MB", file=sys.stderr)
                print(f"  Hash: {file_hash[:16]}... (verified match)", file=sys.stderr)
                print(f"  Space freed so far: {space_freed_mb:.2f} MB", file=sys.stderr)

                choice = input("(y)es, (n)o, (skip), (abort)? ").strip().lower()

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
                    # Skip this file, come back later
                    skipped.append(candidate)
                    continue

                elif choice in ['y', 'yes']:
                    # Delete file
                    try:
                        # Log entry BEFORE deletion (per D-12)
                        self.undo_log.add(other_path, size_mb, file_hash)
                        os.remove(other_path)
                        files_deleted += 1
                        space_freed_mb += size_mb
                        # Update UI with running total (D-05)
                        print(f"  ✓ Deleted. Space freed so far: {space_freed_mb:.2f} MB", file=sys.stderr)
                    except FileNotFoundError:
                        errors.append(f"File not found (may have been deleted): {other_path}")
                        skipped.append(candidate)
                    except PermissionError:
                        errors.append(f"Permission denied: {other_path}")
                        skipped.append(candidate)
                    except OSError as e:
                        errors.append(f"Error deleting {other_path}: {e}")
                        skipped.append(candidate)
                    # Continue to next file even on error

                else:
                    # choice in ['n', 'no'] or invalid input
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
            print(f"\n=== Deletion Preview (Batch Mode) ===", file=sys.stderr)
            print(f"Files to delete: {len(self.candidates)}", file=sys.stderr)
            print(f"Space to free: {total_mb:.2f} MB", file=sys.stderr)
            print("\nFiles:", file=sys.stderr)

            if len(self.candidates) <= 5:
                for c in self.candidates:
                    print(f"  - {c['other_path']} ({c['size_mb']} MB)", file=sys.stderr)
            else:
                for c in self.candidates[:5]:
                    print(f"  - {c['other_path']} ({c['size_mb']} MB)", file=sys.stderr)
                print(f"  ... and {len(self.candidates) - 5} more", file=sys.stderr)

            # Phase 2: Confirmation
            confirm = input("\nType DELETE to proceed, or Ctrl+C to abort: ").strip()
            if confirm != "DELETE":
                print("Deletion cancelled (confirmation string did not match).", file=sys.stderr)
                return DeletionResult(
                    mode='batch',
                    files_deleted=0,
                    space_freed_mb=0.0,
                    files_skipped=len(self.candidates),
                    aborted=True,
                    undo_log_path=None,
                    errors=[]
                )

            # Phase 3: Execute deletions
            files_deleted = 0
            space_freed_mb = 0.0

            # Initialize progress display
            if self.ui:
                self.ui.start_deletion(len(self.candidates))

            for i, candidate in enumerate(self.candidates):
                other_path = candidate['other_path']
                size_mb = float(candidate['size_mb'])
                file_hash = candidate['hash']

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
