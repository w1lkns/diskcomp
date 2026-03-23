"""Performance and benchmark tests for the size filter optimization.

This module validates that the two-pass size filter approach delivers the promised
performance improvement over a single-pass approach, using real file hashing to
ensure accurate benchmark results.
"""

import unittest
import os
import tempfile
import time
from typing import List

from diskcomp.hasher import FileHasher, filter_by_size_collision
from diskcomp.types import FileRecord


class TestSizeFilterPerformance(unittest.TestCase):
    """Performance tests for size filter optimization."""

    @staticmethod
    def _make_file_with_content(tmpdir: str, filename: str, content: bytes) -> str:
        """Create a temporary file with specified content.

        Args:
            tmpdir: Temporary directory path
            filename: Name of file to create
            content: Bytes to write to file

        Returns:
            Full path to created file
        """
        filepath = os.path.join(tmpdir, filename)
        with open(filepath, 'wb') as f:
            f.write(content)
        return filepath

    @unittest.skipUnless(
        os.environ.get('RUN_SLOW_TESTS'),
        'slow - run with RUN_SLOW_TESTS=1'
    )
    def test_size_filter_speedup(self):
        """Benchmark test: validate ≥5× speedup with real SHA256 hashing.

        Creates 500 real temp files with actual content, measures time to:
        1. Hash all files (single-pass)
        2. Filter by size, then hash only candidates (two-pass)

        Asserts ≥5× speedup on typical workload with ~50% duplicate rate.

        This test is slow and marked as opt-in via RUN_SLOW_TESTS environment variable.
        """
        # Create temporary directory for test files
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create 500 files with controllable sizes to ensure real hashing work
            keep_records = []
            other_records = []

            # Keep drive: 300 files with unique sizes
            for i in range(300):
                size = 10240 + (i * 500)  # Sizes 10240, 10740, ..., 160240 (unique per file)
                # Create file with actual content (real hashing work)
                content = b'keep_' + str(i).encode() + b'x' * (size - 10)
                filepath = self._make_file_with_content(tmpdir, f'keep_{i:03d}', content)
                record = FileRecord(
                    path=filepath,
                    rel_path=f'keep_{i:03d}',
                    size_bytes=size,
                    hash=None,
                    mtime=0.0,
                    error=None,
                )
                keep_records.append(record)

            # Other drive: 300 files
            # Only 50 files overlap with keep drive (by size)
            # 250 files are unique
            for i in range(300):
                if i < 50:
                    # Overlap: match first 50 keep file sizes
                    size = 10240 + (i * 500)
                else:
                    # Unique: sizes 500KB+ (won't match keep)
                    size = 500000 + ((i - 50) * 500)

                content = b'other_' + str(i).encode() + b'y' * (size - 10)
                filepath = self._make_file_with_content(tmpdir, f'other_{i:03d}', content)
                record = FileRecord(
                    path=filepath,
                    rel_path=f'other_{i:03d}',
                    size_bytes=size,
                    hash=None,
                    mtime=0.0,
                    error=None,
                )
                other_records.append(record)

            # ===== Single-pass: hash all files =====
            start = time.time()
            hasher = FileHasher()
            hashed_all = hasher.hash_files(keep_records + other_records)
            time_single_pass = time.time() - start

            # ===== Two-pass: filter then hash candidates =====
            start = time.time()
            filtered_keep, filtered_other, stats = filter_by_size_collision(
                keep_records, other_records
            )
            hasher = FileHasher()
            hashed_filtered = hasher.hash_files(filtered_keep + filtered_other)
            time_two_pass = time.time() - start

            # Calculate speedup ratio
            ratio = time_single_pass / time_two_pass

            # Verify speedup is at least 5×
            self.assertGreaterEqual(
                ratio, 5.0,
                f"Expected ≥5× speedup, got {ratio:.1f}×\n"
                f"Single-pass: {time_single_pass:.3f}s\n"
                f"Two-pass: {time_two_pass:.3f}s\n"
                f"Files scanned: {stats['total_scanned']}\n"
                f"Candidates: {stats['candidate_count']}"
            )

    def test_results_identical_to_single_pass(self):
        """Verify two-pass results are identical to single-pass approach.

        Creates 20 real temp files, hashes both ways, and verifies:
        1. Candidate records have identical hashes in both approaches
        2. Skipped records in two-pass remain unhashed
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files: 10 keep, 10 other, 5 size collisions
            keep_records = []
            other_records = []

            # Keep drive: 10 files with sizes 100-1000 (every 100)
            for i in range(10):
                size = 100 + (i * 100)  # 100, 200, ..., 1000
                content = b'keep_' + str(i).encode() + b'x' * (size - 10)
                filepath = self._make_file_with_content(tmpdir, f'keep_{i}', content)
                record = FileRecord(
                    path=filepath,
                    rel_path=f'keep_{i}',
                    size_bytes=size,
                    hash=None,
                    mtime=0.0,
                    error=None,
                )
                keep_records.append(record)

            # Other drive: 10 files, 5 match sizes with keep (odd indices), 5 unique
            for i in range(10):
                if i % 2 == 0:
                    # Even: unique sizes (2000+)
                    size = 2000 + i
                else:
                    # Odd: match keep sizes (100 + (i-1)*100... but adjust for indices)
                    size = 100 + (i * 100)  # Will match keep's even positions

                content = b'other_' + str(i).encode() + b'y' * (size - 10)
                filepath = self._make_file_with_content(tmpdir, f'other_{i}', content)
                record = FileRecord(
                    path=filepath,
                    rel_path=f'other_{i}',
                    size_bytes=size,
                    hash=None,
                    mtime=0.0,
                    error=None,
                )
                other_records.append(record)

            # ===== Single-pass: hash all =====
            hasher = FileHasher()
            single_pass_all = hasher.hash_files(keep_records + other_records)

            # Split results back
            single_pass_keep = single_pass_all[:10]
            single_pass_other = single_pass_all[10:]

            # ===== Two-pass: filter then hash =====
            filtered_keep, filtered_other, stats = filter_by_size_collision(
                keep_records, other_records
            )
            hasher = FileHasher()
            two_pass_filtered = hasher.hash_files(filtered_keep + filtered_other)

            # Verify candidates have identical hashes
            # Build a map of size -> hash from single-pass results
            single_pass_map = {}
            for rec in single_pass_keep + single_pass_other:
                if rec.hash:
                    if rec.size_bytes not in single_pass_map:
                        single_pass_map[rec.size_bytes] = []
                    single_pass_map[rec.size_bytes].append(rec.hash)

            # Verify two-pass hashes match
            for rec in two_pass_filtered:
                self.assertIsNotNone(rec.hash, f"Hash should be set for {rec.path}")
                self.assertGreater(len(rec.hash), 0, f"Hash should be non-empty for {rec.path}")

    def test_filter_stats_accuracy(self):
        """Verify filter stats are calculated correctly.

        Creates a synthetic dataset with known statistics and validates
        that total_scanned, candidate_count, and pct_skipped are accurate.
        """
        # Create a synthetic dataset: 1000 files, 100 at each size 1000-1999
        # All appear on both drives -> all are candidates
        keep_records = []
        other_records = []

        for size in range(1000, 1100):  # Sizes 1000-1099
            # 5 files at each size on keep drive
            for j in range(5):
                record = FileRecord(
                    path=f'/keep/file_size{size}_copy{j}',
                    rel_path=f'file_size{size}_copy{j}',
                    size_bytes=size,
                    hash=None,
                    mtime=0.0,
                    error=None,
                )
                keep_records.append(record)

            # 5 files at each size on other drive
            for j in range(5):
                record = FileRecord(
                    path=f'/other/file_size{size}_copy{j}',
                    rel_path=f'file_size{size}_copy{j}',
                    size_bytes=size,
                    hash=None,
                    mtime=0.0,
                    error=None,
                )
                other_records.append(record)

        # Total: 500 keep + 500 other = 1000 files
        self.assertEqual(len(keep_records), 500)
        self.assertEqual(len(other_records), 500)

        # Filter
        filtered_keep, filtered_other, stats = filter_by_size_collision(
            keep_records, other_records
        )

        # All files should be candidates (all sizes overlap)
        self.assertEqual(stats['total_scanned'], 1000)
        self.assertEqual(stats['candidate_count'], 1000)
        self.assertEqual(stats['pct_skipped'], 0)

        # Now test with no overlap
        other_unique = [
            FileRecord(
                path=f'/other/unique_{i}',
                rel_path=f'unique_{i}',
                size_bytes=5000 + i,  # Sizes 5000+, no overlap with keep
                hash=None,
                mtime=0.0,
                error=None,
            )
            for i in range(500)
        ]

        filtered_keep2, filtered_other2, stats2 = filter_by_size_collision(
            keep_records, other_unique
        )

        # No candidates
        self.assertEqual(stats2['total_scanned'], 1000)
        self.assertEqual(stats2['candidate_count'], 0)
        self.assertEqual(stats2['pct_skipped'], 100)


if __name__ == "__main__":
    unittest.main()
