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
from diskcomp.benchmarker import benchmark_read_speed

# Optional dependency: psutil for disk partitions
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


def get_volume_label(mount_point: str) -> Optional[str]:
    """
    Retrieve the volume label/name of a mounted drive.

    Args:
        mount_point: Path to a mounted drive (e.g., '/Volumes/MyDrive')

    Returns:
        Volume label string if available, else None on error
    """
    try:
        if sys.platform == 'darwin':
            return _get_volume_label_macos(mount_point)
        elif sys.platform == 'win32':
            return _get_volume_label_windows(mount_point)
        elif sys.platform == 'linux':
            return _get_volume_label_linux(mount_point)
    except Exception:
        pass

    return None


def _get_volume_label_macos(mount_point: str) -> Optional[str]:
    """
    Get volume label on macOS using diskutil info.

    Args:
        mount_point: Path to mounted drive

    Returns:
        Volume name or None on error
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
                if 'Volume Name:' in line:
                    # Extract name from line like "   Volume Name:            MyDrive"
                    parts = line.split(':')
                    if len(parts) > 1:
                        return parts[1].strip()
    except Exception:
        pass
    return None


def _get_volume_label_linux(mount_point: str) -> Optional[str]:
    """
    Get volume label on Linux using lsblk or blkid.

    Args:
        mount_point: Path to mounted drive

    Returns:
        Volume label or None on error
    """
    try:
        # Try lsblk first
        result = subprocess.run(
            ['lsblk', '-no', 'LABEL', mount_point],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            label = result.stdout.strip()
            if label:
                return label
    except Exception:
        pass

    return None


def _get_volume_label_windows(mount_point: str) -> Optional[str]:
    """
    Get volume label on Windows using wmic.

    Args:
        mount_point: Drive letter or path (e.g., 'C:\\' or 'C:')

    Returns:
        Volume label or None on error
    """
    try:
        # Extract drive letter
        drive = mount_point[0].upper()
        result = subprocess.run(
            ['wmic', 'logicaldisk', 'where', f'name="{drive}:"', 'get', 'volumename'],
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
    return None


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


def get_fix_instructions(fstype: str, platform: str, mount_point: str) -> str:
    """
    Return platform and filesystem-specific remediation instructions for read-only drives.

    Args:
        fstype: Filesystem type (e.g., 'NTFS', 'HFS+', 'ext4')
        platform: sys.platform value ('darwin', 'linux', 'win32')
        mount_point: Path to mounted drive

    Returns:
        String with actionable remediation steps, or empty string if none needed
    """
    fstype_upper = fstype.upper()

    # NTFS on macOS
    if fstype_upper == 'NTFS' and platform == 'darwin':
        return "Install macFUSE and NTFS-3G: `brew install macfuse ntfs-3g` then remount with write support. See: https://github.com/gromgit/homebrew-fuse"

    # NTFS on Linux
    if fstype_upper == 'NTFS' and platform == 'linux':
        return "Install ntfs-3g: `sudo apt install ntfs-3g` (Ubuntu/Debian) or `sudo dnf install ntfs-3g` (Fedora), then remount: `sudo mount -t ntfs-3g /dev/... /mount/path -o rw`"

    # NTFS on Windows
    if fstype_upper == 'NTFS' and platform == 'win32':
        return "Run `chkdsk X: /F` as Administrator to repair, or check Device Manager for driver issues"

    # HFS+ (read-only) on macOS
    if fstype_upper == 'HFS+' and platform == 'darwin':
        return "Run `diskutil verifyVolume /Volumes/YourDrive` to check, then try remounting: `sudo mount -uw /Volumes/YourDrive`"

    # ext4 on any platform
    if fstype_upper == 'EXT4':
        return f"Check mount options: `mount | grep {mount_point}`. If mounted read-only, remount with: `sudo mount -o remount,rw {mount_point}`"

    # Default fallback
    if platform == 'darwin':
        return f"Try remounting read-write: `sudo mount -uw {mount_point}`"
    elif platform == 'linux':
        return f"Try remounting read-write: `sudo mount -o remount,rw {mount_point}`"
    elif platform == 'win32':
        return "Run Disk Management as Administrator to check drive status and repair"

    return ""


def check_drive_health(mount_point: str) -> HealthCheckResult:
    """
    Perform comprehensive health check on a mounted drive.

    Args:
        mount_point: Path to mounted drive

    Returns:
        HealthCheckResult with space usage, filesystem, read-only status, warnings, benchmark result
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

    # Add warnings and fix instructions for read-only drives
    benchmark_result = None
    if not is_writable:
        fix_instr = get_fix_instructions(fstype, sys.platform, mount_point)
        if fix_instr:
            warnings.append(f"Read-only drive detected. To fix: {fix_instr}")
        else:
            warnings.append("Drive is read-only: cannot write to this path")

    if fstype == 'NTFS' and sys.platform == 'darwin':
        warnings.append("NTFS on macOS may be read-only without macFUSE+NTFS-3G write support")

    # Run benchmark if drive is readable
    if is_writable:
        try:
            benchmark_result = benchmark_read_speed(mount_point)
        except Exception:
            # Benchmark failed; result will be None and warning will be shown in CLI
            pass

    return HealthCheckResult(
        mountpoint=mount_point,
        total_gb=total_gb,
        used_gb=used_gb,
        free_gb=free_gb,
        fstype=fstype,
        is_writable=is_writable,
        warnings=warnings,
        errors=errors,
        smart_data=None,
        benchmark_result=benchmark_result
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
