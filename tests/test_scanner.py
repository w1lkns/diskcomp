"""Unit tests for FileScanner class."""

import unittest
import tempfile
import os
import shutil
from pathlib import Path

from diskcomp.scanner import FileScanner, NOISE_PATTERNS
from diskcomp.types import ScanResult


class TestFileScanner(unittest.TestCase):
    """Test suite for FileScanner."""

    def setUp(self):
        """Create temporary test directory with files."""
        self.test_dir = tempfile.mkdtemp()
        # Create test files (>1KB to meet min_size_bytes default)
        Path(self.test_dir, "file1.txt").write_text("content" * 200)  # ~1400 bytes
        Path(self.test_dir, "file2.txt").write_text("content" * 200)  # ~1400 bytes
        Path(self.test_dir, ".DS_Store").write_text("noise")  # noise file
        Path(self.test_dir, "subdir").mkdir()
        Path(self.test_dir, "subdir", "file3.txt").write_text("content" * 200)  # ~1400 bytes

    def tearDown(self):
        """Clean up test directory."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_scan_counts_files(self):
        """Test that scan counts files correctly."""
        scanner = FileScanner(self.test_dir)
        result = scanner.scan()
        assert result.file_count > 0, "Should find at least one file"
        assert result.total_size_bytes > 0, "Should have total size"

    def test_scan_skips_noise(self):
        """Test that scanner skips noise files like .DS_Store."""
        scanner = FileScanner(self.test_dir)
        result = scanner.scan()
        assert result.skipped_noise_count >= 1, "Should skip .DS_Store"
        # Verify .DS_Store is not in result.files
        file_names = [f.path for f in result.files]
        assert not any(".DS_Store" in f for f in file_names), ".DS_Store should be excluded"

    def test_scan_skips_appledouble_files(self):
        """Test that scanner skips AppleDouble resource fork files (._filename)."""
        # macOS creates these on non-HFS+ volumes (FAT32, NTFS, exFAT)
        Path(self.test_dir, "._DS_Store").write_bytes(b"\x00\x05\x16\x07" * 100)
        Path(self.test_dir, "._photo.jpg").write_bytes(b"\x00\x05\x16\x07" * 100)
        scanner = FileScanner(self.test_dir)
        result = scanner.scan()
        file_names = [f.path for f in result.files]
        assert not any(os.path.basename(f).startswith("._") for f in file_names), \
            "AppleDouble ._* files should be excluded"

    def test_scan_filters_small_files(self):
        """Test that scanner respects min_size_bytes."""
        # Create file < 1KB
        tiny_file = Path(self.test_dir, "tiny.txt")
        tiny_file.write_text("x" * 100)  # 100 bytes
        scanner = FileScanner(self.test_dir, min_size_bytes=1024)
        result = scanner.scan()
        # tiny.txt should not be in result (too small)
        file_names = [f.path for f in result.files]
        assert not any("tiny.txt" in f for f in file_names), "Tiny file should be filtered out"

    def test_dry_run_skips_hashing(self):
        """Test that dry-run counts files without reading them."""
        scanner = FileScanner(self.test_dir)
        result = scanner.scan(dry_run=True)
        # In dry-run, files are counted but may not be fully read
        assert result.file_count > 0, "Even dry-run should count files"

    def test_scan_respects_limit(self):
        """Test that scan respects file count limit."""
        scanner = FileScanner(self.test_dir)
        result = scanner.scan(limit=1)
        assert len(result.files) <= 1, "Should not exceed limit"

    def test_scan_returns_scan_result(self):
        """Test that scan returns a ScanResult object."""
        scanner = FileScanner(self.test_dir)
        result = scanner.scan()
        assert isinstance(result, ScanResult), "Should return ScanResult"
        assert result.drive_path == self.test_dir, "Should set drive_path"

    def test_files_have_metadata(self):
        """Test that files have complete metadata."""
        scanner = FileScanner(self.test_dir)
        result = scanner.scan()
        assert len(result.files) > 0, "Should have at least one file"
        file_record = result.files[0]
        assert hasattr(file_record, 'path'), "Should have path"
        assert hasattr(file_record, 'size_bytes'), "Should have size"
        assert hasattr(file_record, 'mtime'), "Should have mtime"
        assert file_record.path, "Path should not be empty"
        assert file_record.size_bytes >= 0, "Size should be non-negative"


if __name__ == "__main__":
    unittest.main()
