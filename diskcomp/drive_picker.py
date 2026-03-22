"""
Interactive drive enumeration and selection module for diskcomp.

This module provides functions to enumerate all mounted drives on the system,
display health information for each drive, and guide the user through selecting
which drive to keep and which drive to compare against.
"""

import sys
from typing import List, Optional, Dict

from diskcomp.health import check_drive_health, get_filesystem_type, get_volume_label
from diskcomp.types import DriveInfo

# Optional dependency: psutil for disk partitions
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


def get_drives() -> List[DriveInfo]:
    """
    Enumerate all mounted drives and return health information for each.

    Returns:
        List of DriveInfo objects with device, mountpoint, fstype, and space stats.
        Returns empty list on error.
    """
    if PSUTIL_AVAILABLE:
        return _get_drives_psutil()
    else:
        return _get_drives_subprocess()


def _get_drives_psutil() -> List[DriveInfo]:
    """
    Enumerate drives using psutil.disk_partitions().

    Returns:
        List of DriveInfo objects or empty list on error.
    """
    drives = []
    try:
        for partition in psutil.disk_partitions(all=False):
            health = check_drive_health(partition.mountpoint)
            volume_label = get_volume_label(partition.mountpoint)
            drive = DriveInfo(
                device=partition.device,
                mountpoint=partition.mountpoint,
                fstype=partition.fstype,
                total_gb=health.total_gb,
                used_gb=health.used_gb,
                free_gb=health.free_gb,
                is_writable=health.is_writable,
                volume_label=volume_label
            )
            drives.append(drive)
    except Exception as e:
        print(f"Error enumerating drives with psutil: {str(e)}", file=sys.stderr)
        return []

    return drives


def _get_drives_subprocess() -> List[DriveInfo]:
    """
    Enumerate drives using platform-specific subprocess commands.

    Returns:
        List of DriveInfo objects or empty list on error.
    """
    if sys.platform == 'darwin':
        return _get_drives_macos()
    elif sys.platform == 'win32':
        return _get_drives_windows()
    elif sys.platform.startswith('linux'):
        return _get_drives_linux()

    return []


def _get_drives_macos() -> List[DriveInfo]:
    """
    Enumerate drives on macOS using diskutil list -plist.

    Returns:
        List of DriveInfo objects or empty list on error.
    """
    drives = []
    try:
        import subprocess
        import plistlib

        result = subprocess.run(
            ['diskutil', 'list', '-plist'],
            capture_output=True,
            timeout=10
        )

        if result.returncode == 0:
            plist_data = plistlib.loads(result.stdout)
            if 'AllDisksAndPartitions' in plist_data:
                for disk in plist_data['AllDisksAndPartitions']:
                    if 'Partitions' in disk:
                        for partition in disk['Partitions']:
                            if 'MountPoint' in partition:
                                mountpoint = partition['MountPoint']
                                device = partition.get('DeviceIdentifier', 'unknown')
                                fstype = partition.get('Content', 'UNKNOWN')

                                try:
                                    health = check_drive_health(mountpoint)
                                    volume_label = get_volume_label(mountpoint)
                                    drive = DriveInfo(
                                        device=device,
                                        mountpoint=mountpoint,
                                        fstype=fstype,
                                        total_gb=health.total_gb,
                                        used_gb=health.used_gb,
                                        free_gb=health.free_gb,
                                        is_writable=health.is_writable,
                                        volume_label=volume_label
                                    )
                                    drives.append(drive)
                                except Exception:
                                    continue
    except Exception as e:
        print(f"Error enumerating macOS drives: {str(e)}", file=sys.stderr)

    return drives


