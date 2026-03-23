"""Unit tests for FileHasher class."""

import unittest
import tempfile
import os
from pathlib import Path

from diskcomp.hasher import FileHasher, filter_by_size_collision, group_by_hash_single_drive, group_by_size_single_drive
from diskcomp.types import FileNotReadableError, FileRecord


class TestFileHasher(unittest.TestCase):
    """Test suite for FileHasher."""

    def setUp(self):
        """Create temporary test file."""
        self.hasher = FileHasher()
        self.test_file = tempfile.NamedTemporaryFile(delete=False)
        self.test_file.write(b"test content")
        self.test_file.close()

    def tearDown(self):
        """Clean up test file."""
        if os.path.exists(self.test_file.name):
            os.unlink(self.test_file.name)

    def test_hash_returns_hex_string(self):
        """Test that hash returns valid SHA256 hex string."""
        hash_val = self.hasher.hash_file(self.test_file.name)
        assert isinstance(hash_val, str), "Hash should be a string"
        assert len(hash_val) == 64, "SHA256 hex should be 64 characters"
        assert all(c in "0123456789abcdef" for c in hash_val), "Hash should be hex"

    def test_same_file_same_hash(self):
        """Test that same file produces same hash."""
        hash1 = self.hasher.hash_file(self.test_file.name)
        hash2 = self.hasher.hash_file(self.test_file.name)
        assert hash1 == hash2, "Same file should produce same hash"

    def test_different_files_different_hashes(self):
        """Test that different files produce different hashes."""
        test_file2 = tempfile.NamedTemporaryFile(delete=False)
        test_file2.write(b"different content")
        test_file2.close()
        try:
            hash1 = self.hasher.hash_file(self.test_file.name)
            hash2 = self.hasher.hash_file(test_file2.name)
            assert hash1 != hash2, "Different files should produce different hashes"
        finally:
            if os.path.exists(test_file2.name):
                os.unlink(test_file2.name)

    def test_nonexistent_file_raises_error(self):
        """Test that nonexistent file raises FileNotReadableError."""
        with self.assertRaises(FileNotReadableError):
            self.hasher.hash_file("/nonexistent/file.txt")

    def test_hash_file_record(self):
        """Test hashing a FileRecord."""
        record = FileRecord(
            path=self.test_file.name,
            rel_path="test.txt",
            size_bytes=12,
            hash=None,
            mtime=0,
            error=None
        )
        result = self.hasher.hash_file_record(record)
        assert result.hash is not None, "Hash should be set"
        assert len(result.hash) == 64, "Hash should be valid"

    @staticmethod
    def _make_record(path, size_bytes, hash=None):
        """Helper to create a FileRecord with minimal required fields."""
        return FileRecord(
            path=path,
            rel_path=os.path.basename(path),
            size_bytes=size_bytes,
            hash=hash,
            mtime=0.0,
            error=None
        )

    def test_filter_by_size_collision_basic_case(self):
        """Test basic filtering with partial size overlap."""
        keep_records = [
            self._make_record("/keep/file1", 100),
            self._make_record("/keep/file2", 200),
            self._make_record("/keep/file3", 300),
        ]
        other_records = [
            self._make_record("/other/file1", 200),
            self._make_record("/other/file2", 400),
            self._make_record("/other/file3", 500),
        ]

        filtered_keep, filtered_other, stats = filter_by_size_collision(
            keep_records, other_records
        )

        # Only 200-byte files should be candidates
        self.assertEqual(len(filtered_keep), 1, "Keep should have 1 candidate")
        self.assertEqual(filtered_keep[0].size_bytes, 200)
        self.assertEqual(len(filtered_other), 1, "Other should have 1 candidate")
        self.assertEqual(filtered_other[0].size_bytes, 200)

        # Check stats
        self.assertEqual(stats['total_scanned'], 6)
        self.assertEqual(stats['candidate_count'], 2)
        # 2 candidates out of 6 = 67% skipped (or 66 with integer division)
        self.assertIn(stats['pct_skipped'], [66, 67])

    def test_filter_by_size_collision_no_overlap(self):
        """Test filtering with no size overlap."""
        keep_records = [
            self._make_record("/keep/file1", 100),
            self._make_record("/keep/file2", 200),
        ]
        other_records = [
            self._make_record("/other/file1", 300),
            self._make_record("/other/file2", 400),
        ]

        filtered_keep, filtered_other, stats = filter_by_size_collision(
            keep_records, other_records
        )

        self.assertEqual(len(filtered_keep), 0, "Keep should be empty")
        self.assertEqual(len(filtered_other), 0, "Other should be empty")
        self.assertEqual(stats['candidate_count'], 0)
        self.assertEqual(stats['pct_skipped'], 100)

    def test_filter_by_size_collision_all_overlap(self):
        """Test filtering with complete size overlap."""
        keep_records = [
            self._make_record("/keep/file1", 100),
            self._make_record("/keep/file2", 200),
            self._make_record("/keep/file3", 300),
        ]
        other_records = [
            self._make_record("/other/file1", 100),
            self._make_record("/other/file2", 200),
            self._make_record("/other/file3", 300),
        ]

        filtered_keep, filtered_other, stats = filter_by_size_collision(
            keep_records, other_records
        )

        self.assertEqual(len(filtered_keep), 3, "Keep should have 3 candidates")
        self.assertEqual(len(filtered_other), 3, "Other should have 3 candidates")
        self.assertEqual(stats['candidate_count'], 6)
        self.assertEqual(stats['pct_skipped'], 0)

    def test_filter_by_size_collision_empty_input(self):
        """Test filtering with empty input lists."""
        keep_records = []
        other_records = []

        filtered_keep, filtered_other, stats = filter_by_size_collision(
            keep_records, other_records
        )

        self.assertEqual(len(filtered_keep), 0)
        self.assertEqual(len(filtered_other), 0)
        self.assertEqual(stats['total_scanned'], 0)
        self.assertEqual(stats['candidate_count'], 0)

    def test_filter_by_size_collision_preserves_metadata(self):
        """Test that filtering preserves all FileRecord metadata."""
        keep_records = [
            FileRecord(
                path="/keep/file1",
                rel_path="file1.txt",
                size_bytes=100,
                hash=None,
                mtime=1234567.0,
                error=None
            ),
            FileRecord(
                path="/keep/file2",
                rel_path="file2.txt",
                size_bytes=200,
                hash="abc123",
                mtime=2345678.0,
                error=None
            ),
        ]
        other_records = [
            FileRecord(
                path="/other/file1",
                rel_path="f1.txt",
                size_bytes=200,
                hash="def456",
                mtime=3456789.0,
                error="some error",
            ),
        ]

        filtered_keep, filtered_other, stats = filter_by_size_collision(
            keep_records, other_records
        )

        # filtered_keep should contain the 200-byte file
        self.assertEqual(len(filtered_keep), 1)
        self.assertEqual(filtered_keep[0].path, "/keep/file2")
        self.assertEqual(filtered_keep[0].rel_path, "file2.txt")
        self.assertEqual(filtered_keep[0].size_bytes, 200)
        self.assertEqual(filtered_keep[0].hash, "abc123")
        self.assertEqual(filtered_keep[0].mtime, 2345678.0)
        self.assertIsNone(filtered_keep[0].error)

        # filtered_other should contain the 200-byte file
        self.assertEqual(len(filtered_other), 1)
        self.assertEqual(filtered_other[0].path, "/other/file1")
        self.assertEqual(filtered_other[0].hash, "def456")
        self.assertEqual(filtered_other[0].error, "some error")


