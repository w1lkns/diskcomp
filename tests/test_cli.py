"""Unit tests for diskcomp CLI module."""

import unittest
from unittest.mock import patch, MagicMock, call
from io import StringIO

from diskcomp.cli import (
    parse_args, main, display_health_checks, _display_health_result,
    parse_size_value, show_first_run_menu, show_help_guide,
    show_plain_language_summary, show_next_steps, show_action_menu
)
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

    def test_parse_args_min_size(self):
        """Test parse_args with --min-size flag."""
        args = parse_args(['--keep', '/mnt/a', '--other', '/mnt/b', '--min-size', '10MB'])
        self.assertEqual(args.min_size, '10MB')

    def test_parse_args_min_size_bytes(self):
        """Test parse_args with --min-size as plain bytes."""
        args = parse_args(['--keep', '/mnt/a', '--other', '/mnt/b', '--min-size', '1024'])
        self.assertEqual(args.min_size, '1024')

    def test_parse_args_min_size_default(self):
        """Test parse_args defaults min_size to None."""
        args = parse_args(['--keep', '/mnt/a', '--other', '/mnt/b'])
        self.assertIsNone(args.min_size)


class TestInteractiveMode(unittest.TestCase):
    """Test suite for interactive mode in main()."""

    @patch('diskcomp.cli.show_first_run_menu')
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
            mock_input, mock_menu):
        """Test that main() with no args calls interactive_drive_picker()."""
        # Setup mocks
        mock_ui = MagicMock()
        mock_ui_factory.create.return_value = mock_ui

        mock_menu.return_value = 'two_drives'  # Select two-drives from menu
        mock_picker.return_value = {'keep': '/mnt/keep', 'other': '/mnt/other'}
        mock_isdir.return_value = True
        mock_access.return_value = True
        mock_display_health.return_value = True
        mock_input.return_value = 'n'  # User cancels at scan confirmation

        # Create args with None values
        args = parse_args([])
        self.assertIsNone(args.keep)
        self.assertIsNone(args.other)

        # Call main
        result = main(args)

        # Verify
        self.assertEqual(result, 0)
        mock_picker.assert_called_once()

    @patch('diskcomp.cli.show_first_run_menu')
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
            mock_input, mock_menu):
        """Test that main() with --keep/--other skips interactive mode."""
        # Setup mocks
        mock_ui = MagicMock()
        mock_ui_factory.create.return_value = mock_ui
        mock_isdir.return_value = True
        mock_access.return_value = True
        mock_display_health.return_value = True
        mock_input.return_value = 'n'  # User cancels at scan confirmation

        # Create args with paths
        args = parse_args(['--keep', '/mnt/keep', '--other', '/mnt/other'])

        # Call main
        result = main(args)

        # Verify interactive picker was NOT called
        # (menu should not be shown because we have explicit paths)
        self.assertEqual(result, 0)
        mock_picker.assert_not_called()
        mock_menu.assert_not_called()

    @patch('diskcomp.cli.show_first_run_menu')
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
            mock_classifier_class, mock_reporter_class, mock_input, mock_menu):
        """Test that main() handles interactive picker failure."""
        # Setup mocks
        mock_ui = MagicMock()
        mock_ui_factory.create.return_value = mock_ui
        mock_menu.return_value = 'two_drives'  # Select two-drives from menu
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

    @patch('diskcomp.cli.sys.platform', 'darwin')
    @patch('diskcomp.cli.get_fix_instructions')
    def test_display_health_result_ntfs_on_macos(self, mock_fix_instr):
        """Test _display_health_result shows NTFS callout on macOS."""
        mock_fix_instr.return_value = "Install ntfs-3g: brew install macfuse ntfs-3g"

        health = HealthCheckResult(
            mountpoint='/Volumes/NTFS',
            total_gb=500.0,
            used_gb=250.0,
            free_gb=250.0,
            fstype='NTFS',
            is_writable=False,
            warnings=[],
            errors=[]
        )

        mock_ui = MagicMock()
        _display_health_result(mock_ui, "NTFS Drive", "/Volumes/NTFS", health)

        # Verify the NTFS callout was displayed
        warn_calls = [str(c) for c in mock_ui.warn.call_args_list]
        self.assertTrue(any("NTFS on darwin" in s for s in warn_calls))
        self.assertTrue(any("read-only" in s for s in warn_calls))
        self.assertTrue(any("Files cannot be deleted" in s for s in warn_calls))

    @patch('diskcomp.cli.sys.platform', 'linux')
    @patch('diskcomp.cli.get_fix_instructions')
    def test_display_health_result_ntfs_on_linux(self, mock_fix_instr):
        """Test _display_health_result shows NTFS callout on Linux."""
        mock_fix_instr.return_value = "Install ntfs-3g: sudo apt install ntfs-3g"

        health = HealthCheckResult(
            mountpoint='/mnt/ntfs',
            total_gb=1000.0,
            used_gb=500.0,
            free_gb=500.0,
            fstype='NTFS',
            is_writable=False,
            warnings=[],
            errors=[]
        )

        mock_ui = MagicMock()
        _display_health_result(mock_ui, "NTFS Drive", "/mnt/ntfs", health)

        # Verify the NTFS callout was displayed
        warn_calls = [str(c) for c in mock_ui.warn.call_args_list]
        self.assertTrue(any("NTFS on linux" in s for s in warn_calls))
        self.assertTrue(any("read-only" in s for s in warn_calls))
        self.assertTrue(any("Files cannot be deleted" in s for s in warn_calls))

    @patch('diskcomp.cli.sys.platform', 'win32')
    @patch('diskcomp.cli.get_fix_instructions')
    def test_display_health_result_ntfs_on_windows(self, mock_fix_instr):
        """Test _display_health_result does NOT show NTFS callout on Windows."""
        health = HealthCheckResult(
            mountpoint='D:\\',
            total_gb=500.0,
            used_gb=250.0,
            free_gb=250.0,
            fstype='NTFS',
            is_writable=True,
            warnings=[],
            errors=[]
        )

        mock_ui = MagicMock()
        _display_health_result(mock_ui, "NTFS Drive", "D:\\", health)

        # Verify the NTFS callout was NOT displayed
        warn_calls = [str(c) for c in mock_ui.warn.call_args_list]
        self.assertFalse(any("NTFS on win32" in s for s in warn_calls))
        self.assertFalse(any("NTFS on" in s for s in warn_calls))

    @patch('diskcomp.cli.sys.platform', 'darwin')
    @patch('diskcomp.cli.get_fix_instructions')
    def test_display_health_result_ext4_on_macos(self, mock_fix_instr):
        """Test _display_health_result does NOT show NTFS callout for ext4 on macOS."""
        health = HealthCheckResult(
            mountpoint='/Volumes/ext4',
            total_gb=500.0,
            used_gb=250.0,
            free_gb=250.0,
            fstype='ext4',
            is_writable=False,
            warnings=[],
            errors=[]
        )

        mock_ui = MagicMock()
        _display_health_result(mock_ui, "ext4 Drive", "/Volumes/ext4", health)

        # Verify the NTFS callout was NOT displayed for non-NTFS filesystem
        warn_calls = [str(c) for c in mock_ui.warn.call_args_list]
        self.assertFalse(any("NTFS on" in s for s in warn_calls))


