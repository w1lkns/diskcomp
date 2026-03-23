"""End-to-end integration tests for the full diskcomp pipeline."""

import unittest
import tempfile
import os
import shutil
import json
import csv
from pathlib import Path
from unittest.mock import patch, MagicMock

from diskcomp.scanner import FileScanner
from diskcomp.hasher import FileHasher
from diskcomp.reporter import DuplicateClassifier, ReportWriter
from diskcomp.cli import main, parse_args, run_post_scan_menu, orchestrate_deletion, show_folder_selection, show_file_flagging
from diskcomp.types import ScanResult, FileRecord, HealthCheckResult, NavigationContext, DeletionResult
from diskcomp.deletion import filter_candidates_by_flags


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


class TestPhase3Integration(unittest.TestCase):
    """Integration tests for Phase 3: Interactive Drive Picker + Health Checks."""

    @patch('diskcomp.cli.input')
    @patch('diskcomp.cli.ReportWriter')
    @patch('diskcomp.cli.DuplicateClassifier')
    @patch('diskcomp.cli.FileHasher')
    @patch('diskcomp.cli.FileScanner')
    @patch('diskcomp.cli.display_health_checks')
    @patch('diskcomp.cli.check_drive_health')
    @patch('diskcomp.cli.os.access')
    @patch('diskcomp.cli.os.path.isdir')
    @patch('diskcomp.cli.interactive_drive_picker')
    @patch('diskcomp.cli.UIHandler')
    def test_interactive_mode_end_to_end(
            self, mock_ui_factory, mock_picker, mock_isdir, mock_access,
            mock_health_check, mock_display_health, mock_scanner_class,
            mock_hasher_class, mock_classifier_class, mock_reporter_class,
            mock_input):
        """Test full workflow: interactive picker → health checks → scan → report."""
        # Setup UI mock
        mock_ui = MagicMock()
        mock_ui_factory.create.return_value = mock_ui

        # Setup interactive picker
        mock_picker.return_value = {'keep': '/mnt/keep', 'other': '/mnt/other'}

        # Setup path validation
        mock_isdir.return_value = True
        mock_access.return_value = True

        # Setup health checks
        mock_display_health.return_value = True

        # Setup scanner
        keep_file = FileRecord(path='/mnt/keep/file.txt', rel_path='file.txt', size_bytes=1500)
        other_file = FileRecord(path='/mnt/other/file.txt', rel_path='file.txt', size_bytes=1500)
        keep_result = ScanResult(
            drive_path='/mnt/keep',
            file_count=1,
            total_size_bytes=1500,
            files=[keep_file]
        )
        other_result = ScanResult(
            drive_path='/mnt/other',
            file_count=1,
            total_size_bytes=1500,
            files=[other_file]
        )

        mock_scanner = MagicMock()
        mock_scanner.scan.return_value = keep_result
        mock_scanner_class.return_value = mock_scanner

        # Setup hasher
        keep_file_hashed = FileRecord(
            path='/mnt/keep/file.txt',
            rel_path='file.txt',
            size_bytes=1500,
            hash='abc123'
        )
        other_file_hashed = FileRecord(
            path='/mnt/other/file.txt',
            rel_path='file.txt',
            size_bytes=1500,
            hash='abc123'
        )

        mock_hasher = MagicMock()
        mock_hasher.hash_files.return_value = [keep_file_hashed, other_file_hashed]
        mock_hasher_class.return_value = mock_hasher

        # Setup classifier
        mock_classifier = MagicMock()
        mock_classifier.classify.return_value = {
            'duplicates': [{'keep_path': '/mnt/keep/file.txt', 'other_path': '/mnt/other/file.txt', 'size_mb': 0.001}],
            'unique_in_keep': [],
            'unique_in_other': [],
            'summary': {
                'duplicate_count': 1,
                'duplicate_size_mb': 0.001,
                'unique_in_keep_count': 0,
                'unique_in_keep_size_mb': 0,
                'unique_in_other_count': 0,
                'unique_in_other_size_mb': 0
            }
        }
        mock_classifier_class.return_value = mock_classifier

        # Setup reporter
        mock_reporter = MagicMock()
        mock_reporter.output_path = '/tmp/diskcomp-report.csv'
        mock_reporter_class.return_value = mock_reporter

        # Interactive mode: '1' selects "Compare two drives" from menu,
        # 'y' confirms scan, '3' exits action menu
        mock_input.side_effect = ['1', 'y', '3']

        # Call main with empty args (triggers interactive mode)
        from diskcomp.cli import parse_args
        args = parse_args([])
        result = main(args)

        # Verify success
        self.assertEqual(result, 0)
        # Verify interactive picker was called
        mock_picker.assert_called_once()
        # Verify health checks were run
        mock_display_health.assert_called_once()

    @patch('diskcomp.cli.input')
    @patch('diskcomp.cli.ReportWriter')
    @patch('diskcomp.cli.DuplicateClassifier')
    @patch('diskcomp.cli.FileHasher')
    @patch('diskcomp.cli.FileScanner')
    @patch('diskcomp.cli.display_health_checks')
    @patch('diskcomp.cli.os.access')
    @patch('diskcomp.cli.os.path.isdir')
    @patch('diskcomp.cli.UIHandler')
    def test_non_interactive_mode_with_health(
            self, mock_ui_factory, mock_isdir, mock_access,
            mock_display_health, mock_scanner_class, mock_hasher_class,
            mock_classifier_class, mock_reporter_class, mock_input):
        """Test that health checks run even in non-interactive mode (--keep/--other)."""
        # Setup UI mock
        mock_ui = MagicMock()
        mock_ui_factory.create.return_value = mock_ui

        # Setup path validation
        mock_isdir.return_value = True
        mock_access.return_value = True

        # Setup health checks
        mock_display_health.return_value = True

        # Setup scanner
        keep_result = ScanResult(
            drive_path='/mnt/keep',
            file_count=0,
            total_size_bytes=0,
            files=[]
        )
        other_result = ScanResult(
            drive_path='/mnt/other',
            file_count=0,
            total_size_bytes=0,
            files=[]
        )

        mock_scanner = MagicMock()
        mock_scanner.scan.return_value = keep_result
        mock_scanner_class.return_value = mock_scanner

        # Setup hasher
        mock_hasher = MagicMock()
        mock_hasher.hash_files.return_value = []
        mock_hasher_class.return_value = mock_hasher

        # Setup classifier
        mock_classifier = MagicMock()
        mock_classifier.classify.return_value = {
            'duplicates': [],
            'unique_in_keep': [],
            'unique_in_other': [],
            'summary': {
                'duplicate_count': 0,
                'duplicate_size_mb': 0,
                'unique_in_keep_count': 0,
                'unique_in_keep_size_mb': 0,
                'unique_in_other_count': 0,
                'unique_in_other_size_mb': 0
            }
        }
        mock_classifier_class.return_value = mock_classifier

        # Setup reporter
        mock_reporter = MagicMock()
        mock_reporter.output_path = '/tmp/diskcomp-report.csv'
        mock_reporter_class.return_value = mock_reporter

        # User confirms
        mock_input.return_value = 'y'

        # Call main with --keep and --other
        from diskcomp.cli import parse_args
        args = parse_args(['--keep', '/mnt/keep', '--other', '/mnt/other'])
        result = main(args)

        # Verify success
        self.assertEqual(result, 0)
        # Verify health checks still run (even with --keep/--other)
        mock_display_health.assert_called_once()

    @patch('diskcomp.cli.input')
    @patch('diskcomp.cli.ReportWriter')
    @patch('diskcomp.cli.DuplicateClassifier')
    @patch('diskcomp.cli.FileHasher')
    @patch('diskcomp.cli.FileScanner')
    @patch('diskcomp.cli.display_health_checks')
    @patch('diskcomp.cli.os.access')
    @patch('diskcomp.cli.os.path.isdir')
    @patch('diskcomp.cli.UIHandler')
    def test_health_check_blocks_nonwritable_keep(
            self, mock_ui_factory, mock_isdir, mock_access,
            mock_display_health, mock_scanner_class, mock_hasher_class,
            mock_classifier_class, mock_reporter_class, mock_input):
        """Test that non-writable keep drive blocks scan."""
        # Setup UI mock
        mock_ui = MagicMock()
        mock_ui_factory.create.return_value = mock_ui

        # Setup path validation
        mock_isdir.return_value = True
        mock_access.return_value = True

        # Health checks fail (keep not writable)
        mock_display_health.return_value = False

        # Call main
        from diskcomp.cli import parse_args
        args = parse_args(['--keep', '/mnt/keep', '--other', '/mnt/other'])
        result = main(args)

        # Verify failure
        self.assertEqual(result, 1)
        # Verify UI was closed
        mock_ui.close.assert_called()
        # Verify scanner was NOT called
        mock_scanner_class.assert_not_called()

    @patch('diskcomp.cli.input')
    @patch('diskcomp.cli.UIHandler')
    def test_user_cancels_after_health_checks(
            self, mock_ui_factory, mock_input):
        """Test graceful cancellation after health checks."""
        # Setup UI mock
        mock_ui = MagicMock()
        mock_ui_factory.create.return_value = mock_ui

        with patch('diskcomp.cli.os.path.isdir', return_value=True):
            with patch('diskcomp.cli.os.access', return_value=True):
                with patch('diskcomp.cli.display_health_checks', return_value=True):
                    # User cancels (answers 'n' to scan confirmation)
                    mock_input.return_value = 'n'

                    # Call main
                    from diskcomp.cli import parse_args
                    args = parse_args(['--keep', '/mnt/keep', '--other', '/mnt/other'])
                    result = main(args)

                    # Verify graceful exit
                    self.assertEqual(result, 0)
                    # Verify UI was closed
                    mock_ui.close.assert_called()


