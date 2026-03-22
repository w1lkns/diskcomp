"""
Cross-platform filesystem scanner for diskcomp.

This module walks filesystems recursively, skips OS noise files, and collects
file metadata without hashing. Provides the FileScanner class and noise patterns
for all platforms (macOS, Windows, Linux).
"""

import os
import sys
from pathlib import Path
from typing import Optional

from diskcomp.types import FileRecord, ScanResult, ScanError, InvalidPathError


# OS noise patterns to skip during scanning
NOISE_PATTERNS = {
    'all': [
        '.DS_Store',
        '.localized',
        '.Spotlight-V100',
        '.TemporaryItems',
        '.Trashes',
    ],
    'windows': [
        'Thumbs.db',
        '$RECYCLE.BIN',
        '$Recycle.Bin',
        'System Volume Information',
        '$SYSTEM.SAV',
        'NTFS.log',
        'pagefile.sys',
        'hiberfil.sys',
    ],
    'linux': [
        '.cache',
        '.config',
        '.local',
        '.mozilla',
        '.thumbnails',
    ],
}


def should_skip_file(name: str, platform: str) -> bool:
    """
    Check if a filename or directory name should be skipped (OS noise).

    Args:
        name: The filename or directory name to check
        platform: The platform string ('darwin', 'win32', 'linux')

    Returns:
        True if the name matches noise patterns and should be skipped
    """
    # Always check 'all' patterns
    if name in NOISE_PATTERNS['all']:
        return True

    # Check platform-specific patterns
    if platform == 'darwin':
        # macOS patterns already covered in 'all'
        pass
    elif platform == 'win32':
        if name in NOISE_PATTERNS['windows']:
            return True
    elif platform == 'linux':
        if name in NOISE_PATTERNS['linux']:
            return True

    return False


class FileScanner:
    """
    Cross-platform filesystem scanner that walks drives and collects file metadata.

    This scanner recursively walks a filesystem, skips OS noise files and files
    smaller than min_size_bytes, and collects metadata (path, size, mtime) for
    each valid file. Hashing is performed by a separate module.

    Attributes:
        root_path: The root directory path to scan
        min_size_bytes: Minimum file size in bytes (default 1024 = 1KB)
        platform: Detected platform ('darwin', 'win32', 'linux')
    """

    def __init__(self, root_path: str, min_size_bytes: int = 1024):
        """
        Initialize the scanner for a drive path.

        Args:
            root_path: The root directory to scan (e.g., "/Volumes/MyDrive" or "C:\\")
            min_size_bytes: Minimum file size to collect (default 1KB)

        Raises:
            InvalidPathError: If root_path does not exist or is not readable
        """
        self.root_path = os.path.abspath(root_path)
        self.min_size_bytes = min_size_bytes
        self.platform = sys.platform

        # Validate path exists and is readable
        if not os.path.exists(self.root_path):
            raise InvalidPathError(f"Path does not exist: {self.root_path}")
        if not os.path.isdir(self.root_path):
            raise InvalidPathError(f"Path is not a directory: {self.root_path}")
        if not os.access(self.root_path, os.R_OK):
            raise InvalidPathError(f"Path is not readable: {self.root_path}")

    def _is_noise(self, name: str) -> bool:
        """
        Check if a filename or directory name matches noise patterns.

        Args:
            name: The filename or directory name to check

        Returns:
            True if the name should be skipped
        """
        return should_skip_file(name, self.platform)

    def _get_relative_path(self, abs_path: str) -> str:
        """
        Convert an absolute path to a relative path from the drive root.

        Args:
            abs_path: Absolute filesystem path

        Returns:
            Relative path from root_path (using OS-specific separators)
        """
        try:
            rel = os.path.relpath(abs_path, self.root_path)
            return rel
        except ValueError:
            # On Windows, relpath can fail if paths are on different drives
            return abs_path

    def scan(
        self,
        dry_run: bool = False,
        limit: Optional[int] = None,
    ) -> ScanResult:
        """
        Walk the filesystem recursively and collect file metadata.

        This method walks the directory tree, skipping OS noise files and files
        smaller than min_size_bytes. If dry_run=True, only counts files without
        opening them (fast path). If limit is set, stops after collecting limit files.

        Args:
            dry_run: If True, count files without opening them (fast sanity check)
            limit: Maximum number of files to collect (None = unlimited)

        Returns:
            ScanResult with collected files, file_count, total_size, errors, noise_count
        """
        result = ScanResult(drive_path=self.root_path)
        files_collected = 0

        try:
            for root, dirs, filenames in os.walk(self.root_path):
                # Filter out noise directories in-place to prevent os.walk from descending
                # into them
                dirs[:] = [d for d in dirs if not self._is_noise(d)]

                # Process each file in this directory
                for filename in filenames:
                    # Stop if we've reached the limit
                    if limit is not None and files_collected >= limit:
                        break

                    # Skip noise files
                    if self._is_noise(filename):
                        result.skipped_noise_count += 1
                        continue

                    abs_path = os.path.join(root, filename)

                    try:
                        # Get file size (don't open the file in dry-run mode)
                        file_size = os.path.getsize(abs_path)

                        # Skip files smaller than minimum size
                        if file_size < self.min_size_bytes:
                            continue

                        # Get modification time
                        mtime = os.path.getmtime(abs_path)

                        # Get relative path
                        rel_path = self._get_relative_path(abs_path)

                        # Create FileRecord
                        record = FileRecord(
                            path=abs_path,
                            rel_path=rel_path,
                            size_bytes=file_size,
                            hash=None,  # Hashing done separately
                            mtime=mtime,
                            error=None,
                        )

                        result.files.append(record)
                        result.file_count += 1
                        result.total_size_bytes += file_size
                        files_collected += 1

                    except (PermissionError, OSError) as e:
                        # Log error but continue scanning
                        result.errors.append({
                            'path': abs_path,
                            'reason': str(e),
                        })

                # Stop outer loop if we've reached the limit
                if limit is not None and files_collected >= limit:
                    break

        except (PermissionError, OSError) as e:
            # Scan-level error (e.g., cannot read a directory)
            result.errors.append({
                'path': self.root_path,
                'reason': f"Scan error: {str(e)}",
            })

        return result


# Example usage (commented out):
# scanner = FileScanner("/Volumes/MyDrive")
# result = scanner.scan(dry_run=False, limit=None)
# print(f"Found {result.file_count} files, {result.total_size_bytes} bytes, "
#       f"{result.skipped_noise_count} noise files skipped")
# if result.errors:
#     print(f"Errors: {result.errors}")
