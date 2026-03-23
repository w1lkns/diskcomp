"""Unit tests for diskcomp CLI module."""

import unittest
from unittest.mock import patch, MagicMock, call
from io import StringIO

from diskcomp.cli import parse_args, main, display_health_checks, _display_health_result
from diskcomp.types import HealthCheckResult


class TestCLIArgumentParsing(unittest.TestCase):
    """Test suite for argument parsing."""

    def test_parse_args_with_keep_other(self):
        """Test parse_args with --keep and --other flags."""
        args = parse_args(['--keep', '/mnt/a', '--other', '/mnt/b'])
        self.assertEqual(args.keep, '/mnt/a')
        self.assertEqual(args.other, '/mnt/b')

    def test_parse_args_without_keep_other(self):
        """Test parse_args without --keep/--other (interactive mode)."""
        args = parse_args([])
        self.assertIsNone(args.keep)
        self.assertIsNone(args.other)

    def test_parse_args_dry_run_flag(self):
        """Test parse_args with --dry-run flag."""
        args = parse_args(['--keep', '/mnt/a', '--other', '/mnt/b', '--dry-run'])
        self.assertTrue(args.dry_run)

    def test_parse_args_output_flag(self):
        """Test parse_args with --output flag."""
        args = parse_args(['--keep', '/mnt/a', '--other', '/mnt/b', '--output', '/tmp/report.csv'])
        self.assertEqual(args.output, '/tmp/report.csv')

    def test_parse_args_format_json(self):
        """Test parse_args with --format json."""
        args = parse_args(['--keep', '/mnt/a', '--other', '/mnt/b', '--format', 'json'])
        self.assertEqual(args.format, 'json')

    def test_parse_args_limit(self):
        """Test parse_args with --limit flag."""
        args = parse_args(['--keep', '/mnt/a', '--other', '/mnt/b', '--limit', '100'])
        self.assertEqual(args.limit, 100)


class TestInteractiveMode(unittest.TestCase):
    """Test suite for interactive mode in main()."""

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
    def test_main_no_args_calls_interactive_picker(
            self, mock_ui_factory, mock_picker, mock_isdir, mock_access,
            mock_health, mock_display_health, mock_scanner_class,
            mock_hasher_class, mock_classifier_class, mock_reporter_class,
            mock_input):
        """Test that main() with no args calls interactive_drive_picker()."""
        # Setup mocks
        mock_ui = MagicMock()
        mock_ui_factory.create.return_value = mock_ui

        mock_picker.return_value = {'keep': '/mnt/keep', 'other': '/mnt/other'}
        mock_isdir.return_value = True
        mock_access.return_value = True
        mock_display_health.return_value = True
        mock_input.return_value = 'n'  # User cancels

        # Create args with None values
        args = parse_args([])
        self.assertIsNone(args.keep)
        self.assertIsNone(args.other)

        # Call main
        result = main(args)

        # Verify
        self.assertEqual(result, 0)
        mock_picker.assert_called_once()

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
    def test_main_with_args_skips_interactive(
            self, mock_ui_factory, mock_picker, mock_isdir, mock_access,
            mock_health, mock_display_health, mock_scanner_class,
            mock_hasher_class, mock_classifier_class, mock_reporter_class,
            mock_input):
        """Test that main() with --keep/--other skips interactive mode."""
        # Setup mocks
        mock_ui = MagicMock()
        mock_ui_factory.create.return_value = mock_ui
        mock_isdir.return_value = True
        mock_access.return_value = True
        mock_display_health.return_value = True
        mock_input.return_value = 'n'  # User cancels

        # Create args with paths
        args = parse_args(['--keep', '/mnt/keep', '--other', '/mnt/other'])

        # Call main
        result = main(args)

        # Verify interactive picker was NOT called
        self.assertEqual(result, 0)
        mock_picker.assert_not_called()

    @patch('diskcomp.cli.input')
    @patch('diskcomp.cli.ReportWriter')
    @patch('diskcomp.cli.DuplicateClassifier')
    @patch('diskcomp.cli.FileHasher')
    @patch('diskcomp.cli.FileScanner')
    @patch('diskcomp.cli.display_health_checks')
    @patch('diskcomp.cli.os.access')
    @patch('diskcomp.cli.os.path.isdir')
    @patch('diskcomp.cli.interactive_drive_picker')
    @patch('diskcomp.cli.UIHandler')
    def test_main_interactive_picker_fails(
            self, mock_ui_factory, mock_picker, mock_isdir, mock_access,
            mock_display_health, mock_scanner_class, mock_hasher_class,
            mock_classifier_class, mock_reporter_class, mock_input):
        """Test that main() handles interactive picker failure."""
        # Setup mocks
        mock_ui = MagicMock()
        mock_ui_factory.create.return_value = mock_ui
        mock_picker.return_value = None  # Picker failed

        # Create args with no paths
        args = parse_args([])

        # Call main
        result = main(args)

        # Verify error code
        self.assertEqual(result, 1)
        mock_ui.close.assert_called_once()