class TestParseSize(unittest.TestCase):
    """Test suite for parse_size_value helper function."""

    def test_parse_size_value_bytes(self):
        """Test parse_size_value with plain bytes."""
        self.assertEqual(parse_size_value("1024"), 1024)
        self.assertEqual(parse_size_value("0"), 0)

    def test_parse_size_value_kb(self):
        """Test parse_size_value with KB suffix."""
        self.assertEqual(parse_size_value("500KB"), 512000)
        self.assertEqual(parse_size_value("1KB"), 1024)

    def test_parse_size_value_mb(self):
        """Test parse_size_value with MB suffix."""
        self.assertEqual(parse_size_value("10MB"), 10485760)
        self.assertEqual(parse_size_value("1MB"), 1048576)

    def test_parse_size_value_gb(self):
        """Test parse_size_value with GB suffix."""
        self.assertEqual(parse_size_value("1.5GB"), 1610612736)
        self.assertEqual(parse_size_value("1GB"), 1073741824)

    def test_parse_size_value_case_insensitive(self):
        """Test parse_size_value with case-insensitive suffixes."""
        self.assertEqual(parse_size_value("10mb"), 10485760)
        self.assertEqual(parse_size_value("500kb"), 512000)
        self.assertEqual(parse_size_value("1gb"), 1073741824)

    def test_parse_size_value_with_spaces(self):
        """Test parse_size_value with leading/trailing spaces."""
        self.assertEqual(parse_size_value("  1024  "), 1024)
        self.assertEqual(parse_size_value("  10MB  "), 10485760)

    def test_parse_size_value_invalid(self):
        """Test parse_size_value raises ValueError on invalid input."""
        with self.assertRaises(ValueError):
            parse_size_value("xyz")
        with self.assertRaises(ValueError):
            parse_size_value("10XB")
        with self.assertRaises(ValueError):
            parse_size_value("")


