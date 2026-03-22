"""
Deletion orchestration and undo log management for diskcomp.

This module handles safe file deletion with audit trails:
- UndoLog: Writes JSON audit log of deleted files (entries added before deletion)
- DeletionOrchestrator: Mode A (interactive per-file) and Mode B (batch) workflows
"""

import json
import os
import tempfile
from datetime import datetime
from typing import List, Optional

from diskcomp.types import UndoEntry


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