class TestHealthCheckDisplay(unittest.TestCase):
    """Test suite for health check display."""

    def test_display_health_result_basic(self):
        """Test _display_health_result calls UI with correct data."""
        health = HealthCheckResult(
            mountpoint='/mnt/test',
            total_gb=500.0,
            used_gb=250.0,
            free_gb=250.0,
            fstype='APFS',
            is_writable=True,
            warnings=[],
            errors=[]
        )

        mock_ui = MagicMock()
        _display_health_result(mock_ui, "Test Drive", "/mnt/test", health)

        mock_ui.drive_header.assert_called_once_with("Test Drive", "/mnt/test")
        # Space, Filesystem, Writable each get a kv call
        kv_calls = [str(c) for c in mock_ui.kv.call_args_list]
        self.assertTrue(any("500.0" in s for s in kv_calls))
        self.assertTrue(any("APFS" in s for s in kv_calls))
        self.assertTrue(any("Yes" in s for s in kv_calls))

    def test_display_health_result_with_warnings(self):
        """Test _display_health_result passes warnings to UI."""
        health = HealthCheckResult(
            mountpoint='/mnt/test',
            total_gb=100.0,
            used_gb=50.0,
            free_gb=50.0,
            fstype='NTFS',
            is_writable=True,
            warnings=['NTFS on macOS may be read-only'],
            errors=[]
        )

        mock_ui = MagicMock()
        _display_health_result(mock_ui, "Test Drive", "/mnt/test", health)

        mock_ui.warn.assert_called()
        warn_args = str(mock_ui.warn.call_args_list)
        self.assertIn("NTFS on macOS may be read-only", warn_args)

    @patch('diskcomp.cli.check_drive_health')
    def test_display_health_checks_success(self, mock_health):
        """Test display_health_checks with both drives writable."""
        # Create matching health results for both drives
        health_result = HealthCheckResult(
            mountpoint='/mnt/test',
            total_gb=500.0,
            used_gb=250.0,
            free_gb=250.0,
            fstype='APFS',
            is_writable=True,
            warnings=[],
            errors=[]
        )

        mock_health.return_value = health_result
        mock_ui = MagicMock()

        with patch('sys.stderr', new=StringIO()):
            result = display_health_checks('/mnt/keep', '/mnt/other', mock_ui)

        self.assertTrue(result)
        self.assertEqual(mock_health.call_count, 2)

    @patch('diskcomp.cli.check_drive_health')
    def test_display_health_checks_with_warnings_passes(self, mock_health):
        """Test display_health_checks with warnings but still passes."""
        health_result = HealthCheckResult(
            mountpoint='/mnt/test',
            total_gb=500.0,
            used_gb=250.0,
            free_gb=250.0,
            fstype='NTFS',
            is_writable=True,
            warnings=['Low space warning'],
            errors=[]
        )

        mock_health.return_value = health_result
        mock_ui = MagicMock()

        with patch('sys.stderr', new=StringIO()):
            result = display_health_checks('/mnt/keep', '/mnt/other', mock_ui)

        # Should pass because keep is writable
        self.assertTrue(result)

    @patch('diskcomp.cli.check_drive_health')
    def test_display_health_checks_keep_not_writable(self, mock_health):
        """Test display_health_checks blocks when keep drive is not writable."""
        # Keep drive: not writable
        keep_health = HealthCheckResult(
            mountpoint='/mnt/keep',
            total_gb=500.0,
            used_gb=250.0,
            free_gb=250.0,
            fstype='NTFS',
            is_writable=False,
            warnings=[],
            errors=['Read-only']
        )

        # Other drive: writable
        other_health = HealthCheckResult(
            mountpoint='/mnt/other',
            total_gb=500.0,
            used_gb=250.0,
            free_gb=250.0,
            fstype='APFS',
            is_writable=True,
            warnings=[],
            errors=[]
        )

        mock_health.side_effect = [keep_health, other_health]
        mock_ui = MagicMock()

        with patch('sys.stderr', new=StringIO()):
            result = display_health_checks('/mnt/keep', '/mnt/other', mock_ui)

        self.assertFalse(result)

    @patch('diskcomp.cli.check_drive_health')
    def test_display_health_checks_other_not_writable_ok(self, mock_health):
        """Test display_health_checks allows read-only other drive."""
        # Keep drive: writable
        keep_health = HealthCheckResult(
            mountpoint='/mnt/keep',
            total_gb=500.0,
            used_gb=250.0,
            free_gb=250.0,
            fstype='APFS',
            is_writable=True,
            warnings=[],
            errors=[]
        )

        # Other drive: not writable (read-only is OK)
        other_health = HealthCheckResult(
            mountpoint='/mnt/other',
            total_gb=500.0,
            used_gb=250.0,
            free_gb=250.0,
            fstype='NTFS',
            is_writable=False,
            warnings=[],
            errors=['Read-only']
        )

        mock_health.side_effect = [keep_health, other_health]
        mock_ui = MagicMock()

        with patch('sys.stderr', new=StringIO()):
            result = display_health_checks('/mnt/keep', '/mnt/other', mock_ui)

        # Should pass because keep is writable and other read-only is OK
        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()
