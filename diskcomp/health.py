"""
Drive health checks module for diskcomp.

This module handles drive health checks including space usage reporting,
filesystem type detection, read-only status checking, optional SMART data retrieval,
and graceful fallbacks for optional dependencies.
"""

import shutil
import os
import sys
import subprocess
import json
from typing import List, Dict, Optional

from diskcomp.types import DriveInfo, HealthCheckResult, BenchmarkResult

# Optional dependency: psutil for disk partitions
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


def get_filesystem_type(mount_point: str) -> str:
    """
    Detect the filesystem type of a mounted drive.

    Args:
        mount_point: Path to a mounted drive (e.g., '/Volumes/MyDrive')

    Returns:
        Filesystem type string (e.g., 'NTFS', 'HFS+', 'ext4') or 'UNKNOWN' on error
    """
    if PSUTIL_AVAILABLE:
        try:
            partitions = psutil.disk_partitions()
            for partition in partitions:
                if partition.mountpoint == mount_point:
                    return partition.fstype
        except Exception:
            pass

    # Fallback to platform-specific subprocess approach
    try:
        if sys.platform == 'darwin':
            return _get_filesystem_type_macos(mount_point)
        elif sys.platform == 'win32':
            return _get_filesystem_type_windows(mount_point)
        elif sys.platform == 'linux':
            return _get_filesystem_type_linux(mount_point)
    except Exception:
        pass

    return 'UNKNOWN'


def _get_filesystem_type_macos(mount_point: str) -> str:
    """
    Detect filesystem type on macOS using diskutil.

    Args:
        mount_point: Path to mounted drive

    Returns:
        Filesystem type or 'UNKNOWN' on error
    """
    try:
        result = subprocess.run(
            ['diskutil', 'info', mount_point],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'Type:' in line:
                    # Extract type from line like "   Type:                APFS"
                    parts = line.split(':')
                    if len(parts) > 1:
                        fstype = parts[1].strip().split()[0]
                        return fstype
    except Exception:
        pass
    return 'UNKNOWN'


def _get_filesystem_type_linux(mount_point: str) -> str:
    """
    Detect filesystem type on Linux using df.

    Args:
        mount_point: Path to mounted drive

    Returns:
        Filesystem type or 'UNKNOWN' on error
    """
    try:
        result = subprocess.run(
            ['df', '--output=fstype', mount_point],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                return lines[1].strip()
    except Exception:
        pass
    return 'UNKNOWN'


def _get_filesystem_type_windows(mount_point: str) -> str:
    """
    Detect filesystem type on Windows using wmic.

    Args:
        mount_point: Drive letter or path (e.g., 'C:\\' or 'C:')

    Returns:
        Filesystem type or 'UNKNOWN' on error
    """
    try:
        # Extract drive letter
        drive = mount_point[0].upper()
        result = subprocess.run(
            ['wmic', 'logicaldisk', 'where', f'name="{drive}:"', 'get', 'filesystem'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            lines = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
            if len(lines) > 1:
                return lines[1]
    except Exception:
        pass
    return 'UNKNOWN'


def check_drive_health(mount_point: str) -> HealthCheckResult:
    """
    Perform comprehensive health check on a mounted drive.

    Args:
        mount_point: Path to mounted drive

    Returns:
        HealthCheckResult with space usage, filesystem, read-only status, warnings
    """
    warnings: List[str] = []
    errors: List[str] = []

    # Get disk usage
    try:
        usage = shutil.disk_usage(mount_point)
        total_gb = round(usage.total / (1024 ** 3), 2)
        used_gb = round(usage.used / (1024 ** 3), 2)
        free_gb = round(usage.free / (1024 ** 3), 2)
    except Exception as e:
        errors.append(f"Failed to get disk usage: {str(e)}")
        total_gb = 0.0
        used_gb = 0.0
        free_gb = 0.0

    # Get filesystem type
    fstype = get_filesystem_type(mount_point)

    # Check write permission
    is_writable = os.access(mount_point, os.W_OK)

    # Add warnings
    if not is_writable:
        warnings.append("Drive is read-only: cannot write to this path")

    if fstype == 'NTFS' and sys.platform == 'darwin':
        warnings.append("NTFS on macOS may be read-only without macFUSE+NTFS-3G write support")

    return HealthCheckResult(
        mountpoint=mount_point,
        total_gb=total_gb,
        used_gb=used_gb,
        free_gb=free_gb,
        fstype=fstype,
        is_writable=is_writable,
        warnings=warnings,
        errors=errors,
        smart_data=None
    )


def get_smart_data(device_path: str) -> Optional[dict]:
    """
    Retrieve SMART data from a drive if smartmontools is available.

    Args:
        device_path: Device identifier (e.g., '/dev/sda', 'pd0')

    Returns:
        Dict with {device, health_status, temperature_c, error} or None if unavailable
    """
    try:
        result = subprocess.run(
            ['smartctl', '-j', device_path],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode in [0, 2]:  # 0=ok, 2=warnings OK
            data = json.loads(result.stdout)
            health_status = "PASSED" if data['smart_status']['passed'] else "FAILED"
            temperature_c = data.get('temperature', {}).get('current_celsius')
            return {
                'device': device_path,
                'health_status': health_status,
                'temperature_c': temperature_c,
                'error': None
            }
    except FileNotFoundError:
        # smartctl not on PATH
        return None
    except subprocess.TimeoutExpired:
        # Timeout
        return None
    except json.JSONDecodeError:
        # Invalid JSON
        return None
    except Exception:
        # Unexpected error
        return None

    return None
