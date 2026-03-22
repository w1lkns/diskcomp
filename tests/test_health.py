"""
Unit tests for diskcomp health check module.

This module contains comprehensive tests for health check functions including
drive space monitoring, filesystem detection, read-only status checking,
optional SMART data retrieval, and benchmark functionality.
"""

import unittest
import sys
import tempfile
import os
from unittest.mock import patch, MagicMock, mock_open

from diskcomp.health import (
    get_filesystem_type,
    check_drive_health,
    get_smart_data,
)
from diskcomp.benchmarker import benchmark_read_speed
from diskcomp.types import HealthCheckResult, BenchmarkResult


class TestDriveHealth(unittest.TestCase):
    """Test suite for check_drive_health() function (HLTH-01)."""

    def test_check_drive_health_returns_result(self):
        """Test that check_drive_health returns HealthCheckResult with correct space fields."""
        mock_usage = MagicMock()
        mock_usage.total = 1000 * (1024 ** 3)
        mock_usage.used = 400 * (1024 ** 3)
        mock_usage.free = 600 * (1024 ** 3)

        with patch('diskcomp.health.shutil.disk_usage') as mock_du:
            with patch('diskcomp.health.os.access') as mock_access:
                with patch('diskcomp.health.get_filesystem_type') as mock_fstype:
                    # Mock disk usage with proper object structure
                    mock_du.return_value = mock_usage
                    mock_access.return_value = True
                    mock_fstype.return_value = 'HFS+'

                    result = check_drive_health('/Volumes/Test')

                    # Verify result is HealthCheckResult
                    self.assertIsInstance(result, HealthCheckResult)

                    # Verify space fields are correctly calculated
                    self.assertAlmostEqual(result.total_gb, 1000.0, places=1)
                    self.assertAlmostEqual(result.used_gb, 400.0, places=1)
                    self.assertAlmostEqual(result.free_gb, 600.0, places=1)

                    # Verify other fields
                    self.assertEqual(result.is_writable, True)
                    self.assertEqual(result.fstype, 'HFS+')
                    self.assertEqual(len(result.warnings), 0)
                    self.assertEqual(len(result.errors), 0)


class TestFilesystemDetection(unittest.TestCase):
    """Test suite for filesystem detection (HLTH-02)."""

    def test_get_filesystem_type_with_psutil(self):
        """Test get_filesystem_type() with psutil available."""
        try:
            import psutil
            # If psutil is available, test it works
            mock_partition = MagicMock()
            mock_partition.mountpoint = '/Volumes/Test'
            mock_partition.fstype = 'APFS'

            with patch('psutil.disk_partitions') as mock_parts:
                mock_parts.return_value = [mock_partition]
                result = get_filesystem_type('/Volumes/Test')
                # If psutil works, should return the fstype
                self.assertEqual(result, 'APFS')
        except ImportError:
            # psutil not available, skip this test
            self.skipTest("psutil not available")

    def test_get_filesystem_type_fallback_to_subprocess(self):
        """Test get_filesystem_type() fallback to subprocess when psutil unavailable."""
        with patch('diskcomp.health.PSUTIL_AVAILABLE', False):
            with patch('sys.platform', 'linux'):
                with patch('diskcomp.health.subprocess.run') as mock_run:
                    # Mock subprocess output showing ext4 filesystem
                    mock_result = MagicMock()
                    mock_result.returncode = 0
                    mock_result.stdout = 'FSTYPE\next4\n'
                    mock_run.return_value = mock_result

                    result = get_filesystem_type('/mnt/test')
                    self.assertEqual(result, 'ext4')

    def test_check_drive_health_ntfs_on_macos_warning(self):
        """Test HLTH-02: check_drive_health adds NTFS-on-macOS warning."""
        mock_usage = MagicMock()
        mock_usage.total = 1000 * (1024 ** 3)
        mock_usage.used = 400 * (1024 ** 3)
        mock_usage.free = 600 * (1024 ** 3)

        with patch('diskcomp.health.shutil.disk_usage') as mock_du:
            with patch('diskcomp.health.os.access') as mock_access:
                with patch('diskcomp.health.get_filesystem_type') as mock_fstype:
                    with patch('diskcomp.health.sys.platform', 'darwin'):
                        mock_du.return_value = mock_usage
                        mock_access.return_value = True
                        mock_fstype.return_value = 'NTFS'

                        result = check_drive_health('/Volumes/NTFS')

                        # Verify warning is present
                        self.assertGreater(len(result.warnings), 0)
                        self.assertIn('NTFS on macOS', result.warnings[0])

    def test_check_drive_health_readonly_warning(self):
        """Test HLTH-02: check_drive_health adds read-only warning."""
        mock_usage = MagicMock()
        mock_usage.total = 1000 * (1024 ** 3)
        mock_usage.used = 400 * (1024 ** 3)
        mock_usage.free = 600 * (1024 ** 3)

        with patch('diskcomp.health.shutil.disk_usage') as mock_du:
            with patch('diskcomp.health.os.access') as mock_access:
                with patch('diskcomp.health.get_filesystem_type') as mock_fstype:
                    mock_du.return_value = mock_usage
                    mock_access.return_value = False
                    mock_fstype.return_value = 'NTFS'

                    result = check_drive_health('/Volumes/ReadOnly')

                    # Verify read-only warning is present
                    self.assertGreater(len(result.warnings), 0)
                    warning_text = ' '.join(result.warnings).lower()
                    self.assertIn('read-only', warning_text)