class TestFirstRunMenu(unittest.TestCase):
    """Test suite for show_first_run_menu function."""

    @patch('diskcomp.cli.input')
    def test_show_first_run_menu_option_1(self, mock_input):
        """Test show_first_run_menu returns 'two_drives' on input '1'."""
        mock_input.return_value = '1'
        result = show_first_run_menu()
        self.assertEqual(result, 'two_drives')

    @patch('diskcomp.cli.input')
    def test_show_first_run_menu_option_2(self, mock_input):
        """Test show_first_run_menu returns 'single_drive' on input '2'."""
        mock_input.return_value = '2'
        result = show_first_run_menu()
        self.assertEqual(result, 'single_drive')

    @patch('diskcomp.cli.input')
    def test_show_first_run_menu_option_3(self, mock_input):
        """Test show_first_run_menu returns 'help' on input '3'."""
        mock_input.return_value = '3'
        result = show_first_run_menu()
        self.assertEqual(result, 'help')

    @patch('diskcomp.cli.input')
    def test_show_first_run_menu_option_4(self, mock_input):
        """Test show_first_run_menu returns 'quit' on input '4'."""
        mock_input.return_value = '4'
        result = show_first_run_menu()
        self.assertEqual(result, 'quit')

    @patch('diskcomp.cli.input')
    def test_show_first_run_menu_invalid_then_valid(self, mock_input):
        """Test show_first_run_menu retries on invalid input then returns valid choice."""
        mock_input.side_effect = ['0', '5', 'x', '1']
        result = show_first_run_menu()
        self.assertEqual(result, 'two_drives')
        # Should have been called 4 times (3 invalid + 1 valid)
        self.assertEqual(mock_input.call_count, 4)

    @patch('diskcomp.cli.input')
    def test_show_first_run_menu_whitespace_stripped(self, mock_input):
        """Test show_first_run_menu handles whitespace in input."""
        mock_input.return_value = '  2  '
        result = show_first_run_menu()
        self.assertEqual(result, 'single_drive')

    @patch('sys.stdout', new_callable=StringIO)
    @patch('diskcomp.cli.input')
    def test_show_first_run_menu_displays_menu(self, mock_input, mock_stdout):
        """Test show_first_run_menu displays the menu text."""
        mock_input.return_value = '1'
        show_first_run_menu()
        output = mock_stdout.getvalue()
        # Check for menu options
        self.assertIn('What would you like to do?', output)
        self.assertIn('Compare two drives', output)
        self.assertIn('Clean up a single drive', output)
        self.assertIn('Help', output)
        self.assertIn('Quit', output)


class TestHelpGuide(unittest.TestCase):
    """Test suite for show_help_guide function."""

    @patch('sys.stdout', new_callable=StringIO)
    def test_show_help_guide_output(self, mock_stdout):
        """Test show_help_guide displays guide text."""
        show_help_guide()
        output = mock_stdout.getvalue()
        # Check for key phrases from the help guide
        self.assertIn('diskcomp', output)
        self.assertIn('Two modes', output)
        self.assertIn('safety', output)
        self.assertIn('Compare two drives', output)
        self.assertIn('Clean up a single drive', output)

    @patch('sys.stdout', new_callable=StringIO)
    def test_show_help_guide_includes_safety_facts(self, mock_stdout):
        """Test show_help_guide includes three safety facts."""
        show_help_guide()
        output = mock_stdout.getvalue()
        # Check for safety-related text
        self.assertIn('explicit confirmation', output)
        self.assertIn('undo log', output)
        self.assertIn('read-only', output)

    @patch('sys.stdout', new_callable=StringIO)
    def test_show_help_guide_includes_all_modes(self, mock_stdout):
        """Test show_help_guide mentions both modes."""
        show_help_guide()
        output = mock_stdout.getvalue()
        self.assertIn('two drives', output)
        self.assertIn('single drive', output)