def _get_drives_linux() -> List[DriveInfo]:
    """
    Enumerate drives on Linux using /etc/mtab or /proc/mounts.

    Returns:
        List of DriveInfo objects or empty list on error.
    """
    drives = []
    try:
        import subprocess

        # Try df command which works across Linux distributions
        result = subprocess.run(
            ['df', '-P'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            for line in lines:
                parts = line.split()
                if len(parts) >= 6:
                    device = parts[0]
                    mountpoint = parts[5]

                    # Skip virtual filesystems
                    if mountpoint.startswith('/sys') or mountpoint.startswith('/proc'):
                        continue

                    fstype = get_filesystem_type(mountpoint)

                    try:
                        health = check_drive_health(mountpoint)
                        volume_label = get_volume_label(mountpoint)
                        drive = DriveInfo(
                            device=device,
                            mountpoint=mountpoint,
                            fstype=fstype,
                            total_gb=health.total_gb,
                            used_gb=health.used_gb,
                            free_gb=health.free_gb,
                            is_writable=health.is_writable,
                            volume_label=volume_label
                        )
                        drives.append(drive)
                    except Exception:
                        continue
    except Exception as e:
        print(f"Error enumerating Linux drives: {str(e)}", file=sys.stderr)

    return drives


def _get_drives_windows() -> List[DriveInfo]:
    """
    Enumerate drives on Windows using wmic logicaldisk.

    Returns:
        List of DriveInfo objects or empty list on error.
    """
    drives = []
    try:
        import subprocess

        result = subprocess.run(
            ['wmic', 'logicaldisk', 'get', 'name,filesystem,size,freespace', '/format:csv'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                for line in lines[1:]:  # Skip header
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 4:
                        device = parts[0]  # Drive letter
                        fstype = parts[1]
                        try:
                            total_bytes = int(parts[2])
                            free_bytes = int(parts[3])
                            used_bytes = total_bytes - free_bytes

                            total_gb = round(total_bytes / (1024 ** 3), 2)
                            used_gb = round(used_bytes / (1024 ** 3), 2)
                            free_gb = round(free_bytes / (1024 ** 3), 2)

                            # Assume Windows drives are writable (can check via os.access later)
                            import os
                            is_writable = os.access(device, os.W_OK)

                            volume_label = get_volume_label(device)

                            drive = DriveInfo(
                                device=device,
                                mountpoint=device,
                                fstype=fstype,
                                total_gb=total_gb,
                                used_gb=used_gb,
                                free_gb=free_gb,
                                is_writable=is_writable,
                                volume_label=volume_label
                            )
                            drives.append(drive)
                        except (ValueError, IndexError):
                            continue
    except Exception as e:
        print(f"Error enumerating Windows drives: {str(e)}", file=sys.stderr)

    return drives


def _prompt_for_drive_index(prompt_text: str, max_index: int) -> int:
    """
    Prompt user to select a drive by index (1-based input, 0-based output).

    Args:
        prompt_text: Prompt text to display
        max_index: Maximum valid index (1-based)

    Returns:
        0-based index of selected drive
    """
    while True:
        try:
            response = input(f"{prompt_text} (1-{max_index}): ").strip()
            if not response:
                print(f"Invalid input. Please enter a number between 1 and {max_index}.")
                continue

            value = int(response)
            if 1 <= value <= max_index:
                return value - 1
            else:
                print(f"Invalid selection. Enter a number between 1 and {max_index}.")
        except ValueError:
            print("Invalid input. Please enter a number.")


def interactive_drive_picker() -> Optional[Dict[str, str]]:
    """
    Interactive drive selection interface.

    Lists all mounted drives with health information, prompts user to select
    which drive to keep and which to compare against.

    Returns:
        Dict with {'keep': '/path/to/keep', 'other': '/path/to/other'}
        Returns None if fewer than 2 drives available or on error.
    """
    drives = get_drives()

    if not drives:
        print("Error: No mounted drives detected.", file=sys.stderr)
        return None

    if len(drives) < 2:
        print("Error: Need at least 2 drives to compare.", file=sys.stderr)
        return None

    # Display available drives
    print("\n=== Available Drives ===\n")
    for i, drive in enumerate(drives, 1):
        # Display volume label if available, otherwise use mountpoint
        label_or_path = drive.volume_label or drive.mountpoint
        print(f"{i}. {label_or_path} ({drive.mountpoint})")
        print(f"   Device: {drive.device}")
        print(f"   Filesystem: {drive.fstype}")
        print(f"   Space: {drive.used_gb}GB / {drive.total_gb}GB used")
        print(f"   Writable: {'Yes' if drive.is_writable else 'NO (READ-ONLY)'}")

        # Check for warnings
        health = check_drive_health(drive.mountpoint)
        if health.warnings:
            for warning in health.warnings:
                print(f"   WARNING: {warning}")

        print()

    # Prompt for keep drive
    keep_index = _prompt_for_drive_index("Which drive to KEEP?", len(drives))
    keep_drive = drives[keep_index].mountpoint

    print(f"\nKeep drive: {keep_drive}\n")

    # Prompt for other drive
    remaining = [d for i, d in enumerate(drives) if i != keep_index]

    if not remaining:
        print("Error: Need at least 2 drives to compare.", file=sys.stderr)
        return None

    print("Remaining drives for comparison:")
    for i, drive in enumerate(remaining, 1):
        print(f"{i}. {drive.mountpoint}")

    print()
    other_index = _prompt_for_drive_index("Which drive to compare (OTHER)?", len(remaining))
    other_drive = remaining[other_index].mountpoint

    print(f"\nSelected: Keep={keep_drive}, Other={other_drive}")

    return {'keep': keep_drive, 'other': other_drive}
