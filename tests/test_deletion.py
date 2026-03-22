"""Unit tests for deletion module (UndoEntry, DeletionResult, ReportReader, UndoLog, DeletionOrchestrator)."""

import sys
import unittest
import tempfile
import json
import csv
import os
import shutil
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch, call
from io import StringIO

from diskcomp.types import UndoEntry, DeletionResult
from diskcomp.deletion import UndoLog, DeletionOrchestrator
from diskcomp.reporter import ReportReader


class TestUndoEntry(unittest.TestCase):
    """Test suite for UndoEntry dataclass."""

    def test_undo_entry_creation(self):
        """Test that UndoEntry can be instantiated with all fields."""
        timestamp = datetime.now().isoformat()
        entry = UndoEntry(
            path="/tmp/file.txt",
            size_mb=1.5,
            hash="abc123def456",
            deleted_at=timestamp
        )
        assert entry.path == "/tmp/file.txt", "Path should match"
        assert entry.size_mb == 1.5, "Size should match"
        assert entry.hash == "abc123def456", "Hash should match"
        assert entry.deleted_at == timestamp, "Timestamp should match"

    def test_undo_entry_all_fields(self):
        """Test that UndoEntry has all required fields."""
        timestamp = datetime.now().isoformat()
        entry = UndoEntry(
            path="/volumes/drive/subdir/file.pdf",
            size_mb=42.75,
            hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            deleted_at=timestamp
        )
        # Verify all fields exist and are accessible
        assert hasattr(entry, 'path'), "Should have path attribute"
        assert hasattr(entry, 'size_mb'), "Should have size_mb attribute"
        assert hasattr(entry, 'hash'), "Should have hash attribute"
        assert hasattr(entry, 'deleted_at'), "Should have deleted_at attribute"


class TestDeletionResult(unittest.TestCase):
    """Test suite for DeletionResult dataclass."""

    def test_deletion_result_creation(self):
        """Test that DeletionResult can be instantiated with all fields."""
        result = DeletionResult(
            mode="interactive",
            files_deleted=5,
            space_freed_mb=50.25,
            files_skipped=2,
            aborted=False,
            undo_log_path="/tmp/diskcomp-undo-20260322-120000.json",
            errors=[]
        )
        assert result.mode == "interactive", "Mode should match"
        assert result.files_deleted == 5, "Files deleted should match"
        assert result.space_freed_mb == 50.25, "Space freed should match"
        assert result.files_skipped == 2, "Files skipped should match"
        assert result.aborted is False, "Aborted should be False"
        assert result.undo_log_path == "/tmp/diskcomp-undo-20260322-120000.json", "Log path should match"
        assert result.errors == [], "Errors should be empty list"

    def test_deletion_result_with_errors(self):
        """Test that DeletionResult can have error list."""
        errors = ["Permission denied on file.txt", "File already deleted"]
        result = DeletionResult(
            mode="batch",
            files_deleted=10,
            space_freed_mb=100.0,
            files_skipped=0,
            aborted=False,
            undo_log_path="/tmp/undo.json",
            errors=errors
        )
        assert len(result.errors) == 2, "Should have two errors"
        assert "Permission denied" in result.errors[0], "Should contain error message"

    def test_deletion_result_aborted(self):
        """Test DeletionResult with aborted=True."""
        result = DeletionResult(
            mode="interactive",
            files_deleted=3,
            space_freed_mb=15.5,
            files_skipped=7,
            aborted=True,
            undo_log_path="/tmp/undo.json",
            errors=["User aborted"]
        )
        assert result.aborted is True, "Aborted should be True"
        assert result.files_deleted == 3, "Should record partial progress"

    def test_deletion_result_no_deletions(self):
        """Test DeletionResult when no files were deleted."""
        result = DeletionResult(
            mode="batch",
            files_deleted=0,
            space_freed_mb=0.0,
            files_skipped=10,
            aborted=False,
            undo_log_path=None,
            errors=[]
        )
        assert result.files_deleted == 0, "No files deleted"
        assert result.undo_log_path is None, "Log path should be None"


