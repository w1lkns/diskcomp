"""
Integration tests for scanner/hasher callbacks and CLI UI integration.

This module tests the callback wiring between business logic (scanner, hasher)
and the UI layer. Uses mocking to verify UI methods are called with correct
parameters without relying on actual terminal output.
"""

import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, call

from diskcomp.scanner import FileScanner
from diskcomp.hasher import FileHasher
from diskcomp.ui import UIHandler
from diskcomp.types import FileRecord


def create_test_files(directory: str, count: int) -> list:
    """
    Create test files in a directory.

    Args:
        directory: Path to directory where files will be created
        count: Number of test files to create (each >1KB)

    Returns:
        List of created file paths
    """
    files = []
    os.makedirs(directory, exist_ok=True)
    for i in range(count):
        filepath = os.path.join(directory, f"testfile_{i}.txt")
        # Create file with >1KB content
        with open(filepath, 'w') as f:
            f.write("x" * 2048)
        files.append(filepath)
    return files


class TestScannerCallback(unittest.TestCase):
    """Test scanner on_folder_done callback functionality."""

    def setUp(self):
        """Create temporary directory for test drives."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_root = self.temp_dir.name

    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()

    def test_scanner_calls_folder_callback(self):
        """Verify on_folder_done callback is invoked during scan."""
        # Create test files
        test_dir = os.path.join(self.test_root, "test_folder")
        create_test_files(test_dir, 3)

        # Mock callback
        callback = MagicMock()

        # Scan with callback
        scanner = FileScanner(self.test_root)
        result = scanner.scan(on_folder_done=callback)

        # Verify callback was called at least once
        self.assertGreater(callback.call_count, 0)

        # Verify callback received folder path and file count
        for args, kwargs in callback.call_args_list:
            folder_path, file_count = args
            self.assertIsInstance(folder_path, str)
            self.assertIsInstance(file_count, int)
            self.assertGreater(file_count, 0)

    def test_scanner_callback_multiple_folders(self):
        """Verify callback called for each folder in nested structure."""
        # Create nested folder structure
        dir1 = os.path.join(self.test_root, "folder1")
        dir2 = os.path.join(self.test_root, "folder2")
        create_test_files(dir1, 2)
        create_test_files(dir2, 2)

        # Mock callback
        callback = MagicMock()

        # Scan with callback
        scanner = FileScanner(self.test_root)
        result = scanner.scan(on_folder_done=callback)

        # Verify callback called for each folder
        self.assertGreaterEqual(callback.call_count, 2)

    def test_scanner_no_callback(self):
        """Verify scanner works without callback (backward compatibility)."""
        # Create test files
        test_dir = os.path.join(self.test_root, "test_folder")
        create_test_files(test_dir, 3)

        # Scan without callback
        scanner = FileScanner(self.test_root)
        result = scanner.scan()

        # Verify scan succeeded
        self.assertGreater(result.file_count, 0)

    def test_scanner_callback_receives_correct_counts(self):
        """Verify callback file counts match actual files collected."""
        # Create test files
        test_dir = os.path.join(self.test_root, "test_folder")
        files_created = create_test_files(test_dir, 5)

        # Mock callback
        callback = MagicMock()

        # Scan with callback
        scanner = FileScanner(self.test_root)
        result = scanner.scan(on_folder_done=callback)

        # Verify callback was called with correct count
        # Find the call with the test_folder
        found_test_folder = False
        for args, kwargs in callback.call_args_list:
            folder_path, file_count = args
            if "test_folder" in folder_path:
                self.assertEqual(file_count, 5)
                found_test_folder = True
        self.assertTrue(found_test_folder, "test_folder callback not found")


class TestHasherCallback(unittest.TestCase):
    """Test hasher on_file_hashed callback functionality."""

    def setUp(self):
        """Create temporary directory for test files."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_root = self.temp_dir.name

    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()

    def test_hasher_hash_files_method_exists(self):
        """Verify hash_files method is callable."""
        hasher = FileHasher()
        self.assertTrue(callable(hasher.hash_files))

    def test_hasher_calls_file_callback(self):
        """Verify on_file_hashed callback is invoked for each file."""
        # Create test files
        files = create_test_files(self.test_root, 5)
        records = [FileRecord(
            path=f,
            rel_path=os.path.basename(f),
            size_bytes=os.path.getsize(f),
            hash=None,
            mtime=0.0,
            error=None
        ) for f in files]

        # Mock callback
        callback = MagicMock()

        # Hash files with callback
        hasher = FileHasher()
        result = hasher.hash_files(records, on_file_hashed=callback)

        # Verify callback called 5 times
        self.assertEqual(callback.call_count, 5)

    def test_hasher_callback_speed_calculation(self):
        """Verify speed_mbps is calculated and positive."""
        # Create test files
        files = create_test_files(self.test_root, 3)
        records = [FileRecord(
            path=f,
            rel_path=os.path.basename(f),
            size_bytes=os.path.getsize(f),
            hash=None,
            mtime=0.0,
            error=None
        ) for f in files]

        # Mock callback
        callback = MagicMock()

        # Hash files with callback
        hasher = FileHasher()
        result = hasher.hash_files(records, on_file_hashed=callback)

        # Verify speed was passed and is reasonable
        for args, kwargs in callback.call_args_list:
            current, total, speed_mbps, eta_secs = args
            self.assertIsInstance(speed_mbps, float)
            self.assertGreaterEqual(speed_mbps, 0)

    def test_hasher_callback_eta_calculation(self):
        """Verify eta_secs is calculated and non-negative."""
        # Create test files
        files = create_test_files(self.test_root, 3)
        records = [FileRecord(
            path=f,
            rel_path=os.path.basename(f),
            size_bytes=os.path.getsize(f),
            hash=None,
            mtime=0.0,
            error=None
        ) for f in files]

        # Mock callback
        callback = MagicMock()

        # Hash files with callback
        hasher = FileHasher()
        result = hasher.hash_files(records, on_file_hashed=callback)

        # Verify ETA was passed and is non-negative integer
        for args, kwargs in callback.call_args_list:
            current, total, speed_mbps, eta_secs = args
            self.assertIsInstance(eta_secs, int)
            self.assertGreaterEqual(eta_secs, 0)

    def test_hasher_callback_index_sequence(self):
        """Verify callback receives sequential indices 1..N."""
        # Create test files
        files = create_test_files(self.test_root, 5)
        records = [FileRecord(
            path=f,
            rel_path=os.path.basename(f),
            size_bytes=os.path.getsize(f),
            hash=None,
            mtime=0.0,
            error=None
        ) for f in files]

        # Mock callback
        callback = MagicMock()

        # Hash files with callback
        hasher = FileHasher()
        result = hasher.hash_files(records, on_file_hashed=callback)

        # Verify indices are sequential
        expected_indices = list(range(1, 6))
        actual_indices = [args[0] for args, kwargs in callback.call_args_list]
        self.assertEqual(actual_indices, expected_indices)

    def test_hasher_no_callback(self):
        """Verify hasher works without callback."""
        # Create test files
        files = create_test_files(self.test_root, 3)
        records = [FileRecord(
            path=f,
            rel_path=os.path.basename(f),
            size_bytes=os.path.getsize(f),
            hash=None,
            mtime=0.0,
            error=None
        ) for f in files]

        # Hash files without callback
        hasher = FileHasher()
        result = hasher.hash_files(records)

        # Verify all files were hashed
        self.assertEqual(len(result), 3)
        for record in result:
            self.assertIsNotNone(record.hash)


