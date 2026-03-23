"""Unit tests for ANSI codes module and UI classes."""

import unittest
import io
import sys
from contextlib import redirect_stdout

from diskcomp.ansi_codes import (
    CYAN, GREEN, RED, RESET, BOLD, ARROW, TICK, CROSS,
    colored, progress_bar, format_speed, format_eta
)
from diskcomp.ui import UIHandler, RichProgressUI, ANSIProgressUI, RICH_AVAILABLE


class TestANSICodes(unittest.TestCase):
    """Test suite for ANSI codes module."""

    def test_ansi_colors_defined(self):
        """Test that color constants are defined and start with ANSI escape."""
        colors = [CYAN, GREEN, RED, RESET, BOLD]
        for color in colors:
            self.assertIsInstance(color, str)
            self.assertTrue(len(color) > 0, f"Color constant should not be empty")
            if color != RESET:  # RESET is special
                self.assertTrue(color.startswith("\033["), f"Color should start with ANSI escape: {repr(color)}")

    def test_symbols_defined(self):
        """Test that symbol constants are defined."""
        symbols = [ARROW, TICK, CROSS]
        for symbol in symbols:
            self.assertIsInstance(symbol, str)
            self.assertEqual(len(symbol), 1, f"Symbol should be single character: {symbol}")

    def test_colored_function(self):
        """Test colored() wraps text with color codes."""
        text = "test"
        result = colored(text, CYAN)
        self.assertIn(text, result, "Original text should be in result")
        self.assertIn(CYAN, result, "Color code should be in result")
        self.assertIn(RESET, result, "Reset code should be in result")
        self.assertTrue(result.startswith(CYAN), "Result should start with color code")
        self.assertTrue(result.endswith(RESET), "Result should end with reset code")

    def test_progress_bar_zero_percent(self):
        """Test progress_bar at 0%."""
        result = progress_bar(0, 100)
        self.assertIn("0%", result, "Should show 0%")
        self.assertIn("-", result, "Should have empty blocks")

    def test_progress_bar_half(self):
        """Test progress_bar at 50%."""
        result = progress_bar(50, 100)
        self.assertIn("50%", result, "Should show 50%")
        self.assertIn("=", result, "Should have filled blocks")
        self.assertIn("-", result, "Should have empty blocks")

    def test_progress_bar_full(self):
        """Test progress_bar at 100%."""
        result = progress_bar(100, 100)
        self.assertIn("100%", result, "Should show 100%")
        self.assertIn("=", result, "Should be all filled blocks")

    def test_format_speed_kb(self):
        """Test format_speed for KB/s (input in bytes/sec)."""
        result = format_speed(10240)  # 10 KB/s in bytes/sec
        self.assertIn("10.0", result)
        self.assertIn("KB/s", result)

    def test_format_speed_mb(self):
        """Test format_speed for MB/s (input in bytes/sec)."""
        result = format_speed(5 * 1048576)  # 5 MB/s in bytes/sec
        self.assertIn("5.0", result)
        self.assertIn("MB/s", result)

    def test_format_speed_gb(self):
        """Test format_speed for GB/s (input in bytes/sec)."""
        result = format_speed(2 * 1073741824)  # 2 GB/s in bytes/sec
        self.assertIn("2.0", result)
        self.assertIn("GB/s", result)

    def test_format_eta_seconds(self):
        """Test format_eta for seconds only."""
        result = format_eta(30)
        self.assertIn("30s", result)

    def test_format_eta_minutes_seconds(self):
        """Test format_eta for minutes and seconds."""
        result = format_eta(125)  # 2m 5s
        self.assertIn("2m", result)
        self.assertIn("5s", result)

    def test_format_eta_hours(self):
        """Test format_eta for hours."""
        result = format_eta(3665)  # 1h 1m 5s
        self.assertIn("1h", result)
        self.assertIn("1m", result)