class TestPlainLanguageSummary(unittest.TestCase):
    """Test suite for show_plain_language_summary function."""

    @patch('sys.stdout', new_callable=StringIO)
    def test_show_plain_language_summary_with_duplicates(self, mock_stdout):
        """Test show_plain_language_summary displays correctly with duplicates."""
        summary = {
            'duplicate_count': 50,
            'duplicate_size_mb': 10.5
        }
        show_plain_language_summary(summary, mode='two_drives', keep_label='Keep', other_label='Backup')
        output = mock_stdout.getvalue()
        self.assertIn('Found 50 duplicates', output)
        self.assertIn('10.5 MB', output)
        self.assertIn('Backup', output)
        self.assertIn('Ready to review?', output)

    @patch('sys.stdout', new_callable=StringIO)
    def test_show_plain_language_summary_zero_duplicates_two_drives(self, mock_stdout):
        """Test show_plain_language_summary with zero duplicates (two-drive mode)."""
        summary = {
            'duplicate_count': 0,
            'duplicate_size_mb': 0.0
        }
        show_plain_language_summary(summary, mode='two_drives')
        output = mock_stdout.getvalue()
        self.assertIn('No duplicates found', output)
        self.assertIn('Both drives are already clean', output)

    @patch('sys.stdout', new_callable=StringIO)
    def test_show_plain_language_summary_zero_duplicates_single_drive(self, mock_stdout):
        """Test show_plain_language_summary with zero duplicates (single-drive mode)."""
        summary = {
            'duplicate_count': 0,
            'duplicate_size_mb': 0.0
        }
        show_plain_language_summary(summary, mode='single_drive')
        output = mock_stdout.getvalue()
        self.assertIn('No duplicates found', output)
        self.assertIn('This drive has no redundant files', output)

    @patch('sys.stdout', new_callable=StringIO)
    def test_show_plain_language_summary_uses_gb_for_large(self, mock_stdout):
        """Test show_plain_language_summary converts MB to GB for values >= 1000 MB."""
        summary = {
            'duplicate_count': 100,
            'duplicate_size_mb': 2500.0
        }
        show_plain_language_summary(summary, mode='two_drives', other_label='External')
        output = mock_stdout.getvalue()
        self.assertIn('Found 100 duplicates', output)
        self.assertIn('2.5 GB', output)
        self.assertNotIn('2500', output)  # Should not show as MB

    @patch('sys.stdout', new_callable=StringIO)
    def test_show_plain_language_summary_uses_mb_for_small(self, mock_stdout):
        """Test show_plain_language_summary uses MB for values < 1000 MB."""
        summary = {
            'duplicate_count': 25,
            'duplicate_size_mb': 500.0
        }
        show_plain_language_summary(summary, mode='two_drives')
        output = mock_stdout.getvalue()
        self.assertIn('Found 25 duplicates', output)
        self.assertIn('500.0 MB', output)
        self.assertNotIn('GB', output)

    @patch('sys.stdout', new_callable=StringIO)
    def test_show_plain_language_summary_single_drive_mode_label(self, mock_stdout):
        """Test show_plain_language_summary uses 'this drive' for single-drive mode."""
        summary = {
            'duplicate_count': 10,
            'duplicate_size_mb': 100.0
        }
        show_plain_language_summary(summary, mode='single_drive')
        output = mock_stdout.getvalue()
        self.assertIn('this drive', output)

    @patch('sys.stdout', new_callable=StringIO)
    def test_show_plain_language_summary_threshold_at_1000(self, mock_stdout):
        """Test show_plain_language_summary uses GB for exactly 1000 MB."""
        summary = {
            'duplicate_count': 5,
            'duplicate_size_mb': 1000.0
        }
        show_plain_language_summary(summary, mode='two_drives')
        output = mock_stdout.getvalue()
        self.assertIn('1.0 GB', output)


class TestNextSteps(unittest.TestCase):
    """Test suite for show_next_steps function."""

    @patch('sys.stdout', new_callable=StringIO)
    def test_show_next_steps_output(self, mock_stdout):
        """Test show_next_steps displays correct commands and paths."""
        report_path = '/tmp/diskcomp-report-20260323-120000.csv'
        show_next_steps(report_path)
        output = mock_stdout.getvalue()
        self.assertIn('Next steps', output)
        self.assertIn(f'cat {report_path}', output)
        self.assertIn(f'diskcomp --delete-from {report_path}', output)
        self.assertIn('diskcomp --undo', output)
        self.assertIn('diskcomp-undo', output)

    @patch('sys.stdout', new_callable=StringIO)
    def test_show_next_steps_undo_hint_format(self, mock_stdout):
        """Test show_next_steps shows undo log hint with date pattern."""
        report_path = '/home/user/diskcomp-report.csv'
        show_next_steps(report_path)
        output = mock_stdout.getvalue()
        # Check for undo hint pattern (should be like ~/diskcomp-undo-YYYYMMDD.json)
        self.assertIn('~/diskcomp-undo-', output)
        self.assertIn('.json', output)

    @patch('sys.stdout', new_callable=StringIO)
    def test_show_next_steps_border_format(self, mock_stdout):
        """Test show_next_steps displays border lines correctly."""
        report_path = '/tmp/report.csv'
        show_next_steps(report_path)
        output = mock_stdout.getvalue()
        # Check for border dashes (ASCII for cross-platform compatibility)
        self.assertIn('--', output)
        self.assertIn('-' * 60, output)