class TestCLIUI(unittest.TestCase):
    """Test CLI UI integration with scanner and hasher."""

    def setUp(self):
        """Create temporary directories for test drives."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_root = self.temp_dir.name
        self.keep_dir = os.path.join(self.test_root, "keep")
        self.other_dir = os.path.join(self.test_root, "other")
        create_test_files(self.keep_dir, 3)
        create_test_files(self.other_dir, 3)

    def tearDown(self):
        """Clean up temporary directories."""
        self.temp_dir.cleanup()

    def test_cli_ui_handler_created(self):
        """Verify UIHandler.create() returns a UI instance."""
        ui = UIHandler.create()
        self.assertIsNotNone(ui)
        self.assertTrue(hasattr(ui, 'start_scan'))
        self.assertTrue(hasattr(ui, 'on_folder_done'))
        self.assertTrue(hasattr(ui, 'start_hash'))
        self.assertTrue(hasattr(ui, 'on_file_hashed'))
        self.assertTrue(hasattr(ui, 'show_summary'))
        self.assertTrue(hasattr(ui, 'close'))

    def test_cli_ui_start_scan_called(self):
        """Verify main() calls ui.start_scan() during scanning."""
        from diskcomp.cli import main

        with patch('diskcomp.cli.UIHandler.create') as mock_create:
            mock_ui = MagicMock()
            mock_create.return_value = mock_ui

            with patch('diskcomp.cli.input', return_value='y'):
                # Run CLI with test directories
                args = [
                    '--keep', self.keep_dir,
                    '--other', self.other_dir,
                    '--dry-run'
                ]
                from diskcomp.cli import parse_args
                parsed = parse_args(args)
                result = main(parsed)

                # Verify start_scan was called
                self.assertEqual(mock_ui.start_scan.call_count, 2)

    def test_cli_ui_on_folder_done_called(self):
        """Verify main() calls ui.on_folder_done() during scan."""
        from diskcomp.cli import main

        with patch('diskcomp.cli.UIHandler.create') as mock_create:
            mock_ui = MagicMock()
            mock_create.return_value = mock_ui

            with patch('diskcomp.cli.input', return_value='y'):
                # Run CLI with test directories
                args = [
                    '--keep', self.keep_dir,
                    '--other', self.other_dir,
                    '--dry-run'
                ]
                from diskcomp.cli import parse_args
                parsed = parse_args(args)
                result = main(parsed)

                # Verify on_folder_done was called
                self.assertGreater(mock_ui.on_folder_done.call_count, 0)

    def test_cli_ui_start_hash_called(self):
        """Verify main() calls ui.start_hash() before hashing."""
        from diskcomp.cli import main

        with patch('diskcomp.cli.UIHandler.create') as mock_create:
            mock_ui = MagicMock()
            mock_create.return_value = mock_ui

            with patch('diskcomp.cli.input', return_value='y'):
                # Run CLI without dry-run to trigger hashing
                args = [
                    '--keep', self.keep_dir,
                    '--other', self.other_dir
                ]
                from diskcomp.cli import parse_args
                parsed = parse_args(args)
                result = main(parsed)

                # Verify start_hash was called
                self.assertGreater(mock_ui.start_hash.call_count, 0)

    def test_cli_ui_on_file_hashed_called(self):
        """Verify main() calls ui.on_file_hashed() during hashing."""
        from diskcomp.cli import main

        with patch('diskcomp.cli.UIHandler.create') as mock_create:
            mock_ui = MagicMock()
            mock_create.return_value = mock_ui

            with patch('diskcomp.cli.input', return_value='y'):
                # Run CLI without dry-run to trigger hashing
                args = [
                    '--keep', self.keep_dir,
                    '--other', self.other_dir
                ]
                from diskcomp.cli import parse_args
                parsed = parse_args(args)
                result = main(parsed)

                # Verify on_file_hashed was called
                self.assertGreater(mock_ui.on_file_hashed.call_count, 0)

    def test_cli_ui_show_summary_called(self):
        """Verify main() calls ui.show_summary() with correct stats."""
        from diskcomp.cli import main

        with patch('diskcomp.cli.UIHandler.create') as mock_create:
            mock_ui = MagicMock()
            mock_create.return_value = mock_ui

            with patch('diskcomp.cli.input', return_value='y'):
                # Run CLI without dry-run
                args = [
                    '--keep', self.keep_dir,
                    '--other', self.other_dir
                ]
                from diskcomp.cli import parse_args
                parsed = parse_args(args)
                result = main(parsed)

                # Verify show_summary was called
                mock_ui.show_summary.assert_called_once()

                # Verify arguments
                call_args = mock_ui.show_summary.call_args
                self.assertIn('duplicates_mb', call_args.kwargs)
                self.assertIn('duplicates_count', call_args.kwargs)
                self.assertIn('unique_keep_mb', call_args.kwargs)
                self.assertIn('unique_keep_count', call_args.kwargs)
                self.assertIn('unique_other_mb', call_args.kwargs)
                self.assertIn('unique_other_count', call_args.kwargs)
                self.assertIn('report_path', call_args.kwargs)

    def test_cli_ui_close_called(self):
        """Verify main() calls ui.close() at end."""
        from diskcomp.cli import main

        with patch('diskcomp.cli.UIHandler.create') as mock_create:
            mock_ui = MagicMock()
            mock_create.return_value = mock_ui

            with patch('diskcomp.cli.input', return_value='y'):
                # Run CLI without dry-run
                args = [
                    '--keep', self.keep_dir,
                    '--other', self.other_dir,
                    '--dry-run'
                ]
                from diskcomp.cli import parse_args
                parsed = parse_args(args)
                result = main(parsed)

                # Verify close was called
                mock_ui.close.assert_called()


if __name__ == '__main__':
    unittest.main()
