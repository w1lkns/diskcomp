"""End-to-end integration tests for the full diskcomp pipeline."""

import unittest
import tempfile
import os
import shutil
from pathlib import Path

from diskcomp.scanner import FileScanner
from diskcomp.hasher import FileHasher
from diskcomp.reporter import DuplicateClassifier, ReportWriter


class TestIntegration(unittest.TestCase):
    """End-to-end integration tests."""

    def test_full_pipeline(self):
        """Test complete pipeline: scan → hash → classify → report."""
        # Create two test directories with files
        keep_dir = tempfile.mkdtemp()
        other_dir = tempfile.mkdtemp()

        try:
            # Create identical files (>1KB to meet min_size_bytes default)
            content = "same content " * 100  # ~1300 bytes
            keep_file = Path(keep_dir, "file.txt")
            keep_file.write_text(content)

            other_file = Path(other_dir, "file.txt")
            other_file.write_text(content)

            # Create unique file
            unique_content = "unique to keep " * 100  # ~1400 bytes
            unique_keep = Path(keep_dir, "unique.txt")
            unique_keep.write_text(unique_content)

            # Scan both
            keep_scanner = FileScanner(keep_dir)
            other_scanner = FileScanner(other_dir)

            keep_result = keep_scanner.scan()
            other_result = other_scanner.scan()

            # Verify scans found files
            assert keep_result.file_count >= 2, "Keep should have at least 2 files"
            assert other_result.file_count >= 1, "Other should have at least 1 file"

            # Hash files
            hasher = FileHasher()
            keep_result.files = [hasher.hash_file_record(f) for f in keep_result.files]
            other_result.files = [hasher.hash_file_record(f) for f in other_result.files]

            # Verify hashes are set
            for f in keep_result.files:
                assert f.hash is not None, "All files should be hashed"

            # Classify
            classifier = DuplicateClassifier(keep_result, other_result)
            classification = classifier.classify()

            # Verify classification has duplicates
            assert 'duplicates' in classification, "Should have duplicates list"
            assert 'unique_in_keep' in classification, "Should have unique_in_keep list"
            assert len(classification['duplicates']) >= 1, "Should find at least one duplicate"

            # Write report
            report_dir = tempfile.mkdtemp()
            try:
                report_path = os.path.join(report_dir, "test-report.csv")
                writer = ReportWriter(output_path=report_path)
                writer.write_csv(classification)

                # Verify report exists
                assert Path(writer.output_path).exists(), "Report should be created"
                # Verify report is not empty
                assert os.path.getsize(writer.output_path) > 0, "Report should have content"
            finally:
                if os.path.exists(report_dir):
                    shutil.rmtree(report_dir)
        finally:
            if os.path.exists(keep_dir):
                shutil.rmtree(keep_dir)
            if os.path.exists(other_dir):
                shutil.rmtree(other_dir)

    def test_pipeline_with_dry_run(self):
        """Test pipeline with dry-run mode (no hashing)."""
        keep_dir = tempfile.mkdtemp()
        other_dir = tempfile.mkdtemp()

        try:
            # Create test files (>1KB to meet min_size_bytes default)
            Path(keep_dir, "file1.txt").write_text("content1 " * 150)
            Path(other_dir, "file2.txt").write_text("content2 " * 150)

            # Scan with dry-run
            keep_scanner = FileScanner(keep_dir)
            other_scanner = FileScanner(other_dir)

            keep_result = keep_scanner.scan(dry_run=True)
            other_result = other_scanner.scan(dry_run=True)

            # Verify counts work even in dry-run
            assert keep_result.file_count >= 1, "Dry-run should still count files"
            assert other_result.file_count >= 1, "Dry-run should still count files"
        finally:
            if os.path.exists(keep_dir):
                shutil.rmtree(keep_dir)
            if os.path.exists(other_dir):
                shutil.rmtree(other_dir)

    def test_pipeline_with_limit(self):
        """Test pipeline respects file limit."""
        keep_dir = tempfile.mkdtemp()
        other_dir = tempfile.mkdtemp()

        try:
            # Create multiple files (>1KB to meet min_size_bytes default)
            for i in range(5):
                Path(keep_dir, f"file{i}.txt").write_text(f"content{i} " * 150)
                Path(other_dir, f"file{i}.txt").write_text(f"content{i} " * 150)

            # Scan with limit
            keep_scanner = FileScanner(keep_dir)
            other_scanner = FileScanner(other_dir)

            keep_result = keep_scanner.scan(limit=2)
            other_result = other_scanner.scan(limit=2)

            # Verify limit is respected
            assert len(keep_result.files) <= 2, "Should respect limit"
            assert len(other_result.files) <= 2, "Should respect limit"
        finally:
            if os.path.exists(keep_dir):
                shutil.rmtree(keep_dir)
            if os.path.exists(other_dir):
                shutil.rmtree(other_dir)


if __name__ == "__main__":
    unittest.main()