class TestDeletionCLI(unittest.TestCase):
    """Integration tests for deletion CLI workflow."""

    def test_delete_from_missing_report(self):
        """--delete-from with missing report file returns error."""
        args = parse_args(['--delete-from', '/nonexistent/report.csv'])
        result = main(args)
        self.assertEqual(result, 1)

    def test_delete_from_empty_report(self):
        """--delete-from with no candidates exits cleanly."""
        # Create temporary report with no DELETE_FROM_OTHER rows
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(
                f,
                fieldnames=['action', 'keep_path', 'other_path', 'size_mb', 'hash']
            )
            writer.writeheader()
            writer.writerow({
                'action': 'UNIQUE_IN_KEEP',
                'keep_path': '/path/a',
                'other_path': None,
                'size_mb': 1.0,
                'hash': 'abc123'
            })
            temp_report = f.name

        try:
            args = parse_args(['--delete-from', temp_report])
            result = main(args)
            self.assertEqual(result, 0)
        finally:
            os.unlink(temp_report)

    @patch('diskcomp.cli.input', return_value='skip')
    def test_delete_from_skip_mode(self, mock_input):
        """--delete-from with skip selection exits without deletion."""
        # Create temp directories with actual files
        temp_dir = tempfile.mkdtemp()

        try:
            # Create an "other" file to reference in the report
            other_file = os.path.join(temp_dir, 'file.txt')
            with open(other_file, 'w') as f:
                f.write("test content")

            # Create temporary report with DELETE_FROM_OTHER row
            report_file = os.path.join(temp_dir, 'report.csv')
            with open(report_file, 'w') as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=['action', 'keep_path', 'other_path', 'size_mb', 'hash']
                )
                writer.writeheader()
                writer.writerow({
                    'action': 'DELETE_FROM_OTHER',
                    'keep_path': '/path/keep/file.txt',
                    'other_path': other_file,
                    'size_mb': 1.0,
                    'hash': 'abc123def456'
                })

            args = parse_args(['--delete-from', report_file])
            result = main(args)
            self.assertEqual(result, 0)
        finally:
            shutil.rmtree(temp_dir)

    def test_undo_missing_log(self):
        """--undo with missing log file returns error."""
        args = parse_args(['--undo', '/nonexistent/undo.json'])
        result = main(args)
        self.assertEqual(result, 1)

    def test_undo_valid_log(self):
        """--undo with valid log displays audit view."""
        # Create temporary undo log
        undo_data = [
            {
                'path': '/path/to/deleted/file.txt',
                'size_mb': 1.5,
                'hash': 'abc123def456abcdef123456abcdef12',
                'deleted_at': '2026-03-22T10:30:00'
            }
        ]
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(undo_data, f)
            temp_undo = f.name

        try:
            args = parse_args(['--undo', temp_undo])
            result = main(args)
            self.assertEqual(result, 0)
        finally:
            os.unlink(temp_undo)

    def test_undo_empty_log(self):
        """--undo with empty log returns success."""
        # Create temporary empty undo log
        undo_data = []
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(undo_data, f)
            temp_undo = f.name

        try:
            args = parse_args(['--undo', temp_undo])
            result = main(args)
            self.assertEqual(result, 0)
        finally:
            os.unlink(temp_undo)

    def test_undo_invalid_json(self):
        """--undo with invalid JSON returns error."""
        # Create temporary invalid JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{ invalid json")
            temp_undo = f.name

        try:
            args = parse_args(['--undo', temp_undo])
            result = main(args)
            self.assertEqual(result, 1)
        finally:
            os.unlink(temp_undo)

    @patch('diskcomp.cli.input', return_value='interactive')
    @patch('diskcomp.deletion.DeletionOrchestrator')
    def test_delete_from_interactive_mode(self, mock_orchestrator_class, mock_input):
        """--delete-from with interactive mode selection."""
        from diskcomp.types import DeletionResult

        temp_dir = tempfile.mkdtemp()

        try:
            # Create an "other" file to reference in the report
            other_file = os.path.join(temp_dir, 'file.txt')
            with open(other_file, 'w') as f:
                f.write("test content")

            # Create temporary report
            report_file = os.path.join(temp_dir, 'report.csv')
            with open(report_file, 'w') as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=['action', 'keep_path', 'other_path', 'size_mb', 'hash']
                )
                writer.writeheader()
                writer.writerow({
                    'action': 'DELETE_FROM_OTHER',
                    'keep_path': '/path/keep/file.txt',
                    'other_path': other_file,
                    'size_mb': 1.0,
                    'hash': 'abc123'
                })

            # Mock orchestrator
            mock_orchestrator = MagicMock()
            mock_orchestrator.interactive_mode.return_value = DeletionResult(
                mode='interactive',
                files_deleted=0,
                space_freed_mb=0.0,
                files_skipped=1,
                aborted=False,
                undo_log_path=None,
                errors=[]
            )
            mock_orchestrator_class.return_value = mock_orchestrator

            args = parse_args(['--delete-from', report_file])
            result = main(args)
            self.assertEqual(result, 0)
            # Verify orchestrator was created
            mock_orchestrator_class.assert_called_once()
        finally:
            shutil.rmtree(temp_dir)

    @patch('diskcomp.cli.input', return_value='batch')
    @patch('diskcomp.deletion.DeletionOrchestrator')
    def test_delete_from_batch_mode(self, mock_orchestrator_class, mock_input):
        """--delete-from with batch mode selection."""
        from diskcomp.types import DeletionResult

        temp_dir = tempfile.mkdtemp()

        try:
            # Create an "other" file to reference in the report
            other_file = os.path.join(temp_dir, 'file.txt')
            with open(other_file, 'w') as f:
                f.write("test content")

            # Create temporary report
            report_file = os.path.join(temp_dir, 'report.csv')
            with open(report_file, 'w') as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=['action', 'keep_path', 'other_path', 'size_mb', 'hash']
                )
                writer.writeheader()
                writer.writerow({
                    'action': 'DELETE_FROM_OTHER',
                    'keep_path': '/path/keep/file.txt',
                    'other_path': other_file,
                    'size_mb': 1.0,
                    'hash': 'abc123'
                })

            # Mock orchestrator
            mock_orchestrator = MagicMock()
            mock_orchestrator.batch_mode.return_value = DeletionResult(
                mode='batch',
                files_deleted=1,
                space_freed_mb=1.0,
                files_skipped=0,
                aborted=False,
                undo_log_path=os.path.join(temp_dir, 'diskcomp-undo-test.json'),
                errors=[]
            )
            mock_orchestrator_class.return_value = mock_orchestrator

            args = parse_args(['--delete-from', report_file])
            result = main(args)
            self.assertEqual(result, 0)
            # Verify batch_mode was called
            mock_orchestrator.batch_mode.assert_called_once()
        finally:
            shutil.rmtree(temp_dir)

    @patch('diskcomp.cli.input', return_value='')
    def test_delete_from_empty_mode_choice(self, mock_input):
        """--delete-from with empty mode choice (enter) exits without deletion."""
        temp_dir = tempfile.mkdtemp()

        try:
            # Create an "other" file to reference in the report
            other_file = os.path.join(temp_dir, 'file.txt')
            with open(other_file, 'w') as f:
                f.write("test content")

            # Create temporary report
            report_file = os.path.join(temp_dir, 'report.csv')
            with open(report_file, 'w') as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=['action', 'keep_path', 'other_path', 'size_mb', 'hash']
                )
                writer.writeheader()
                writer.writerow({
                    'action': 'DELETE_FROM_OTHER',
                    'keep_path': '/path/keep/file.txt',
                    'other_path': other_file,
                    'size_mb': 1.0,
                    'hash': 'abc123'
                })

            args = parse_args(['--delete-from', report_file])
            result = main(args)
            self.assertEqual(result, 0)
        finally:
            shutil.rmtree(temp_dir)

    @patch('diskcomp.cli.input', return_value='batch')
    @patch('diskcomp.deletion.DeletionOrchestrator')
    def test_delete_from_aborted_shows_message(self, mock_orchestrator_class, mock_input):
        """--delete-from shows abort message when aborted during batch."""
        from diskcomp.types import DeletionResult

        temp_dir = tempfile.mkdtemp()

        try:
            # Create "other" files
            other_file1 = os.path.join(temp_dir, 'file1.txt')
            with open(other_file1, 'w') as f:
                f.write("test content 1")

            other_file2 = os.path.join(temp_dir, 'file2.txt')
            with open(other_file2, 'w') as f:
                f.write("test content 2")

            # Create temporary report
            report_file = os.path.join(temp_dir, 'report.csv')
            with open(report_file, 'w') as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=['action', 'keep_path', 'other_path', 'size_mb', 'hash']
                )
                writer.writeheader()
                writer.writerow({
                    'action': 'DELETE_FROM_OTHER',
                    'keep_path': '/path/keep/file1.txt',
                    'other_path': other_file1,
                    'size_mb': 1.0,
                    'hash': 'abc123'
                })
                writer.writerow({
                    'action': 'DELETE_FROM_OTHER',
                    'keep_path': '/path/keep/file2.txt',
                    'other_path': other_file2,
                    'size_mb': 1.5,
                    'hash': 'def456'
                })

            # Mock orchestrator with aborted result
            mock_orchestrator = MagicMock()
            mock_orchestrator.batch_mode.return_value = DeletionResult(
                mode='batch',
                files_deleted=1,
                space_freed_mb=1.0,
                files_skipped=1,
                aborted=True,
                undo_log_path=os.path.join(temp_dir, 'diskcomp-undo-test.json'),
                errors=[]
            )
            mock_orchestrator_class.return_value = mock_orchestrator

            args = parse_args(['--delete-from', report_file])
            result = main(args)
            self.assertEqual(result, 0)
        finally:
            shutil.rmtree(temp_dir)