class TestGroupByHashSingleDrive(unittest.TestCase):
    """Test suite for group_by_hash_single_drive function."""

    @staticmethod
    def _make_record(path, size_bytes, hash=None):
        """Helper to create a FileRecord."""
        return FileRecord(
            path=path,
            rel_path=os.path.basename(path),
            size_bytes=size_bytes,
            hash=hash,
            mtime=0.0,
            error=None
        )

    def test_group_by_hash_single_drive_no_duplicates(self):
        """Test with all unique hashes (no duplicates)."""
        records = [
            self._make_record("/drive/file1", 100, "hash1"),
            self._make_record("/drive/file2", 200, "hash2"),
            self._make_record("/drive/file3", 300, "hash3"),
        ]

        result = group_by_hash_single_drive(records)

        # All files should be marked as unique
        self.assertEqual(len(result['duplicates']), 0)
        self.assertEqual(len(result['unique']), 3)
        self.assertEqual(result['summary']['duplicate_count'], 0)
        self.assertEqual(result['summary']['unique_in_other_count'], 3)

    def test_group_by_hash_single_drive_with_duplicates(self):
        """Test with duplicate files (same hash)."""
        records = [
            self._make_record("/drive/a/dup", 100, "hash1"),
            self._make_record("/drive/b/dup", 100, "hash1"),
            self._make_record("/drive/c/dup", 100, "hash1"),
        ]

        result = group_by_hash_single_drive(records)

        # Should have 2 duplicates (3-1 = 2) and 0 uniques
        self.assertEqual(len(result['duplicates']), 2)
        self.assertEqual(len(result['unique']), 0)
        self.assertEqual(result['summary']['duplicate_count'], 2)
        self.assertEqual(result['summary']['unique_in_other_count'], 0)

    def test_group_by_hash_single_drive_keeps_alphabetically_first(self):
        """Test that alphabetically first path is kept, others marked DELETE."""
        records = [
            self._make_record("/drive/z/file", 100, "hash1"),
            self._make_record("/drive/a/file", 100, "hash1"),
            self._make_record("/drive/m/file", 100, "hash1"),
        ]

        result = group_by_hash_single_drive(records)

        # /drive/a/file should be kept (alphabetically first)
        duplicates = result['duplicates']
        self.assertEqual(len(duplicates), 2)

        # Both duplicates should have keep_path pointing to /drive/a/file
        for dup in duplicates:
            self.assertEqual(dup['keep_path'], '/drive/a/file')
            self.assertIn(dup['other_path'], ['/drive/z/file', '/drive/m/file'])

    def test_group_by_hash_single_drive_mixed(self):
        """Test with mix of duplicates and unique files."""
        records = [
            self._make_record("/drive/file1", 100, "hash1"),
            self._make_record("/drive/file2", 100, "hash1"),
            self._make_record("/drive/file3", 200, "hash2"),
            self._make_record("/drive/file4", 300, "hash3"),
        ]

        result = group_by_hash_single_drive(records)

        # 1 duplicate (hash1 has 2 copies), 2 unique (hash2, hash3)
        self.assertEqual(len(result['duplicates']), 1)
        self.assertEqual(len(result['unique']), 2)

    def test_group_by_hash_single_drive_sizes(self):
        """Test that size_mb is calculated correctly."""
        records = [
            self._make_record("/drive/file1", 1024*1024, "hash1"),  # 1 MB
            self._make_record("/drive/file2", 1024*1024, "hash1"),  # 1 MB duplicate
        ]

        result = group_by_hash_single_drive(records)

        duplicates = result['duplicates']
        self.assertEqual(len(duplicates), 1)
        self.assertAlmostEqual(duplicates[0]['size_mb'], 1.0, places=2)
        self.assertAlmostEqual(result['summary']['duplicate_size_mb'], 1.0, places=2)


