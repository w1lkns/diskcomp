"""Unit tests for FileHasher class."""

import unittest
import tempfile
import os
from pathlib import Path

from diskcomp.hasher import FileHasher
from diskcomp.types import FileNotReadableError


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
        from diskcomp.types import FileRecord
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


if __name__ == "__main__":
    unittest.main()
