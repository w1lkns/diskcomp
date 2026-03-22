"""
Type definitions and exceptions for diskcomp.

This module defines the data contracts (dataclasses) and exceptions used throughout
the diskcomp scanner, hasher, and reporter modules.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict


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


@dataclass
class DriveInfo:
    """
    Represents a mounted drive with space and filesystem info.

    Attributes:
        device: Device identifier (e.g., '/dev/sda', 'C:\\', '/dev/disk1')
        mountpoint: Mount path (e.g., '/Volumes/MyDrive', '/mnt/external')
        fstype: Filesystem type (e.g., 'NTFS', 'HFS+', 'ext4', 'exFAT')
        total_gb: Total capacity in GB
        used_gb: Used space in GB
        free_gb: Free space in GB
        is_writable: Result of os.access(mountpoint, os.W_OK)
    """
    device: str
    mountpoint: str
    fstype: str
    total_gb: float
    used_gb: float
    free_gb: float
    is_writable: bool


@dataclass
class HealthCheckResult:
    """
    Complete health check result for one drive.

    Attributes:
        mountpoint: Drive being checked
        total_gb: Total capacity in GB
        used_gb: Used space in GB
        free_gb: Free space in GB
        fstype: Detected filesystem type
        is_writable: Write permission check result
        warnings: List of warning messages
        errors: List of error messages
        smart_data: SMART info if available, else None
    """
    mountpoint: str
    total_gb: float
    used_gb: float
    free_gb: float
    fstype: str
    is_writable: bool
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    smart_data: Optional[Dict] = None


@dataclass
class BenchmarkResult:
    """
    Result of sequential read speed benchmark on a drive.

    Attributes:
        mountpoint: Drive tested
        speed_mbps: Measured speed in MB/s
        duration_secs: Time elapsed in seconds
        bytes_read: Total bytes read during test
        success: True if benchmark completed without error
        error: Error message if success=False, else None
    """
    mountpoint: str
    speed_mbps: float
    duration_secs: float
    bytes_read: int
    success: bool
    error: Optional[str] = None