class TestPostScanWorkflow(unittest.TestCase):
    """Integration tests for post-scan navigation workflow with back navigation and state preservation."""

    def test_navigation_context_preserves_state_on_back(self):
        """Verify NavigationContext preserves state when navigating back."""
        # Create scan results dict with FileRecord objects in files_by_hash
        scan_results = {
            'files_by_hash': {
                'hash1': [
                    FileRecord(path='/folder/a/file1.txt', rel_path='file1.txt', size_bytes=1024),
                    FileRecord(path='/folder/b/file2.txt', rel_path='file2.txt', size_bytes=1024)
                ],
                'hash2': [
                    FileRecord(path='/folder/c/file3.txt', rel_path='file3.txt', size_bytes=1024)
                ]
            },
            'duplicates': [
                {'keep_path': '/folder/a/file1.txt', 'other_path': '/folder/b/file2.txt', 'size_mb': 1.0, 'hash': 'hash1'},
            ],
            'unique_in_keep': [],
            'unique_in_other': [],
            'summary': {}
        }

        # Create context with scan results
        context = NavigationContext(
            scan_results=scan_results,
            keep_path='/folder/a',
            other_path='/folder/b'
        )

        # Mock UI
        ui = MagicMock()
        ui.display_folder_list = MagicMock()
        ui.ok = MagicMock()
        ui.error = MagicMock()

        # Call show_folder_selection to populate selected_folders_skip
        with patch('builtins.input', side_effect=['1', 'b']):
            # First call: user selects folder 1
            result1 = show_folder_selection(context, ui)
            initial_folders = result1.selected_folders_skip.copy() if result1.selected_folders_skip else set()

            # Second call: user presses 'b' to go back (returns context unchanged)
            result2 = show_folder_selection(result1, ui)

        # Verify state was preserved across back navigation
        self.assertEqual(result2.selected_folders_skip, initial_folders, "Folder selection should be preserved on back navigation")

    def test_post_scan_menu_routes_to_folder_skip(self):
        """Verify run_post_scan_menu routes to show_folder_selection on option 1."""
        scan_results = {
            'files_by_hash': {
                'hash1': ['/path/file1.txt']
            },
            'duplicates': [],
            'unique_in_keep': [],
            'unique_in_other': [],
            'summary': {}
        }

        context = NavigationContext(scan_results=scan_results)
        ui = MagicMock()

        # Mock input and show_folder_selection
        with patch('builtins.input', side_effect=['1', '6']):
            with patch('diskcomp.cli.show_folder_selection', return_value=context):
                result = run_post_scan_menu(context, ui)

        # Verify result is 'skipped_deletion' (user chose option 6: exit)
        self.assertEqual(result, 'skipped_deletion')

    def test_post_scan_menu_routes_to_file_flagging(self):
        """Verify run_post_scan_menu routes to show_file_flagging on option 2."""
        scan_results = {
            'files_by_hash': {
                'hash1': ['/path/file1.txt']
            },
            'duplicates': [],
            'unique_in_keep': [],
            'unique_in_other': [],
            'summary': {}
        }

        context = NavigationContext(scan_results=scan_results)
        ui = MagicMock()

        # Mock input and show_file_flagging
        with patch('builtins.input', side_effect=['2', '6']):
            with patch('diskcomp.cli.show_file_flagging', return_value=context):
                result = run_post_scan_menu(context, ui)

        # Verify result is 'skipped_deletion' (user chose option 6: exit)
        self.assertEqual(result, 'skipped_deletion')

    def test_orchestrate_deletion_filters_flagged_files(self):
        """Verify orchestrate_deletion filters flagged files before deletion."""
        # Create scan results with duplicates
        scan_results = {
            'files_by_hash': {
                'hash1': [
                    FileRecord(path='/keep/file1.txt', rel_path='file1.txt', size_bytes=1048576),
                    FileRecord(path='/other/file1.txt', rel_path='file1.txt', size_bytes=1048576)
                ],
                'hash2': [
                    FileRecord(path='/keep/file2.txt', rel_path='file2.txt', size_bytes=1048576),
                    FileRecord(path='/other/file2.txt', rel_path='file2.txt', size_bytes=1048576)
                ]
            },
            'duplicates': [
                {'keep_path': '/keep/file1.txt', 'other_path': '/other/file1.txt', 'size_mb': 1.0, 'hash': 'hash1'},
                {'keep_path': '/keep/file2.txt', 'other_path': '/other/file2.txt', 'size_mb': 1.0, 'hash': 'hash2'}
            ],
            'unique_in_keep': [],
            'unique_in_other': [],
            'summary': {}
        }

        # Create context with one flagged file
        context = NavigationContext(
            scan_results=scan_results,
            flagged_files={'/other/file1.txt'},  # Flag file1 to exclude from deletion
            report_path='/tmp/report.csv'
        )

        ui = MagicMock()

        # Create a temp directory for undo log
        temp_dir = tempfile.mkdtemp()
        try:
            context.report_path = os.path.join(temp_dir, 'report.csv')

            # Mock DeletionOrchestrator to capture what it receives
            with patch('diskcomp.deletion.DeletionOrchestrator') as mock_orchestrator_class:
                mock_orchestrator = MagicMock()
                mock_orchestrator.batch_mode.return_value = DeletionResult(
                    mode='batch',
                    files_deleted=1,
                    space_freed_mb=1.0,
                    files_skipped=0,
                    aborted=False,
                    undo_log_path=os.path.join(temp_dir, 'undo.json'),
                    errors=[]
                )
                mock_orchestrator_class.return_value = mock_orchestrator

                # Call orchestrate_deletion
                result = orchestrate_deletion(context, ui, mode='batch')

                # Verify DeletionOrchestrator was called with filtered candidates
                # (should be called once, with only file2, not file1)
                mock_orchestrator_class.assert_called_once()
                call_args = mock_orchestrator_class.call_args
                candidates = call_args[1]['candidates'] if 'candidates' in call_args[1] else call_args[0][0]

                # File1 should be filtered out, only file2 should remain
                self.assertEqual(len(candidates), 1, "Only file2 should be in candidates (file1 is flagged)")
                self.assertEqual(candidates[0]['keep_path'], '/keep/file2.txt')

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_run_post_scan_menu_returns_deleted_on_batch_completion(self):
        """Verify run_post_scan_menu returns 'deleted' when batch deletion completes."""
        scan_results = {
            'files_by_hash': {},
            'duplicates': [
                {'keep_path': '/keep/file1.txt', 'other_path': '/other/file1.txt', 'size_mb': 1.0, 'hash': 'hash1'}
            ],
            'unique_in_keep': [],
            'unique_in_other': [],
            'summary': {}
        }

        context = NavigationContext(scan_results=scan_results)
        ui = MagicMock()

        # Mock input to select option 5 (batch deletion)
        with patch('builtins.input', return_value='5'):
            with patch('diskcomp.cli.orchestrate_deletion') as mock_orchestrate:
                # Return successful deletion result
                mock_orchestrate.return_value = DeletionResult(
                    mode='batch',
                    files_deleted=1,
                    space_freed_mb=1.0,
                    files_skipped=0,
                    aborted=False,
                    undo_log_path='/tmp/undo.json',
                    errors=[]
                )

                result = run_post_scan_menu(context, ui)

        # Verify result is 'deleted'
        self.assertEqual(result, 'deleted')


if __name__ == "__main__":
    unittest.main()