class TestReportReader(unittest.TestCase):
    """Test suite for ReportReader class."""

    def setUp(self):
        """Create temporary test directory and sample reports."""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test directory."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_load_csv_with_deletion_candidates(self):
        """Test loading CSV report and filtering for DELETE_FROM_OTHER."""
        csv_path = os.path.join(self.test_dir, "test-report.csv")
        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=['action', 'keep_path', 'other_path', 'size_mb', 'hash']
            )
            writer.writeheader()
            writer.writerow({
                'action': 'DELETE_FROM_OTHER',
                'keep_path': '/keep/file1.txt',
                'other_path': '/other/file1.txt',
                'size_mb': '10.5',
                'hash': 'hash1'
            })
            writer.writerow({
                'action': 'UNIQUE_IN_KEEP',
                'keep_path': '/keep/unique.txt',
                'other_path': None,
                'size_mb': '5.0',
                'hash': 'hash2'
            })
            writer.writerow({
                'action': 'DELETE_FROM_OTHER',
                'keep_path': '/keep/file2.txt',
                'other_path': '/other/file2.txt',
                'size_mb': '20.0',
                'hash': 'hash3'
            })

        candidates = ReportReader.load_csv(csv_path)
        assert len(candidates) == 2, "Should filter to 2 DELETE_FROM_OTHER rows"
        assert all(c['action'] == 'DELETE_FROM_OTHER' for c in candidates), "All should be DELETE_FROM_OTHER"
        assert candidates[0]['keep_path'] == '/keep/file1.txt', "First candidate should be file1"
        assert candidates[1]['keep_path'] == '/keep/file2.txt', "Second candidate should be file2"

    def test_load_json_with_deletion_candidates(self):
        """Test loading JSON report and filtering for DELETE_FROM_OTHER."""
        json_path = os.path.join(self.test_dir, "test-report.json")
        report_data = {
            'duplicates': [
                {
                    'action': 'DELETE_FROM_OTHER',
                    'keep_path': '/keep/file1.txt',
                    'other_path': '/other/file1.txt',
                    'size_mb': 10.5,
                    'hash': 'hash1'
                },
                {
                    'action': 'UNIQUE_IN_KEEP',
                    'keep_path': '/keep/unique.txt',
                    'other_path': None,
                    'size_mb': 5.0,
                    'hash': 'hash2'
                },
                {
                    'action': 'DELETE_FROM_OTHER',
                    'keep_path': '/keep/file2.txt',
                    'other_path': '/other/file2.txt',
                    'size_mb': 20.0,
                    'hash': 'hash3'
                }
            ],
            'summary': {}
        }
        with open(json_path, 'w') as f:
            json.dump(report_data, f)

        candidates = ReportReader.load_json(json_path)
        assert len(candidates) == 2, "Should filter to 2 DELETE_FROM_OTHER rows"
        assert all(c['action'] == 'DELETE_FROM_OTHER' for c in candidates), "All should be DELETE_FROM_OTHER"

    def test_load_auto_detects_json(self):
        """Test that load() auto-detects JSON format by extension."""
        json_path = os.path.join(self.test_dir, "test-report.json")
        report_data = {
            'duplicates': [
                {
                    'action': 'DELETE_FROM_OTHER',
                    'keep_path': '/keep/file.txt',
                    'other_path': '/other/file.txt',
                    'size_mb': 10.0,
                    'hash': 'hash1'
                }
            ]
        }
        with open(json_path, 'w') as f:
            json.dump(report_data, f)

        candidates = ReportReader.load(json_path)
        assert len(candidates) == 1, "Should load JSON automatically"
        assert candidates[0]['action'] == 'DELETE_FROM_OTHER'

    def test_load_auto_detects_csv(self):
        """Test that load() auto-detects CSV format by extension."""
        csv_path = os.path.join(self.test_dir, "test-report.csv")
        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=['action', 'keep_path', 'other_path', 'size_mb', 'hash']
            )
            writer.writeheader()
            writer.writerow({
                'action': 'DELETE_FROM_OTHER',
                'keep_path': '/keep/file.txt',
                'other_path': '/other/file.txt',
                'size_mb': '10.0',
                'hash': 'hash1'
            })

        candidates = ReportReader.load(csv_path)
        assert len(candidates) == 1, "Should load CSV automatically"

    def test_load_raises_filenotfounderror(self):
        """Test that load() raises FileNotFoundError for missing files."""
        nonexistent = os.path.join(self.test_dir, "does-not-exist.csv")
        with self.assertRaises(FileNotFoundError):
            ReportReader.load(nonexistent)

    def test_load_csv_raises_filenotfounderror(self):
        """Test that load_csv() raises FileNotFoundError."""
        nonexistent = os.path.join(self.test_dir, "missing.csv")
        with self.assertRaises(FileNotFoundError):
            ReportReader.load_csv(nonexistent)

    def test_load_json_raises_filenotfounderror(self):
        """Test that load_json() raises FileNotFoundError."""
        nonexistent = os.path.join(self.test_dir, "missing.json")
        with self.assertRaises(FileNotFoundError):
            ReportReader.load_json(nonexistent)

    def test_load_csv_returns_empty_list_if_no_candidates(self):
        """Test that load_csv() returns empty list if no DELETE_FROM_OTHER rows."""
        csv_path = os.path.join(self.test_dir, "empty-report.csv")
        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=['action', 'keep_path', 'other_path', 'size_mb', 'hash']
            )
            writer.writeheader()
            writer.writerow({
                'action': 'UNIQUE_IN_KEEP',
                'keep_path': '/keep/unique.txt',
                'other_path': None,
                'size_mb': '5.0',
                'hash': 'hash1'
            })

        candidates = ReportReader.load_csv(csv_path)
        assert candidates == [], "Should return empty list if no DELETE_FROM_OTHER"

    def test_load_json_returns_empty_list_if_no_candidates(self):
        """Test that load_json() returns empty list if no DELETE_FROM_OTHER rows."""
        json_path = os.path.join(self.test_dir, "empty-report.json")
        report_data = {
            'duplicates': [
                {
                    'action': 'UNIQUE_IN_KEEP',
                    'keep_path': '/keep/unique.txt',
                    'other_path': None,
                    'size_mb': 5.0,
                    'hash': 'hash1'
                }
            ]
        }
        with open(json_path, 'w') as f:
            json.dump(report_data, f)

        candidates = ReportReader.load_json(json_path)
        assert candidates == [], "Should return empty list if no DELETE_FROM_OTHER"


