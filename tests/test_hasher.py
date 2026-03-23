"""Unit tests for FileHasher class."""

import unittest
import tempfile
import os
from pathlib import Path

from diskcomp.hasher import FileHasher, filter_by_size_collision
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


if __name__ == "__main__":
    unittest.main()
