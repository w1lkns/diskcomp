"""Unit tests for DuplicateClassifier and ReportWriter."""

import unittest
import tempfile
import json
import csv
import os
import shutil
from pathlib import Path

from diskcomp.types import FileRecord, ScanResult
from diskcomp.reporter import DuplicateClassifier, ReportWriter


class TestDuplicateClassifier(unittest.TestCase):
    """Test suite for DuplicateClassifier."""

    def test_classify_identifies_duplicates(self):
        """Test that classifier identifies duplicates correctly."""
        # Create mock ScanResults
        keep_file = FileRecord(
            path="/keep/file.txt",
            rel_path="file.txt",
            size_bytes=1024,
            hash="abc123",
            mtime=0,
            error=None
        )
        other_file = FileRecord(
            path="/other/file.txt",
            rel_path="file.txt",
            size_bytes=1024,
            hash="abc123",  # Same hash → duplicate
            mtime=0,
            error=None
        )
        keep_result = ScanResult(
            drive_path="/keep",
            file_count=1,
            total_size_bytes=1024,
            files=[keep_file],
            errors=[],
            skipped_noise_count=0
        )
        other_result = ScanResult(
            drive_path="/other",
            file_count=1,
            total_size_bytes=1024,
            files=[other_file],
            errors=[],
            skipped_noise_count=0
        )

        classifier = DuplicateClassifier(keep_result, other_result)
        classification = classifier.classify()

        assert len(classification['duplicates']) == 1, "Should find one duplicate"
        assert classification['duplicates'][0]['hash'] == 'abc123', "Hash should match"
        assert classification['duplicates'][0]['action'] == 'DELETE_FROM_OTHER', "Action should be DELETE_FROM_OTHER"

    def test_classify_identifies_unique_files(self):
        """Test that classifier identifies unique files."""
        keep_file = FileRecord(
            path="/keep/unique.txt",
            rel_path="unique.txt",
            size_bytes=1024,
            hash="unique123",
            mtime=0,
            error=None
        )
        keep_result = ScanResult(
            drive_path="/keep",
            file_count=1,
            total_size_bytes=1024,
            files=[keep_file],
            errors=[],
            skipped_noise_count=0
        )
        other_result = ScanResult(
            drive_path="/other",
            file_count=0,
            total_size_bytes=0,
            files=[],
            errors=[],
            skipped_noise_count=0
        )

        classifier = DuplicateClassifier(keep_result, other_result)
        classification = classifier.classify()

        assert len(classification['unique_in_keep']) == 1, "Should find one unique in keep"
        assert classification['unique_in_keep'][0]['action'] == 'UNIQUE_IN_KEEP', "Action should be UNIQUE_IN_KEEP"

    def test_classify_returns_summary(self):
        """Test that classification includes summary."""
        keep_result = ScanResult(
            drive_path="/keep",
            file_count=0,
            total_size_bytes=0,
            files=[],
            errors=[],
            skipped_noise_count=0
        )
        other_result = ScanResult(
            drive_path="/other",
            file_count=0,
            total_size_bytes=0,
            files=[],
            errors=[],
            skipped_noise_count=0
        )

        classifier = DuplicateClassifier(keep_result, other_result)
        classification = classifier.classify()

        assert 'summary' in classification, "Should have summary"
        assert 'duplicate_count' in classification['summary'], "Should have duplicate_count"
        assert 'unique_in_keep_count' in classification['summary'], "Should have unique_in_keep_count"
        assert 'unique_in_other_count' in classification['summary'], "Should have unique_in_other_count"


class TestReportWriter(unittest.TestCase):
    """Test suite for ReportWriter."""

    def setUp(self):
        """Create temporary test directory."""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test directory."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_write_csv(self):
        """Test CSV report writing."""
        classification = {
            'duplicates': [{
                'action': 'DELETE_FROM_OTHER',
                'keep_path': '/keep/file.txt',
                'other_path': '/other/file.txt',
                'size_mb': 1.0,
                'hash': 'abc123'
            }],
            'unique_in_keep': [],
            'unique_in_other': [],
            'summary': {}
        }
        # Specify custom path to ensure correct extension
        csv_path = os.path.join(self.test_dir, "test-report.csv")
        writer = ReportWriter(output_path=csv_path)
        writer.write_csv(classification)

        # Verify CSV file exists
        assert os.path.exists(writer.output_path), "CSV file should be created"
        # Verify CSV has correct columns
        with open(writer.output_path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) >= 1, "Should have at least one row"
            assert 'action' in rows[0], "Should have action column"
            assert 'hash' in rows[0], "Should have hash column"

    def test_write_json(self):
        """Test JSON report writing."""
        classification = {
            'duplicates': [{
                'action': 'DELETE_FROM_OTHER',
                'keep_path': '/keep/file.txt',
                'other_path': '/other/file.txt',
                'size_mb': 1.0,
                'hash': 'abc123'
            }],
            'unique_in_keep': [],
            'unique_in_other': [],
            'summary': {'duplicate_count': 1}
        }
        # Specify custom path to ensure correct extension
        json_path = os.path.join(self.test_dir, "test-report.json")
        writer = ReportWriter(output_path=json_path)
        writer.write_json(classification)

        # Verify JSON file exists
        assert os.path.exists(writer.output_path), "JSON file should be created"
        # Verify JSON is valid
        with open(writer.output_path) as f:
            data = json.load(f)
            assert len(data['duplicates']) == 1, "Should have one duplicate"

    def test_write_csv_with_custom_path(self):
        """Test CSV writing with custom path."""
        classification = {
            'duplicates': [],
            'unique_in_keep': [],
            'unique_in_other': [],
            'summary': {}
        }
        custom_path = os.path.join(self.test_dir, "custom-report.csv")
        writer = ReportWriter(output_path=custom_path)
        writer.write_csv(classification)

        assert os.path.exists(writer.output_path), "Custom path should be used"
        assert "custom-report" in writer.output_path, "Should contain custom name"


if __name__ == "__main__":
    unittest.main()