class TestUndoLog(unittest.TestCase):
    """Test suite for UndoLog class."""

    def setUp(self):
        """Create temporary test directory."""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test directory."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_undo_log_creation(self):
        """Test that UndoLog can be instantiated."""
        undo_log = UndoLog(self.test_dir)
        assert undo_log.report_dir == self.test_dir, "Report dir should match"
        assert undo_log.entries == [], "Entries should start empty"
        assert "diskcomp-undo-" in undo_log.file_path, "File path should have expected prefix"

    def test_undo_log_raises_on_invalid_dir(self):
        """Test that UndoLog raises ValueError for non-existent directory."""
        nonexistent = os.path.join(self.test_dir, "nonexistent")
        with self.assertRaises(ValueError):
            UndoLog(nonexistent)

    @unittest.skipIf(sys.platform == 'win32', "chmod does not restrict admin on Windows CI runners")
    def test_undo_log_raises_on_unwritable_dir(self):
        """Test that UndoLog raises ValueError for non-writable directory."""
        # Create a read-only directory
        readonly_dir = os.path.join(self.test_dir, "readonly")
        os.makedirs(readonly_dir)
        os.chmod(readonly_dir, 0o444)
        try:
            with self.assertRaises(ValueError):
                UndoLog(readonly_dir)
        finally:
            os.chmod(readonly_dir, 0o755)

    def test_undo_log_add(self):
        """Test that add() accumulates entries."""
        undo_log = UndoLog(self.test_dir)
        undo_log.add("/tmp/file1.txt", 10.5, "hash1")
        undo_log.add("/tmp/file2.txt", 20.0, "hash2")

        assert len(undo_log.entries) == 2, "Should have 2 entries"
        assert undo_log.entries[0].path == "/tmp/file1.txt", "First entry path should match"
        assert undo_log.entries[1].path == "/tmp/file2.txt", "Second entry path should match"

    def test_undo_log_write(self):
        """Test that write() creates JSON file with all entries."""
        undo_log = UndoLog(self.test_dir)
        undo_log.add("/tmp/file1.txt", 10.5, "hash1")
        undo_log.add("/tmp/file2.txt", 20.0, "hash2")
        undo_log.write()

        # Verify file was created
        assert os.path.exists(undo_log.file_path), "Undo log file should exist"

        # Verify JSON content
        with open(undo_log.file_path, 'r') as f:
            data = json.load(f)
            assert isinstance(data, list), "JSON should be an array"
            assert len(data) == 2, "Should have 2 entries in JSON"
            assert data[0]['path'] == "/tmp/file1.txt", "First entry path should match"
            assert data[1]['size_mb'] == 20.0, "Second entry size should match"

    def test_undo_log_write_is_noop_if_empty(self):
        """Test that write() is a no-op if entries list is empty."""
        undo_log = UndoLog(self.test_dir)
        undo_log.write()  # No entries added

        # Verify file was NOT created
        assert not os.path.exists(undo_log.file_path), "Undo log should not be created if empty"

    def test_undo_log_write_atomic(self):
        """Test that write() uses atomic write pattern."""
        undo_log = UndoLog(self.test_dir)
        undo_log.add("/tmp/file.txt", 10.0, "hash123")
        undo_log.write()

        # Verify no .tmp files left
        temp_files = [f for f in os.listdir(self.test_dir) if f.endswith('.tmp')]
        assert len(temp_files) == 0, "No temporary files should remain"

    def test_undo_log_entries_have_timestamps(self):
        """Test that entries have deleted_at timestamps."""
        undo_log = UndoLog(self.test_dir)
        before = datetime.now().isoformat()
        undo_log.add("/tmp/file.txt", 10.0, "hash")
        after = datetime.now().isoformat()

        entry = undo_log.entries[0]
        assert entry.deleted_at >= before, "Timestamp should be after entry creation"
        assert entry.deleted_at <= after, "Timestamp should be before now"

    def test_undo_log_write_includes_all_fields(self):
        """Test that JSON includes all required fields."""
        undo_log = UndoLog(self.test_dir)
        undo_log.add("/tmp/file.txt", 15.75, "abcdef123456")
        undo_log.write()

        with open(undo_log.file_path, 'r') as f:
            data = json.load(f)
            entry = data[0]
            assert 'path' in entry, "Should have path field"
            assert 'size_mb' in entry, "Should have size_mb field"
            assert 'hash' in entry, "Should have hash field"
            assert 'deleted_at' in entry, "Should have deleted_at field"
            assert entry['path'] == "/tmp/file.txt", "Path should match"
            assert entry['size_mb'] == 15.75, "Size should match"