class TestSingleDriveMode(unittest.TestCase):
    """Test suite for --single flag and single-drive mode."""

    def test_parse_args_single_flag(self):
        """Test parse_args with --single flag."""
        args = parse_args(['--single', '/mnt/test'])
        self.assertEqual(args.single, '/mnt/test')

    def test_parse_args_single_with_min_size(self):
        """Test parse_args with --single and --min-size."""
        args = parse_args(['--single', '/mnt/test', '--min-size', '5MB'])
        self.assertEqual(args.single, '/mnt/test')
        self.assertEqual(args.min_size, '5MB')

    def test_parse_args_single_with_format_json(self):
        """Test parse_args with --single and --format json."""
        args = parse_args(['--single', '/mnt/test', '--format', 'json'])
        self.assertEqual(args.single, '/mnt/test')
        self.assertEqual(args.format, 'json')

    @patch('diskcomp.cli.show_next_steps')
    @patch('diskcomp.cli.show_plain_language_summary')
    @patch('diskcomp.cli.ReportWriter')
    @patch('diskcomp.hasher.group_by_hash_single_drive')
    @patch('diskcomp.hasher.group_by_size_single_drive')
    @patch('diskcomp.cli.FileHasher')
    @patch('diskcomp.cli.FileScanner')
    @patch('diskcomp.cli.os.path.isdir')
    @patch('diskcomp.cli.UIHandler')
    def test_main_single_drive_flag(
            self, mock_ui_factory, mock_isdir,
            mock_scanner_class, mock_hasher_class, mock_size_filter,
            mock_hash_grouper, mock_reporter_class, mock_summary,
            mock_next_steps):
        """Test main() with --single flag."""
        # Setup mocks
        mock_ui = MagicMock()
        mock_ui_factory.create.return_value = mock_ui

        mock_isdir.return_value = True

        # Mock scanner
        mock_scanner = MagicMock()
        mock_scanner_class.return_value = mock_scanner
        mock_scan_result = MagicMock()
        mock_scan_result.files = []
        mock_scan_result.file_count = 0
        mock_scanner.scan.return_value = mock_scan_result

        # Mock size filter
        mock_size_filter.return_value = ([], {'total_scanned': 0, 'candidate_count': 0, 'pct_skipped': 100})

        # Mock hash grouper
        mock_hash_grouper.return_value = {
            'duplicates': [],
            'unique': [],
            'summary': {
                'duplicate_count': 0,
                'duplicate_size_mb': 0,
                'unique_in_other_count': 0,
                'unique_in_other_size_mb': 0,
            }
        }

        # Mock reporter
        mock_reporter = MagicMock()
        mock_reporter.output_path = '/tmp/test-report.csv'
        mock_reporter_class.return_value = mock_reporter

        # Run main with --single flag
        args = parse_args(['--single', '/tmp/test_dir'])
        result = main(args)

        # Should complete successfully
        self.assertEqual(result, 0)

        # UI should be closed
        mock_ui.close.assert_called_once()

        # Scanner should be called
        mock_scanner_class.assert_called_once()

        # Report should be written
        mock_reporter.write_csv.assert_called_once()

    def test_main_single_drive_invalid_path(self):
        """Test main() with --single flag and invalid path."""
        with patch('diskcomp.cli.os.path.isdir', return_value=False):
            args = parse_args(['--single', '/nonexistent/path'])
            result = main(args)

            # Should fail with error code 1
            self.assertEqual(result, 1)