class TestGroupBySizeSingleDrive(unittest.TestCase):
    """Test suite for group_by_size_single_drive function."""

    @staticmethod
    def _make_record(path, size_bytes):
        """Helper to create a FileRecord."""
        return FileRecord(
            path=path,
            rel_path=os.path.basename(path),
            size_bytes=size_bytes,
            hash=None,
            mtime=0.0,
            error=None
        )

    def test_group_by_size_single_drive_filters_singletons(self):
        """Test that sizes appearing once are skipped."""
        records = [
            self._make_record("/drive/file1", 100),  # Unique size
            self._make_record("/drive/file2", 200),  # Size appears 2x
            self._make_record("/drive/file3", 200),  # Size appears 2x
            self._make_record("/drive/file4", 300),  # Unique size
        ]

        candidates, stats = group_by_size_single_drive(records)

        # Only 2 candidates (the two 200-byte files)
        self.assertEqual(len(candidates), 2)
        self.assertEqual(stats['total_scanned'], 4)
        self.assertEqual(stats['candidate_count'], 2)
        self.assertEqual(stats['pct_skipped'], 50)

    def test_group_by_size_single_drive_no_duplicates(self):
        """Test with all unique sizes."""
        records = [
            self._make_record("/drive/file1", 100),
            self._make_record("/drive/file2", 200),
            self._make_record("/drive/file3", 300),
        ]

        candidates, stats = group_by_size_single_drive(records)

        # No candidates (no sizes appear 2+ times)
        self.assertEqual(len(candidates), 0)
        self.assertEqual(stats['candidate_count'], 0)
        self.assertEqual(stats['pct_skipped'], 100)

    def test_group_by_size_single_drive_all_same_size(self):
        """Test with all files same size."""
        records = [
            self._make_record("/drive/file1", 100),
            self._make_record("/drive/file2", 100),
            self._make_record("/drive/file3", 100),
        ]

        candidates, stats = group_by_size_single_drive(records)

        # All 3 should be candidates
        self.assertEqual(len(candidates), 3)
        self.assertEqual(stats['pct_skipped'], 0)

    def test_group_by_size_single_drive_empty(self):
        """Test with empty input."""
        records = []

        candidates, stats = group_by_size_single_drive(records)

        self.assertEqual(len(candidates), 0)
        self.assertEqual(stats['total_scanned'], 0)
        self.assertEqual(stats['pct_skipped'], 0)


if __name__ == "__main__":
    unittest.main()