class TestDeletionOrchestrator(unittest.TestCase):
    """Test suite for DeletionOrchestrator class."""

    def setUp(self):
        """Create temporary test directory and mock UI."""
        self.test_dir = tempfile.mkdtemp()
        self.mock_ui = Mock()
        self.mock_ui.start_deletion = Mock()
        self.mock_ui.on_file_deleted = Mock()
        self.mock_ui.close = Mock()

    def tearDown(self):
        """Clean up test directory."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def _create_test_file(self, filename: str, size_mb: float = 1.0) -> str:
        """Create a test file and return its path."""
        filepath = os.path.join(self.test_dir, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            # Write data to match size_mb
            size_bytes = int(size_mb * 1024 * 1024)
            f.write('x' * size_bytes)
        return filepath

    def test_deletion_orchestrator_initialization(self):
        """Test that DeletionOrchestrator can be instantiated."""
        candidates = [{'other_path': '/tmp/file.txt', 'size_mb': 10.0, 'hash': 'hash1'}]
        orchestrator = DeletionOrchestrator(candidates, self.mock_ui, os.path.join(self.test_dir, 'report.csv'))

        assert orchestrator.candidates == candidates, "Candidates should be stored"
        assert orchestrator.ui == self.mock_ui, "UI should be stored"
        assert orchestrator.report_dir == self.test_dir, "Report dir should be extracted"

    def test_interactive_mode_yes_deletes_file(self):
        """Test that choosing yes in interactive mode deletes file."""
        test_file = self._create_test_file('file1.txt', 1.0)
        candidates = [{'other_path': test_file, 'size_mb': 1.0, 'hash': 'hash123'}]
        orchestrator = DeletionOrchestrator(candidates, self.mock_ui, os.path.join(self.test_dir, 'report.csv'))

        with patch('builtins.input', return_value='y'):
            result = orchestrator.interactive_mode()

        assert result.files_deleted == 1, "Should have deleted 1 file"
        assert result.space_freed_mb == 1.0, "Should report 1.0 MB freed"
        assert result.aborted is False, "Should not be aborted"
        assert not os.path.exists(test_file), "File should be deleted"

    def test_interactive_mode_no_skips_file(self):
        """Test that choosing no in interactive mode skips file."""
        test_file = self._create_test_file('file2.txt', 1.0)
        candidates = [{'other_path': test_file, 'size_mb': 1.0, 'hash': 'hash123'}]
        orchestrator = DeletionOrchestrator(candidates, self.mock_ui, os.path.join(self.test_dir, 'report.csv'))

        with patch('builtins.input', return_value='n'):
            result = orchestrator.interactive_mode()

        assert result.files_deleted == 0, "Should not have deleted any files"
        assert result.files_skipped == 1, "Should have 1 skipped file"
        assert os.path.exists(test_file), "File should still exist"

    def test_interactive_mode_skip_option(self):
        """Test that skip option defers file for later."""
        test_file = self._create_test_file('file3.txt', 1.0)
        candidates = [{'other_path': test_file, 'size_mb': 1.0, 'hash': 'hash123'}]
        orchestrator = DeletionOrchestrator(candidates, self.mock_ui, os.path.join(self.test_dir, 'report.csv'))

        with patch('builtins.input', return_value='skip'):
            result = orchestrator.interactive_mode()

        assert result.files_deleted == 0, "Should not have deleted any files"
        assert result.files_skipped == 1, "Should have 1 skipped file"
        assert os.path.exists(test_file), "File should still exist"

    def test_interactive_mode_abort_stops_early(self):
        """Test that abort option stops workflow early."""
        file1 = self._create_test_file('file_a.txt', 1.0)
        file2 = self._create_test_file('file_b.txt', 1.0)
        candidates = [
            {'other_path': file1, 'size_mb': 1.0, 'hash': 'hash1'},
            {'other_path': file2, 'size_mb': 1.0, 'hash': 'hash2'},
        ]
        orchestrator = DeletionOrchestrator(candidates, self.mock_ui, os.path.join(self.test_dir, 'report.csv'))

        with patch('builtins.input', return_value='abort'):
            result = orchestrator.interactive_mode()

        assert result.files_deleted == 0, "Should not delete before abort"
        assert result.aborted is True, "Should be marked as aborted"
        assert os.path.exists(file1), "File 1 should still exist"
        assert os.path.exists(file2), "File 2 should still exist"

    def test_interactive_mode_undo_logged_before_delete(self):
        """Test that undo log entry is added before deletion."""
        test_file = self._create_test_file('file4.txt', 1.0)
        candidates = [{'other_path': test_file, 'size_mb': 1.0, 'hash': 'hash123'}]
        orchestrator = DeletionOrchestrator(candidates, self.mock_ui, os.path.join(self.test_dir, 'report.csv'))

        with patch('builtins.input', return_value='y'):
            # Spy on the undo_log.add method
            original_add = orchestrator.undo_log.add
            calls_sequence = []

            def track_add(*args, **kwargs):
                calls_sequence.append(('add', os.path.exists(test_file)))
                return original_add(*args, **kwargs)

            orchestrator.undo_log.add = track_add
            result = orchestrator.interactive_mode()

        # At the time of add(), the file should still exist (not deleted yet)
        assert len(calls_sequence) > 0, "add() should be called"
        assert calls_sequence[0][1] is True, "File should still exist when add() is called"

    def test_interactive_mode_keyboard_interrupt(self):
        """Test that KeyboardInterrupt returns aborted result."""
        test_file = self._create_test_file('file5.txt', 1.0)
        candidates = [{'other_path': test_file, 'size_mb': 1.0, 'hash': 'hash123'}]
        orchestrator = DeletionOrchestrator(candidates, self.mock_ui, os.path.join(self.test_dir, 'report.csv'))

        with patch('builtins.input', side_effect=KeyboardInterrupt()):
            result = orchestrator.interactive_mode()

        assert result.aborted is True, "Should be marked as aborted"
        assert os.path.exists(test_file), "File should still exist"

    def test_batch_mode_requires_delete_confirmation(self):
        """Test that batch mode requires exact 'DELETE' confirmation."""
        candidates = [{'other_path': '/tmp/file.txt', 'size_mb': 1.0, 'hash': 'hash123'}]
        orchestrator = DeletionOrchestrator(candidates, self.mock_ui, os.path.join(self.test_dir, 'report.csv'))

        with patch('builtins.input', return_value='yes'):
            result = orchestrator.batch_mode()

        assert result.aborted is False, "Should not be aborted on wrong confirmation — only real Ctrl+C sets aborted"
        assert result.files_deleted == 0, "No files should be deleted"
        assert result.files_skipped == len(candidates), "All files should be skipped"

    def test_batch_mode_executes_on_delete_confirmation(self):
        """Test that batch mode executes when 'DELETE' is typed exactly."""
        test_file = self._create_test_file('batch_file.txt', 1.5)
        candidates = [{'other_path': test_file, 'size_mb': 1.5, 'hash': 'hash123'}]
        orchestrator = DeletionOrchestrator(candidates, self.mock_ui, os.path.join(self.test_dir, 'report.csv'))

        with patch('builtins.input', return_value='DELETE'):
            result = orchestrator.batch_mode()

        assert result.files_deleted == 1, "Should delete 1 file"
        assert result.space_freed_mb == 1.5, "Should report 1.5 MB freed"
        assert result.aborted is False, "Should not be aborted"
        assert not os.path.exists(test_file), "File should be deleted"

    def test_batch_mode_dry_run_preview(self):
        """Test that batch mode shows dry-run preview."""
        test_file = self._create_test_file('preview_file.txt', 2.0)
        candidates = [{'other_path': test_file, 'size_mb': 2.0, 'hash': 'hash123'}]
        orchestrator = DeletionOrchestrator(candidates, self.mock_ui, os.path.join(self.test_dir, 'report.csv'))

        with patch('builtins.input', return_value='yes'):  # Not DELETE, so should abort after preview
            with patch('builtins.print') as mock_print:
                result = orchestrator.batch_mode()

        # Preview should have been printed before the confirmation prompt
        assert result.aborted is False, "Should not be aborted when DELETE not typed — only real Ctrl+C sets aborted"

    def test_batch_mode_calls_ui_start_deletion(self):
        """Test that batch mode calls ui.start_deletion()."""
        test_file = self._create_test_file('ui_test.txt', 1.0)
        candidates = [{'other_path': test_file, 'size_mb': 1.0, 'hash': 'hash123'}]
        orchestrator = DeletionOrchestrator(candidates, self.mock_ui, os.path.join(self.test_dir, 'report.csv'))

        with patch('builtins.input', return_value='DELETE'):
            result = orchestrator.batch_mode()

        self.mock_ui.start_deletion.assert_called_once_with(1)

    def test_batch_mode_calls_ui_on_file_deleted(self):
        """Test that batch mode calls ui.on_file_deleted() for each file."""
        test_file = self._create_test_file('ui_test2.txt', 1.0)
        candidates = [{'other_path': test_file, 'size_mb': 1.0, 'hash': 'hash123'}]
        orchestrator = DeletionOrchestrator(candidates, self.mock_ui, os.path.join(self.test_dir, 'report.csv'))

        with patch('builtins.input', return_value='DELETE'):
            result = orchestrator.batch_mode()

        self.mock_ui.on_file_deleted.assert_called_once()
        call_args = self.mock_ui.on_file_deleted.call_args[0]
        assert call_args[0] == 1, "Should pass current=1"
        assert call_args[1] == 1, "Should pass total=1"

    def test_batch_mode_keyboard_interrupt(self):
        """Test that KeyboardInterrupt in batch mode is handled."""
        test_file = self._create_test_file('batch_interrupt.txt', 1.0)
        candidates = [{'other_path': test_file, 'size_mb': 1.0, 'hash': 'hash123'}]
        orchestrator = DeletionOrchestrator(candidates, self.mock_ui, os.path.join(self.test_dir, 'report.csv'))

        with patch('builtins.input', side_effect=KeyboardInterrupt()):
            result = orchestrator.batch_mode()

        assert result.aborted is True, "Should be marked as aborted"
        self.mock_ui.close.assert_called_once()

    def test_batch_mode_calls_ui_close(self):
        """Test that batch mode calls ui.close() after execution."""
        test_file = self._create_test_file('close_test.txt', 1.0)
        candidates = [{'other_path': test_file, 'size_mb': 1.0, 'hash': 'hash123'}]
        orchestrator = DeletionOrchestrator(candidates, self.mock_ui, os.path.join(self.test_dir, 'report.csv'))

        with patch('builtins.input', return_value='DELETE'):
            result = orchestrator.batch_mode()

        self.mock_ui.close.assert_called_once()

    def test_batch_mode_undo_log_written(self):
        """Test that batch mode writes undo log."""
        test_file = self._create_test_file('undo_batch.txt', 1.0)
        candidates = [{'other_path': test_file, 'size_mb': 1.0, 'hash': 'hash123'}]
        orchestrator = DeletionOrchestrator(candidates, self.mock_ui, os.path.join(self.test_dir, 'report.csv'))

        with patch('builtins.input', return_value='DELETE'):
            result = orchestrator.batch_mode()

        assert result.undo_log_path is not None, "Should have undo log path"
        assert os.path.exists(result.undo_log_path), "Undo log file should exist"

    def test_batch_mode_multiple_files(self):
        """Test batch mode with multiple files."""
        file1 = self._create_test_file('multi1.txt', 1.0)
        file2 = self._create_test_file('multi2.txt', 2.0)
        file3 = self._create_test_file('multi3.txt', 3.0)
        candidates = [
            {'other_path': file1, 'size_mb': 1.0, 'hash': 'hash1'},
            {'other_path': file2, 'size_mb': 2.0, 'hash': 'hash2'},
            {'other_path': file3, 'size_mb': 3.0, 'hash': 'hash3'},
        ]
        orchestrator = DeletionOrchestrator(candidates, self.mock_ui, os.path.join(self.test_dir, 'report.csv'))

        with patch('builtins.input', return_value='DELETE'):
            result = orchestrator.batch_mode()

        assert result.files_deleted == 3, "Should delete all 3 files"
        assert result.space_freed_mb == 6.0, "Should free 6.0 MB"
        assert not os.path.exists(file1), "File 1 should be deleted"
        assert not os.path.exists(file2), "File 2 should be deleted"
        assert not os.path.exists(file3), "File 3 should be deleted"


class TestUIHandlerDeletionMethods(unittest.TestCase):
    """Test suite for UI deletion methods."""

    def setUp(self):
        """Set up test environment."""
        from diskcomp.ui import RICH_AVAILABLE
        self.rich_available = RICH_AVAILABLE

    def test_ansi_start_deletion(self):
        """Test ANSIProgressUI.start_deletion()."""
        from diskcomp.ui import UIHandler
        ui = UIHandler.create(force_ansi=True)

        with patch('builtins.print') as mock_print:
            ui.start_deletion(10)

        # Verify print was called (exact format depends on implementation)
        mock_print.assert_called_once()

    def test_ansi_on_file_deleted(self):
        """Test ANSIProgressUI.on_file_deleted()."""
        from diskcomp.ui import UIHandler
        ui = UIHandler.create(force_ansi=True)

        with patch('builtins.print') as mock_print:
            ui.on_file_deleted(5, 10, 25.5)

        mock_print.assert_called_once()
        output = mock_print.call_args[0][0]
        assert '5' in str(output), "Should show current count"
        assert '10' in str(output), "Should show total count"
        assert '25.5' in str(output), "Should show space freed"

    def test_rich_start_deletion_available(self):
        """Test RichProgressUI.start_deletion() if Rich is available."""
        if not self.rich_available:
            self.skipTest("Rich not available")

        from diskcomp.ui import UIHandler
        ui = UIHandler.create(force_ansi=False)

        ui.start_deletion(10)
        assert hasattr(ui, 'deletion_task_id'), "Should have deletion_task_id"

    def test_rich_on_file_deleted_available(self):
        """Test RichProgressUI.on_file_deleted() if Rich is available."""
        if not self.rich_available:
            self.skipTest("Rich not available")

        from diskcomp.ui import UIHandler
        ui = UIHandler.create(force_ansi=False)

        ui.start_deletion(10)
        ui.on_file_deleted(5, 10, 25.5)
        # Verify it doesn't raise


if __name__ == "__main__":
    unittest.main()
