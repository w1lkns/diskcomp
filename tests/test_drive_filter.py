"""
Test mount point filtering logic for diskcomp drive picker.
"""
import pytest
from diskcomp.drive_picker import _should_include_mount


def test_should_include_mount_user_friendly():
    """Test that user-friendly mounts are included."""
    # Root filesystem should always be included
    assert _should_include_mount('/', 'ext4', '/dev/sda1') == True
    assert _should_include_mount('/', 'apfs', '/dev/disk3s1s1') == True
    
    # Home directory if separate partition
    assert _should_include_mount('/home', 'ext4', '/dev/sdb1') == True


def test_should_include_mount_external_drives():
    """Test that external drives are included."""
    # Linux external drives
    assert _should_include_mount('/media/pi/USB_DRIVE', 'vfat', '/dev/sdb1') == True
    assert _should_include_mount('/mnt/backup', 'ext4', '/dev/sdc1') == True
    
    # macOS external drives  
    assert _should_include_mount('/Volumes/USB', 'msdos', '/dev/disk4s1') == True
    assert _should_include_mount('/Volumes/Backup', 'hfs', '/dev/disk5s2') == True


def test_should_include_mount_virtual_filesystems():
    """Test that virtual/temporary filesystems are excluded."""
    virtual_mounts = [
        ('/dev', 'devtmpfs', 'udev'),
        ('/run', 'tmpfs', 'tmpfs'),  
        ('/sys/fs/cgroup', 'tmpfs', 'tmpfs'),
        ('/proc', 'proc', 'proc'),
        ('/tmp', 'tmpfs', 'tmpfs'),
        ('/dev/shm', 'tmpfs', 'tmpfs'),
    ]
    
    for mount, fstype, device in virtual_mounts:
        assert _should_include_mount(mount, fstype, device) == False


def test_should_include_mount_system_paths():
    """Test that system mount paths are excluded."""
    system_mounts = [
        ('/run/user/1000', 'tmpfs', 'tmpfs'),
        ('/run/credentials/systemd-journald.service', 'tmpfs', 'tmpfs'), 
        ('/run/lock', 'tmpfs', 'tmpfs'),
        ('/boot/firmware', 'vfat', '/dev/sda1'),
        ('/snap/core20/1828', 'squashfs', '/dev/loop0'),
        ('/var/snap/lxd/common/lxd', 'ext4', '/dev/sda3'),
        ('/System/Volumes/VM', 'apfs', '/dev/disk3s6'),  # macOS
    ]
    
    for mount, fstype, device in system_mounts:
        assert _should_include_mount(mount, fstype, device) == False


def test_should_include_mount_edge_cases():
    """Test edge cases and boundary conditions."""
    # Root should be included even with tmpfs (unusual but possible)
    assert _should_include_mount('/', 'tmpfs', 'tmpfs') == True
    
    # External mounts with unusual filesystems should be included
    assert _should_include_mount('/media/usb', 'ntfs', '/dev/sdc1') == True
    assert _should_include_mount('/Volumes/BACKUP', 'exfat', '/dev/disk6s1') == True
    
    # System-like paths that could be user data should be excluded conservatively
    assert _should_include_mount('/opt', 'ext4', '/dev/sda2') == False
    assert _should_include_mount('/usr', 'ext4', '/dev/sda3') == False
    assert _should_include_mount('/var', 'ext4', '/dev/sda4') == False