@unittest.skipUnless(RICH_AVAILABLE, "Rich not installed")
class TestRichProgressUI(unittest.TestCase):
    """Test suite for RichProgressUI class."""

    def test_init(self):
        """Test RichProgressUI instantiation."""
        ui = RichProgressUI()
        self.assertIsNotNone(ui)
        self.assertIsNone(ui.scan_task_id)
        self.assertIsNone(ui.hash_task_id)

    def test_start_scan(self):
        """Test start_scan method."""
        ui = RichProgressUI()
        # Just verify it doesn't crash
        ui.start_scan("/test/path")
        self.assertIsNotNone(ui.scan_task_id)
        ui.close()

    def test_on_folder_done(self):
        """Test on_folder_done method."""
        ui = RichProgressUI()
        ui.start_scan("/test/path")
        # Should not crash
        ui.on_folder_done("/test/path/folder", 42)
        ui.close()

    def test_start_hash(self):
        """Test start_hash method."""
        ui = RichProgressUI()
        ui.start_hash(100)
        self.assertIsNotNone(ui.hash_task_id)
        ui.close()

    def test_on_file_hashed(self):
        """Test on_file_hashed method."""
        ui = RichProgressUI()
        ui.start_hash(100)
        # Should not crash
        ui.on_file_hashed(50, 100, 2.5, 60)
        ui.close()

    def test_show_summary(self):
        """Test show_summary method."""
        ui = RichProgressUI()
        # Should not crash
        ui.show_summary(
            duplicates_mb=100.5,
            duplicates_count=42,
            unique_keep_mb=200.0,
            unique_keep_count=100,
            unique_other_mb=150.0,
            unique_other_count=75,
            report_path="/tmp/report.csv"
        )
        ui.close()

    def test_show_summary_with_custom_labels(self):
        """Test show_summary method with custom labels."""
        ui = RichProgressUI()
        # Should not crash with custom labels
        ui.show_summary(
            duplicates_mb=100.5,
            duplicates_count=42,
            unique_keep_mb=200.0,
            unique_keep_count=100,
            unique_other_mb=150.0,
            unique_other_count=75,
            report_path="/tmp/report.csv",
            keep_label="Drive A",
            other_label="Drive B"
        )
        ui.close()

    def test_close(self):
        """Test close method."""
        ui = RichProgressUI()
        ui.start_scan("/test/path")
        # Should not crash
        ui.close()
        self.assertIsNone(ui.progress_context)