class TestActionMenu(unittest.TestCase):
    """Test suite for show_action_menu function (D-23, D-24)."""

    @patch('diskcomp.cli.input')
    def test_show_action_menu_option_1(self, mock_input):
        """Test show_action_menu returns 'interactive' on input '1'."""
        mock_input.return_value = '1'
        result = show_action_menu()
        self.assertEqual(result, 'interactive')

    @patch('diskcomp.cli.input')
    def test_show_action_menu_option_2(self, mock_input):
        """Test show_action_menu returns 'batch' on input '2'."""
        mock_input.return_value = '2'
        result = show_action_menu()
        self.assertEqual(result, 'batch')

    @patch('diskcomp.cli.input')
    def test_show_action_menu_option_3(self, mock_input):
        """Test show_action_menu returns 'exit' on input '3'."""
        mock_input.return_value = '3'
        result = show_action_menu()
        self.assertEqual(result, 'exit')

    @patch('diskcomp.cli.input')
    def test_show_action_menu_invalid_then_valid(self, mock_input):
        """Test show_action_menu retries on invalid input then returns valid choice."""
        mock_input.side_effect = ['0', '4', 'x', '2']
        result = show_action_menu()
        self.assertEqual(result, 'batch')
        # Should have been called 4 times (3 invalid + 1 valid)
        self.assertEqual(mock_input.call_count, 4)

    @patch('diskcomp.cli.input')
    def test_show_action_menu_whitespace_stripped(self, mock_input):
        """Test show_action_menu handles whitespace in input."""
        mock_input.return_value = '  3  '
        result = show_action_menu()
        self.assertEqual(result, 'exit')

    @patch('sys.stdout', new_callable=StringIO)
    @patch('diskcomp.cli.input')
    def test_show_action_menu_displays_menu(self, mock_input, mock_stdout):
        """Test show_action_menu displays the menu text."""
        mock_input.return_value = '1'
        show_action_menu()
        output = mock_stdout.getvalue()
        # Check for menu options
        self.assertIn('What next?', output)
        self.assertIn('Review and delete interactively', output)
        self.assertIn('Batch delete', output)
        self.assertIn('Exit', output)


