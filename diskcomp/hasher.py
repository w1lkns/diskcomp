"""
SHA256 hashing module for diskcomp.

This module provides the FileHasher class which implements SHA256 hashing with
chunked reading for memory efficiency and comprehensive error handling.

Chunked reading ensures large files (GB+) can be hashed without loading the
entire file into memory. Each chunk is processed incrementally through the
hash function.
"""

import hashlib
import os
import time
from typing import Callable, List, Optional
from diskcomp.types import FileRecord, FileNotReadableError


class FileHasher:
    """
    Computes SHA256 hashes of files with chunked reading for memory efficiency.

    This hasher reads files in fixed-size chunks (default 8KB) to minimize memory
    usage while computing cryptographic hashes. Provides comprehensive error
    handling for permission errors, IO errors, and file access issues.

    Attributes:
        chunk_size: Size of each read chunk in bytes (default 8192 = 8KB)

    Example:
        hasher = FileHasher(chunk_size=8192)
        hash_value = hasher.hash_file("/path/to/file.txt")
        # Returns "abc123def456..." (64-character hex string)
    """

    def __init__(self, chunk_size: int = 8192):
        """
        Initialize the FileHasher with a chunk size.

        Args:
            chunk_size: Size of each read chunk in bytes (default 8192 = 8KB)
                       Larger chunks improve I/O efficiency but use more memory.
                       Smaller chunks reduce memory usage but increase I/O operations.
        """
        self.chunk_size = chunk_size

    def hash_file(self, file_path: str) -> str:
        """
        Compute the SHA256 hash of a file.

        Reads the file in chunks and computes the SHA256 hash incrementally.
        This approach allows hashing of very large files without loading the
        entire file into memory.

        Args:
            file_path: Absolute filesystem path to the file to hash

        Returns:
            64-character hexadecimal string representing the SHA256 digest
            (all lowercase)

        Raises:
            FileNotReadableError: If the file cannot be opened or read
                - On PermissionError: reason "Permission denied"
                - On OSError: reason "Cannot read file"
                - On IOError: reason "IO error"
        """
        hasher = hashlib.sha256()

        try:
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(self.chunk_size)
                    if not chunk:
                        break
                    hasher.update(chunk)
            return hasher.hexdigest()

        except PermissionError as e:
            raise FileNotReadableError(f"Permission denied: {file_path}") from e
        except OSError as e:
            raise FileNotReadableError(f"Cannot read file: {file_path}") from e
        except IOError as e:
            raise FileNotReadableError(f"IO error reading file: {file_path}") from e

    def hash_file_record(self, record: FileRecord) -> FileRecord:
        """
        Hash a FileRecord and return an updated copy.

        This method takes a FileRecord (from the scanner) and computes its SHA256 hash.
        On success, updates the record's hash field. On error, sets the error field
        and returns the record so the caller can decide how to handle it.

        Args:
            record: FileRecord object with path and other metadata

        Returns:
            FileRecord with hash field updated on success, or error field set on failure.
            Returns a new object (modified copy of input record).
        """
        try:
            hash_value = self.hash_file(record.path)
            record.hash = hash_value
            return record
        except FileNotReadableError as e:
            record.error = str(e)
            return record

    def hash_files(
        self,
        records: List[FileRecord],
        on_file_hashed: Optional[Callable[[int, int, float, int], None]] = None,
    ) -> List[FileRecord]:
        """
        Hash multiple files with per-file progress callback.

        Processes a list of FileRecord objects, computing SHA256 hashes and invoking
        a callback after each file with progress metrics including speed and ETA.

        Args:
            records: List of FileRecord objects to hash
            on_file_hashed: Optional callback(current_index, total, speed_mbps, eta_secs)
                           called after hashing each file

        Returns:
            List of FileRecord objects with hash field populated
        """
        hashed_records = []
        start_time = time.time()
        total_bytes_hashed = 0
        total_files = len(records)

        for i, record in enumerate(records):
            # Hash the record
            record = self.hash_file_record(record)

            # Update total bytes hashed (even if error)
            if record.error is None:
                total_bytes_hashed += record.size_bytes

            # Calculate metrics if callback provided
            if on_file_hashed:
                elapsed = time.time() - start_time

                # Calculate speed in MB/s
                if elapsed > 0:
                    speed_mbps = (total_bytes_hashed / elapsed) / (1024 * 1024)
                else:
                    speed_mbps = 0.0

                # Calculate ETA in seconds
                eta_secs = 0
                if speed_mbps > 0 and elapsed > 0:
                    bytes_per_sec = (total_bytes_hashed / elapsed)
                    remaining_bytes = sum(r.size_bytes for r in records[i + 1:] if r.error is None)
                    eta_secs = int(remaining_bytes / bytes_per_sec) if bytes_per_sec > 0 else 0

                # Invoke callback with current index (1-based), total, speed, and ETA
                on_file_hashed(i + 1, total_files, speed_mbps, eta_secs)

            hashed_records.append(record)

        return hashed_records


def filter_by_size_collision(
    keep_records: List[FileRecord],
    other_records: List[FileRecord],
) -> tuple:
    """
    Filter file records by cross-drive size collision matching.

    This function implements the two-pass optimization: identifies files that
    could potentially be duplicates by checking if their file size exists on
    the other drive. Files with sizes that don't appear on the other drive are
    skipped entirely (not candidates for hashing).

    The mechanism:
    - A file from keep_records is a candidate only if at least one file on
      other_records has the same size_bytes
    - A file from other_records is a candidate only if at least one file on
      keep_records has the same size_bytes
    - This cross-drive intersection ensures we never hash files that cannot
      possibly be duplicates

    Args:
        keep_records: List of FileRecord objects from the "keep" drive
        other_records: List of FileRecord objects from the "other" drive

    Returns:
        Tuple of (filtered_keep, filtered_other, stats) where:
        - filtered_keep: FileRecords from keep_records that have size matches on other drive
        - filtered_other: FileRecords from other_records that have size matches on keep drive
        - stats: dict with keys:
            - total_scanned: int, original total count (len(keep_records) + len(other_records))
            - candidate_count: int, filtered total count (len(filtered_keep) + len(filtered_other))
            - pct_skipped: int, percentage skipped (0-100), calculated as
              (total_scanned - candidate_count) * 100 // total_scanned
    """
    # Build sets of all sizes on each drive
    other_sizes = {r.size_bytes for r in other_records}
    keep_sizes = {r.size_bytes for r in keep_records}

    # Filter: keep only records whose size exists on the other drive
    filtered_keep = [r for r in keep_records if r.size_bytes in other_sizes]
    filtered_other = [r for r in other_records if r.size_bytes in keep_sizes]

    # Calculate stats
    total_scanned = len(keep_records) + len(other_records)
    candidate_count = len(filtered_keep) + len(filtered_other)
    pct_skipped = 0
    if total_scanned > 0:
        pct_skipped = (total_scanned - candidate_count) * 100 // total_scanned

    stats = {
        'total_scanned': total_scanned,
        'candidate_count': candidate_count,
        'pct_skipped': pct_skipped,
    }

    return (filtered_keep, filtered_other, stats)
