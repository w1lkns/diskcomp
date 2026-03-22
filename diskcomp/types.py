"""
Type definitions and exceptions for diskcomp.

This module defines the data contracts (dataclasses) and exceptions used throughout
the diskcomp scanner, hasher, and reporter modules.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class FileRecord:
    """
    Represents a single scanned file.

    Attributes:
        path: Absolute filesystem path to the file
        rel_path: Relative path from the drive root (for reporting)
        size_bytes: File size in bytes
        hash: SHA256 hex string (None until hashed)
        mtime: Modification time as Unix timestamp (float)
        error: Error message if file couldn't be read or hashed (None if success)
    """
    path: str
    rel_path: str
    size_bytes: int
    hash: Optional[str] = None
    mtime: float = 0.0
    error: Optional[str] = None


@dataclass
class ScanResult:
    """
    Result of scanning one drive.

    Attributes:
        drive_path: The root path passed by user (e.g., "/Volumes/MyDrive" or "C:\\")
        file_count: Total number of files found (excluding noise)
        total_size_bytes: Sum of all file sizes (bytes)
        files: List of FileRecord objects collected
        errors: List of dicts with {path, reason} for errors encountered during scan
        skipped_noise_count: Count of OS noise files skipped during scan
    """
    drive_path: str
    file_count: int = 0
    total_size_bytes: int = 0
    files: List[FileRecord] = field(default_factory=list)
    errors: List[dict] = field(default_factory=list)
    skipped_noise_count: int = 0


class ScanError(Exception):
    """
    Raised on fatal scan errors that prevent scanning from proceeding.

    Examples: drive not mounted, invalid path, permission denied on root.
    """
    pass


class FileNotReadableError(Exception):
    """
    Raised when a file cannot be opened or read.

    Examples: permission denied, file deleted mid-scan, IO error.
    """
    pass


class InvalidPathError(Exception):
    """
    Raised when a path is not mounted or not readable.

    Examples: path does not exist, not a directory, not mounted.
    """
    pass