class TestActionMenuIntegration(unittest.TestCase):
    """Test suite for action menu integration in main() flow."""

    @patch('diskcomp.deletion.DeletionOrchestrator')
    @patch('diskcomp.reporter.ReportReader')
    @patch('diskcomp.cli.show_action_menu')
    @patch('diskcomp.cli.show_next_steps')
    @patch('diskcomp.cli.show_plain_language_summary')
    @patch('diskcomp.cli.ReportWriter')
    @patch('diskcomp.cli.DuplicateClassifier')
    @patch('diskcomp.cli.FileHasher')
    @patch('diskcomp.cli.FileScanner')
    @patch('diskcomp.cli.display_health_checks')
    @patch('diskcomp.cli.os.access')
    @patch('diskcomp.cli.os.path.isdir')
    @patch('diskcomp.cli.UIHandler')
    def test_main_action_menu_interactive(
            self, mock_ui_factory, mock_isdir, mock_access,
            mock_display_health, mock_scanner_class, mock_hasher_class,
            mock_classifier_class, mock_reporter_class, mock_summary,
            mock_next_steps, mock_action_menu, mock_reader, mock_orchestrator):
        """Test main() action menu interactive mode path."""
        # Setup UI
        mock_ui = MagicMock()
        mock_ui_factory.create.return_value = mock_ui
        mock_isdir.return_value = True
        mock_access.return_value = True
        mock_display_health.return_value = True

        # Setup scanner
        mock_scanner = MagicMock()
        mock_scanner_class.return_value = mock_scanner
        mock_scan_result = MagicMock()
        mock_scan_result.files = []
        mock_scanner.scan.return_value = mock_scan_result

        # Setup classifier
        mock_classifier = MagicMock()
        mock_classifier_class.return_value = mock_classifier
        classification = {
            'summary': {
                'duplicate_count': 5,
                'duplicate_size_mb': 50.0,
                'unique_in_keep_count': 10,
                'unique_in_keep_size_mb': 100.0,
                'unique_in_other_count': 20,
                'unique_in_other_size_mb': 200.0,
            },
            'duplicates': [
                {'action': 'DELETE_FROM_OTHER', 'other_path': '/path/file1', 'size_mb': 10.0, 'hash': 'abc123', 'keep_path': '/path/keep1'},
            ],
            'unique_in_keep': [],
            'unique_in_other': [],
        }
        mock_classifier.classify.return_value = classification

        # Setup reporter
        mock_reporter = MagicMock()
        mock_reporter.output_path = '/tmp/test-report.csv'
        mock_reporter_class.return_value = mock_reporter

        # Setup action menu to return 'interactive'
        mock_action_menu.return_value = 'interactive'

        # Setup ReportReader
        mock_reader.load.return_value = [
            {'action': 'DELETE_FROM_OTHER', 'other_path': '/path/file1', 'size_mb': 10.0, 'hash': 'abc123', 'keep_path': '/path/keep1'},
        ]

        # Setup DeletionOrchestrator
        mock_orch = MagicMock()
        mock_orchestrator.return_value = mock_orch
        mock_result = MagicMock()
        mock_result.files_deleted = 1
        mock_result.space_freed_mb = 10.0
        mock_result.errors = []
        mock_result.undo_log_path = '/tmp/diskcomp-undo-20260323-120000.json'
        mock_orch.interactive_mode.return_value = mock_result

        # Mock input for scan confirmation
        with patch('diskcomp.cli.input', side_effect=['y']):
            args = parse_args(['--keep', '/mnt/keep', '--other', '/mnt/other'])
            result = main(args)

        # Verify
        self.assertEqual(result, 0)
        mock_action_menu.assert_called_once()
        mock_orch.interactive_mode.assert_called_once()
        mock_reader.load.assert_called_once_with('/tmp/test-report.csv')

    @patch('diskcomp.deletion.DeletionOrchestrator')
    @patch('diskcomp.reporter.ReportReader')
    @patch('diskcomp.cli.show_action_menu')
    @patch('diskcomp.cli.show_next_steps')
    @patch('diskcomp.cli.show_plain_language_summary')
    @patch('diskcomp.cli.ReportWriter')
    @patch('diskcomp.cli.DuplicateClassifier')
    @patch('diskcomp.cli.FileHasher')
    @patch('diskcomp.cli.FileScanner')
    @patch('diskcomp.cli.display_health_checks')
    @patch('diskcomp.cli.os.access')
    @patch('diskcomp.cli.os.path.isdir')
    @patch('diskcomp.cli.UIHandler')
    def test_main_action_menu_batch(
            self, mock_ui_factory, mock_isdir, mock_access,
            mock_display_health, mock_scanner_class, mock_hasher_class,
            mock_classifier_class, mock_reporter_class, mock_summary,
            mock_next_steps, mock_action_menu, mock_reader, mock_orchestrator):
        """Test main() action menu batch mode path."""
        # Setup UI
        mock_ui = MagicMock()
        mock_ui_factory.create.return_value = mock_ui
        mock_isdir.return_value = True
        mock_access.return_value = True
        mock_display_health.return_value = True

        # Setup scanner
        mock_scanner = MagicMock()
        mock_scanner_class.return_value = mock_scanner
        mock_scan_result = MagicMock()
        mock_scan_result.files = []
        mock_scanner.scan.return_value = mock_scan_result

        # Setup classifier
        mock_classifier = MagicMock()
        mock_classifier_class.return_value = mock_classifier
        classification = {
            'summary': {
                'duplicate_count': 3,
                'duplicate_size_mb': 30.0,
                'unique_in_keep_count': 10,
                'unique_in_keep_size_mb': 100.0,
                'unique_in_other_count': 20,
                'unique_in_other_size_mb': 200.0,
            },
            'duplicates': [
                {'action': 'DELETE_FROM_OTHER', 'other_path': '/path/file1', 'size_mb': 10.0, 'hash': 'abc123', 'keep_path': '/path/keep1'},
            ],
            'unique_in_keep': [],
            'unique_in_other': [],
        }
        mock_classifier.classify.return_value = classification

        # Setup reporter
        mock_reporter = MagicMock()
        mock_reporter.output_path = '/tmp/test-report.csv'
        mock_reporter_class.return_value = mock_reporter

        # Setup action menu to return 'batch'
        mock_action_menu.return_value = 'batch'

        # Setup ReportReader
        mock_reader.load.return_value = [
            {'action': 'DELETE_FROM_OTHER', 'other_path': '/path/file1', 'size_mb': 10.0, 'hash': 'abc123', 'keep_path': '/path/keep1'},
        ]

        # Setup DeletionOrchestrator
        mock_orch = MagicMock()
        mock_orchestrator.return_value = mock_orch
        mock_result = MagicMock()
        mock_result.files_deleted = 1
        mock_result.space_freed_mb = 10.0
        mock_result.errors = []
        mock_result.undo_log_path = '/tmp/diskcomp-undo-20260323-120000.json'
        mock_orch.batch_mode.return_value = mock_result

        # Mock input for scan confirmation
        with patch('diskcomp.cli.input', side_effect=['y']):
            args = parse_args(['--keep', '/mnt/keep', '--other', '/mnt/other'])
            result = main(args)

        # Verify
        self.assertEqual(result, 0)
        mock_action_menu.assert_called_once()
        mock_orch.batch_mode.assert_called_once()
        mock_reader.load.assert_called_once_with('/tmp/test-report.csv')

    @patch('diskcomp.cli.show_action_menu')
    @patch('diskcomp.cli.show_next_steps')
    @patch('diskcomp.cli.show_plain_language_summary')
    @patch('diskcomp.cli.ReportWriter')
    @patch('diskcomp.cli.DuplicateClassifier')
    @patch('diskcomp.cli.FileHasher')
    @patch('diskcomp.cli.FileScanner')
    @patch('diskcomp.cli.display_health_checks')
    @patch('diskcomp.cli.os.access')
    @patch('diskcomp.cli.os.path.isdir')
    @patch('diskcomp.cli.UIHandler')
    def test_main_action_menu_exit(
            self, mock_ui_factory, mock_isdir, mock_access,
            mock_display_health, mock_scanner_class, mock_hasher_class,
            mock_classifier_class, mock_reporter_class, mock_summary,
            mock_next_steps, mock_action_menu):
        """Test main() action menu exit path (no deletion)."""
        # Setup UI
        mock_ui = MagicMock()
        mock_ui_factory.create.return_value = mock_ui
        mock_isdir.return_value = True
        mock_access.return_value = True
        mock_display_health.return_value = True

        # Setup scanner
        mock_scanner = MagicMock()
        mock_scanner_class.return_value = mock_scanner
        mock_scan_result = MagicMock()
        mock_scan_result.files = []
        mock_scanner.scan.return_value = mock_scan_result

        # Setup classifier
        mock_classifier = MagicMock()
        mock_classifier_class.return_value = mock_classifier
        classification = {
            'summary': {
                'duplicate_count': 2,
                'duplicate_size_mb': 20.0,
                'unique_in_keep_count': 10,
                'unique_in_keep_size_mb': 100.0,
                'unique_in_other_count': 20,
                'unique_in_other_size_mb': 200.0,
            },
            'duplicates': [],
            'unique_in_keep': [],
            'unique_in_other': [],
        }
        mock_classifier.classify.return_value = classification

        # Setup reporter
        mock_reporter = MagicMock()
        mock_reporter.output_path = '/tmp/test-report.csv'
        mock_reporter_class.return_value = mock_reporter

        # Setup action menu to return 'exit'
        mock_action_menu.return_value = 'exit'

        # Mock input for scan confirmation
        with patch('diskcomp.cli.input', side_effect=['y']):
            args = parse_args(['--keep', '/mnt/keep', '--other', '/mnt/other'])
            result = main(args)

        # Verify
        self.assertEqual(result, 0)
        mock_action_menu.assert_called_once()
        # UI should be closed (no deletion)
        mock_ui.close.assert_called_once()

    @patch('diskcomp.cli.show_action_menu')
    @patch('diskcomp.cli.show_next_steps')
    @patch('diskcomp.cli.show_plain_language_summary')
    @patch('diskcomp.cli.ReportWriter')
    @patch('diskcomp.cli.DuplicateClassifier')
    @patch('diskcomp.cli.FileHasher')
    @patch('diskcomp.cli.FileScanner')
    @patch('diskcomp.cli.display_health_checks')
    @patch('diskcomp.cli.os.access')
    @patch('diskcomp.cli.os.path.isdir')
    @patch('diskcomp.cli.UIHandler')
    def test_main_no_action_menu_zero_duplicates(
            self, mock_ui_factory, mock_isdir, mock_access,
            mock_display_health, mock_scanner_class, mock_hasher_class,
            mock_classifier_class, mock_reporter_class, mock_summary,
            mock_next_steps, mock_action_menu):
        """Test main() does NOT show action menu when duplicate_count is 0 (D-24)."""
        # Setup UI
        mock_ui = MagicMock()
        mock_ui_factory.create.return_value = mock_ui
        mock_isdir.return_value = True
        mock_access.return_value = True
        mock_display_health.return_value = True

        # Setup scanner
        mock_scanner = MagicMock()
        mock_scanner_class.return_value = mock_scanner
        mock_scan_result = MagicMock()
        mock_scan_result.files = []
        mock_scanner.scan.return_value = mock_scan_result

        # Setup classifier with ZERO duplicates
        mock_classifier = MagicMock()
        mock_classifier_class.return_value = mock_classifier
        classification = {
            'summary': {
                'duplicate_count': 0,
                'duplicate_size_mb': 0.0,
                'unique_in_keep_count': 10,
                'unique_in_keep_size_mb': 100.0,
                'unique_in_other_count': 20,
                'unique_in_other_size_mb': 200.0,
            },
            'duplicates': [],
            'unique_in_keep': [],
            'unique_in_other': [],
        }
        mock_classifier.classify.return_value = classification

        # Setup reporter
        mock_reporter = MagicMock()
        mock_reporter.output_path = '/tmp/test-report.csv'
        mock_reporter_class.return_value = mock_reporter

        # Mock input for scan confirmation
        with patch('diskcomp.cli.input', side_effect=['y']):
            args = parse_args(['--keep', '/mnt/keep', '--other', '/mnt/other'])
            result = main(args)

        # Verify
        self.assertEqual(result, 0)
        # Action menu should NOT have been called because duplicate_count == 0
        mock_action_menu.assert_not_called()


if __name__ == '__main__':
    unittest.main()