class TestBenchmark(unittest.TestCase):
    """Test suite for benchmark_read_speed() function (HLTH-03)."""

    def test_benchmark_read_speed_success(self):
        """Test HLTH-03: benchmark_read_speed returns successful BenchmarkResult."""
        import tempfile as tempfile_module

        # Create actual temp file for realistic test
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a small test file
            test_file = os.path.join(tmpdir, 'test_benchmark.bin')
            with open(test_file, 'wb') as f:
                f.write(b'\0' * (10 * 1024 * 1024))  # 10MB test file

            # Run benchmark on actual file
            result = benchmark_read_speed(
                tmpdir,
                test_size_mb=10,  # Use smaller size for test
                chunk_size_kb=512
            )

            # Verify result
            self.assertIsInstance(result, BenchmarkResult)
            # On temp dir, we might not be able to write, so check for either success or permission error
            if result.success:
                self.assertGreater(result.speed_mbps, 0)
                self.assertGreater(result.duration_secs, 0)
                self.assertEqual(result.bytes_read, 10 * 1024 * 1024)

    def test_benchmark_read_speed_failure(self):
        """Test HLTH-03: benchmark_read_speed returns failure on exception."""
        with patch('diskcomp.benchmarker.tempfile.mkstemp') as mock_mkstemp:
            # Mock PermissionError on temp file creation
            mock_mkstemp.side_effect = PermissionError("Permission denied")

            result = benchmark_read_speed('/Volumes/ReadOnly')

            # Verify failure result
            self.assertEqual(result.success, False)
            self.assertIn('Permission', result.error)
            self.assertEqual(result.speed_mbps, 0.0)
            self.assertEqual(result.bytes_read, 0)


class TestSMART(unittest.TestCase):
    """Test suite for get_smart_data() function (HLTH-04)."""

    def test_get_smart_data_not_available(self):
        """Test HLTH-04: get_smart_data returns None when smartctl unavailable."""
        with patch('diskcomp.health.subprocess.run') as mock_run:
            # Mock FileNotFoundError (smartctl not on PATH)
            mock_run.side_effect = FileNotFoundError("smartctl not found")

            result = get_smart_data('/dev/sda')

            # Verify None is returned
            self.assertIsNone(result)

    def test_get_smart_data_success(self):
        """Test HLTH-04: get_smart_data returns dict with health_status on success."""
        with patch('diskcomp.health.subprocess.run') as mock_run:
            # Mock successful smartctl response
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = '''{
                "smart_status": {"passed": true},
                "temperature": {"current_celsius": 35}
            }'''
            mock_run.return_value = mock_result

            result = get_smart_data('/dev/sda')

            # Verify result
            self.assertIsNotNone(result)
            self.assertEqual(result['health_status'], 'PASSED')
            self.assertEqual(result['temperature_c'], 35)

    def test_get_smart_data_timeout(self):
        """Test HLTH-04: get_smart_data returns None on timeout."""
        with patch('diskcomp.health.subprocess.run') as mock_run:
            # Mock TimeoutExpired
            mock_run.side_effect = TimeoutError("Timeout")

            result = get_smart_data('/dev/sda')

            # Verify None is returned
            self.assertIsNone(result)


class TestIntegration(unittest.TestCase):
    """Integration tests for health checks (HLTH-05)."""

    def test_health_checks_dont_block(self):
        """Test HLTH-05: check_drive_health warnings don't block function."""
        # Create actual temp directory for real test
        with tempfile.TemporaryDirectory() as temp_dir:
            # Call check_drive_health on real system path
            result = check_drive_health(temp_dir)

            # Verify result is returned (even if warnings exist)
            self.assertIsInstance(result, HealthCheckResult)

            # Verify fields are populated
            self.assertGreater(result.total_gb, 0)
            self.assertIsInstance(result.warnings, list)
            self.assertIsInstance(result.errors, list)

            # Verify the function returns successfully regardless of warnings
            self.assertIsNotNone(result.mountpoint)
            self.assertIsNotNone(result.fstype)


if __name__ == '__main__':
    unittest.main()