class TestANSIProgressUI(unittest.TestCase):
    """Test suite for ANSIProgressUI class."""

    def test_init(self):
        """Test ANSIProgressUI instantiation."""
        ui = ANSIProgressUI()
        self.assertIsNotNone(ui)

    def test_start_scan(self):
        """Test start_scan prints with cyan arrow."""
        ui = ANSIProgressUI()
        f = io.StringIO()
        with redirect_stdout(f):
            ui.start_scan("/test/path")
        output = f.getvalue()
        self.assertIn("Scanning", output)
        self.assertIn("/test/path", output)
        # Should contain ANSI codes or arrow symbol
        self.assertIn(ARROW, output)

    def test_on_folder_done(self):
        """Test on_folder_done prints folder path and file count."""
        ui = ANSIProgressUI()
        f = io.StringIO()
        with redirect_stdout(f):
            ui.on_folder_done("/test/path/folder", 42)
        output = f.getvalue()
        self.assertIn("42", output)
        self.assertIn("/test/path/folder", output)
        self.assertIn(ARROW, output)

    def test_start_hash(self):
        """Test start_hash prints with cyan arrow."""
        ui = ANSIProgressUI()
        f = io.StringIO()
        with redirect_stdout(f):
            ui.start_hash(100)
        output = f.getvalue()
        self.assertIn("Hashing", output)
        self.assertIn("100", output)
        self.assertIn(ARROW, output)

    def test_on_file_hashed(self):
        """Test on_file_hashed prints progress bar and stats."""
        ui = ANSIProgressUI()
        f = io.StringIO()
        with redirect_stdout(f):
            ui.on_file_hashed(50, 100, 2.5, 60)
        output = f.getvalue()
        self.assertIn("50", output, "Should show current count")
        self.assertIn("100", output, "Should show total count")
        self.assertIn("50%", output, "Should show percentage")

    def test_on_file_hashed_without_eta(self):
        """Test on_file_hashed without ETA."""
        ui = ANSIProgressUI()
        f = io.StringIO()
        with redirect_stdout(f):
            ui.on_file_hashed(25, 100, 1.0, None)
        output = f.getvalue()
        self.assertIn("25", output)
        self.assertIn("25%", output)
        # ETA should not appear if None
        # (may or may not contain "ETA" depending on implementation)

    def test_show_summary(self):
        """Test show_summary prints formatted box with stats."""
        ui = ANSIProgressUI()
        f = io.StringIO()
        with redirect_stdout(f):
            ui.show_summary(
                duplicates_mb=100.5,
                duplicates_count=42,
                unique_keep_mb=200.0,
                unique_keep_count=100,
                unique_other_mb=150.0,
                unique_other_count=75,
                report_path="/tmp/report.csv"
            )
        output = f.getvalue()
        # Check for key stats
        self.assertIn("100.5", output, "Should show duplicates MB")
        self.assertIn("42", output, "Should show duplicates count")
        self.assertIn("200", output, "Should show unique keep MB")
        self.assertIn("100", output, "Should show unique keep count")
        self.assertIn("150", output, "Should show unique other MB")
        self.assertIn("75", output, "Should show unique other count")
        self.assertIn("/tmp/report.csv", output, "Should show report path")
        # Check for box-drawing characters
        self.assertTrue(
            any(char in output for char in ["╔", "╚", "║", "═"]),
            "Should contain box-drawing characters"
        )

    def test_show_summary_with_custom_labels(self):
        """Test show_summary prints custom labels correctly."""
        ui = ANSIProgressUI()
        f = io.StringIO()
        with redirect_stdout(f):
            ui.show_summary(
                duplicates_mb=100.5,
                duplicates_count=42,
                unique_keep_mb=200.0,
                unique_keep_count=100,
                unique_other_mb=150.0,
                unique_other_count=75,
                report_path="/tmp/report.csv",
                keep_label="MyDrive",
                other_label="ExternalDrive"
            )
        output = f.getvalue()
        # Check for custom labels
        self.assertIn("Unique in MyDrive", output, "Should show custom keep label")
        self.assertIn("Unique in ExternalDrive", output, "Should show custom other label")
        # Check for key stats
        self.assertIn("100.5", output, "Should show duplicates MB")
        self.assertIn("/tmp/report.csv", output, "Should show report path")

    def test_close(self):
        """Test close method (should be no-op)."""
        ui = ANSIProgressUI()
        # Should not crash
        ui.close()


class TestUIHandler(unittest.TestCase):
    """Test suite for UIHandler factory class."""

    def test_create_ansi_forced(self):
        """Test create with force_ansi=True."""
        ui = UIHandler.create(force_ansi=True)
        self.assertIsInstance(ui, ANSIProgressUI)

    def test_get_available(self):
        """Test get_available returns string."""
        available = UIHandler.get_available()
        self.assertIsInstance(available, str)
        self.assertIn(available, ["rich", "ansi"])

    def test_create_returns_ui_instance(self):
        """Test create returns a UI instance."""
        ui = UIHandler.create(force_ansi=True)
        # Should have all required methods
        self.assertTrue(hasattr(ui, "start_scan"))
        self.assertTrue(hasattr(ui, "on_folder_done"))
        self.assertTrue(hasattr(ui, "start_hash"))
        self.assertTrue(hasattr(ui, "on_file_hashed"))
        self.assertTrue(hasattr(ui, "show_summary"))
        self.assertTrue(hasattr(ui, "close"))


if __name__ == "__main__":
    unittest.main()
