# Phase 3: Drive Health + Setup - Research

**Researched:** 2026-03-22
**Domain:** Cross-platform disk health monitoring, filesystem detection, interactive drive enumeration, read speed benchmarking
**Confidence:** HIGH

## Summary

Phase 3 requires five technical capabilities: (1) reporting disk space statistics, (2) detecting filesystem types, (3) enumerating mounted drives interactively, (4) benchmarking sequential read performance, and (5) optionally retrieving SMART health data. The Python standard library provides most requirements via `shutil.disk_usage()` and `os.access()`; filesystem detection and drive enumeration require platform-specific tools (psutil or subprocess calls to native commands); SMART data is optional and requires the `smartmontools` external tool.

The codebase already patterns optional dependencies with try/except ImportError, graceful fallback, and factory patterns (see: `UIHandler` in ui.py). Phase 3 follows the same pattern: disk space and read-only checks use stdlib; filesystem enumeration prefers `psutil.disk_partitions()` but falls back to subprocess + platform-native commands if psutil unavailable; SMART data gracefully skips if smartmontools not installed; interactive drive picker uses plain `input()` with validation loop.

**Primary recommendation:** Use `shutil.disk_usage()` for space (stdlib, cross-platform), `psutil.disk_partitions()` as optional dependency for drive enumeration with subprocess fallback, `os.access(path, os.W_OK)` for write-permission checks, platform-specific subprocess calls for filesystem types when psutil unavailable, and `smartctl` via subprocess (from smartmontools package) for optional SMART reporting.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `shutil` | stdlib | Disk space reporting via `disk_usage(path)` — cross-platform, no deps | Stdlib, proven for space queries across macOS/Linux/Windows (Python 3.3+) |
| `os.access()` | stdlib | Check read-write permissions via `os.access(path, os.W_OK)` | Stdlib, cross-platform write-permission detection, simple sentinel for read-only drives |
| `tempfile` | stdlib | Create temporary test files for read-speed benchmarking | Stdlib, secure temp file creation with automatic cleanup |
| `time` | stdlib | Measure sequential read duration in seconds/milliseconds | Stdlib, sufficient granularity for 128MB read timing |
| `subprocess` | stdlib | Call platform-native commands (diskutil, wmic, mount/df) | Stdlib, required for filesystem type detection when psutil absent |

### Supporting (Recommended)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `psutil` | ≥5.4 | `disk_partitions()` returns device/mountpoint/fstype tuples | If available, simplifies drive enumeration and filesystem detection across macOS/Linux/Windows; gracefully skip if missing |
| `smartmontools` | system tool | `smartctl` command for SMART health data | Optional: if `smartctl` on PATH, display health; skip warning if absent |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `psutil.disk_partitions()` | `subprocess` + `df` (Unix) / `diskutil` (macOS) / `wmic` (Windows) | psutil is single unified API; subprocess requires per-platform parsing logic and error handling. Use subprocess when psutil unavailable. |
| `os.access(path, os.W_OK)` | `os.statvfs()` (Unix only) + platform APIs (Windows) | `os.access()` is cross-platform; `os.statvfs()` only Unix; Windows requires different approach. Use `os.access()` as primary. |
| Plain `input()` for drive picker | Rich `Prompt.ask()` | Plain input works always; Rich requires optional dep. Both valid; use input() for consistency with existing ANSI fallback pattern. |
| Sequential read test via tempfile | Write-then-read test | Tempfile allows read-only test (avoids side effects); write-then-read measures both I/O, less clean. Use read-only approach. |

**Installation:**
```bash
# Core dependencies (zero mandatory for Phase 3)
pip install psutil  # Optional: makes drive enumeration simpler

# System dependency (optional)
# macOS: brew install smartmontools
# Linux: apt-get install smartmontools
# Windows: choco install smartmontools
```

**Version verification:**
- `psutil`: Latest stable is 6.0.0 (Feb 2025). Cross-platform disk_partitions() stable since 5.4.
- `smartmontools`: Various distributions; recent v7.3+ support JSON output (`smartctl -j` flag).
- All stdlib APIs (shutil, os, tempfile, time, subprocess) stable in Python 3.8+.

## Architecture Patterns

### Recommended Project Structure
```
diskcomp/
├── health.py          # NEW: Drive health checks (space, SMART, read-only detection)
├── drive_picker.py    # NEW: Interactive drive enumeration and user selection
├── benchmarker.py     # NEW: Read speed testing (128MB sequential read)
├── cli.py             # MODIFIED: Route no-args → interactive setup
├── types.py           # EXTENDED: DriveInfo, HealthCheckResult dataclasses
└── ...existing files
```

### Pattern 1: Optional Dependency Detection with Graceful Fallback

**What:** Try importing optional library; fall back to alternative (stdlib, subprocess, or skip feature) if unavailable.

**When to use:** psutil for drive enumeration, smartmontools for SMART data, Rich for UI (already implemented in Phase 2).

**Example:**
```python
# diskcomp/health.py

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

def get_drives():
    """
    Returns list of mounted drives with device/mountpoint/fstype.
    Uses psutil if available, else falls back to platform-specific commands.
    """
    if PSUTIL_AVAILABLE:
        return _get_drives_psutil()
    else:
        return _get_drives_subprocess()

def _get_drives_psutil():
    """Uses psutil.disk_partitions() — simple, cross-platform."""
    drives = []
    for partition in psutil.disk_partitions(all=False):  # all=False filters out pseudo/virtual
        drives.append({
            'device': partition.device,
            'mountpoint': partition.mountpoint,
            'fstype': partition.fstype,
        })
    return drives

def _get_drives_subprocess():
    """Falls back to subprocess + platform-native commands."""
    if sys.platform == 'darwin':
        return _get_drives_macos()
    elif sys.platform == 'win32':
        return _get_drives_windows()
    elif sys.platform == 'linux':
        return _get_drives_linux()
    return []

def _get_drives_macos():
    """Parse diskutil list -plist on macOS."""
    # Source: https://docs.python.org/3/library/subprocess.html
    # diskutil list -plist | plistlib.loads() → device/mount/fstype
    ...

def _get_drives_windows():
    """Parse wmic logicaldisk on Windows."""
    # wmic logicaldisk get name,filesystem,size,freespace
    # Or: os.listdrives() (Python 3.12+) for drive letters C:\ D:\ ...
    ...

def _get_drives_linux():
    """Parse /proc/mounts or mount command on Linux."""
    # Source: /proc/mounts format
    ...
```

Source: [Python subprocess documentation](https://docs.python.org/3/library/subprocess.html)

### Pattern 2: Space Reporting and Read-Only Detection

**What:** Use `shutil.disk_usage(path)` for space stats; use `os.access(path, os.W_OK)` to flag read-only drives.

**When to use:** Before scan starts, show user what they're working with.

**Example:**
```python
# diskcomp/health.py

import shutil
import os

def check_drive_health(mount_point):
    """
    Returns dict with space usage and read-write status.

    Returns:
        {
            'mountpoint': '/Volumes/Drive',
            'total_gb': 500.0,
            'used_gb': 250.5,
            'free_gb': 249.5,
            'is_writable': True,
            'warnings': ['NTFS read-only: mounted via macFUSE without write support']
        }
    """
    usage = shutil.disk_usage(mount_point)
    is_writable = os.access(mount_point, os.W_OK)

    warnings = []
    if not is_writable:
        warnings.append('DRIVE IS READ-ONLY: cannot write to this path')
        # Additional check: NTFS on macOS?
        fstype = get_filesystem_type(mount_point)
        if fstype == 'ntfs':
            warnings.append('NTFS detected on macOS: often read-only without macFUSE+NTFS-3G')

    return {
        'mountpoint': mount_point,
        'total_gb': round(usage.total / (1024**3), 2),
        'used_gb': round(usage.used / (1024**3), 2),
        'free_gb': round(usage.free / (1024**3), 2),
        'is_writable': is_writable,
        'warnings': warnings,
    }
```

Source: [Python shutil documentation](https://docs.python.org/3/library/shutil.html)

### Pattern 3: Read Speed Benchmarking

**What:** Create 128MB temporary file, read it sequentially in chunks, measure elapsed time, calculate MB/s.

**When to use:** Detect slow or failing drives before starting the scan.

**Example:**
```python
# diskcomp/benchmarker.py

import tempfile
import os
import time

def benchmark_read_speed(mount_point, test_size_mb=128, chunk_size_kb=512):
    """
    Benchmarks sequential read speed on mount_point.

    Creates temporary 128MB file in mount_point, reads it in chunks,
    measures elapsed time, deletes temp file.

    Returns:
        {
            'mountpoint': '/Volumes/Drive',
            'speed_mbps': 45.2,
            'duration_secs': 2.83,
            'success': True,
            'error': None,
        }
    """
    test_size_bytes = test_size_mb * (1024 ** 2)
    chunk_size_bytes = chunk_size_kb * 1024

    # Create temp file on target drive
    temp_fd, temp_path = tempfile.mkstemp(dir=mount_point, prefix='diskcomp_bench_')

    try:
        # Write 128MB of test data (required for read benchmark)
        # Note: We MUST write first; can't benchmark read from non-existent file
        bytes_written = 0
        with os.fdopen(temp_fd, 'wb') as f:
            while bytes_written < test_size_bytes:
                chunk = b'\0' * min(chunk_size_bytes, test_size_bytes - bytes_written)
                f.write(chunk)
                bytes_written += len(chunk)

        # Now read it sequentially and time
        start_time = time.time()
        bytes_read = 0
        with open(temp_path, 'rb') as f:
            while bytes_read < test_size_bytes:
                chunk = f.read(chunk_size_bytes)
                if not chunk:
                    break
                bytes_read += len(chunk)
        elapsed = time.time() - start_time

        speed_mbps = (bytes_read / (1024 ** 2)) / elapsed if elapsed > 0 else 0

        return {
            'mountpoint': mount_point,
            'speed_mbps': round(speed_mbps, 2),
            'duration_secs': round(elapsed, 3),
            'bytes_read': bytes_read,
            'success': True,
            'error': None,
        }

    except Exception as e:
        return {
            'mountpoint': mount_point,
            'speed_mbps': 0,
            'duration_secs': 0,
            'bytes_read': 0,
            'success': False,
            'error': str(e),
        }

    finally:
        # Clean up temp file
        try:
            os.remove(temp_path)
        except:
            pass
```

### Pattern 4: Interactive Drive Picker

**What:** List all mounted drives, show space/filesystem info, ask user to pick keep/other, validate input.

**When to use:** `diskcomp` with no args launches interactive mode (requirement SETUP-01/02).

**Example:**
```python
# diskcomp/drive_picker.py

def interactive_drive_picker():
    """
    Lists all mounted drives, shows health info, asks user to pick keep/other.

    Returns:
        {'keep': '/Volumes/KeepDrive', 'other': '/Volumes/OtherDrive'}
    """
    drives = get_drives()

    if not drives:
        print("Error: No mounted drives detected.", file=sys.stderr)
        return None

    print("\n=== Available Drives ===\n")
    for i, drive in enumerate(drives, 1):
        health = check_drive_health(drive['mountpoint'])
        print(f"{i}. {drive['mountpoint']}")
        print(f"   Filesystem: {drive['fstype']}")
        print(f"   Space: {health['used_gb']}GB / {health['total_gb']}GB used")
        print(f"   Writable: {'Yes' if health['is_writable'] else 'NO (READ-ONLY)'}")
        if health['warnings']:
            for warning in health['warnings']:
                print(f"   WARNING: {warning}")
        print()

    # Ask user for keep drive
    keep_index = _prompt_for_drive_index("Which drive to KEEP?", len(drives))
    keep_drive = drives[keep_index]['mountpoint']

    # Ask user for other drive
    remaining = [d for i, d in enumerate(drives) if i != keep_index]
    if not remaining:
        print("Error: Need at least 2 drives to compare.", file=sys.stderr)
        return None

    print(f"\nKeep drive: {keep_drive}")
    print(f"\nRemaining drives for comparison:")
    for i, drive in enumerate(remaining, 1):
        print(f"{i}. {drive['mountpoint']}")

    other_index = _prompt_for_drive_index("Which drive to compare (OTHER)?", len(remaining))
    other_drive = remaining[other_index]['mountpoint']

    return {'keep': keep_drive, 'other': other_drive}

def _prompt_for_drive_index(prompt_text, max_index):
    """
    Prompts user to pick a number 1..max_index, keeps asking until valid.
    """
    while True:
        response = input(f"{prompt_text} (1-{max_index}): ").strip()
        try:
            index = int(response) - 1
            if 0 <= index < max_index:
                return index
        except ValueError:
            pass
        print(f"Invalid selection. Enter a number between 1 and {max_index}.")
```

### Pattern 5: SMART Data (Optional)

**What:** If `smartctl` (from smartmontools) is available on PATH, run it to get drive health; skip gracefully if not.

**When to use:** Optional feature; drives without SMART or tool not installed should not block setup.

**Example:**
```python
# diskcomp/health.py

import subprocess
import json

def get_smart_data(device_path):
    """
    Retrieves SMART health data for device via smartctl.
    If smartctl not available or errors, returns None (graceful skip).

    Args:
        device_path: e.g., '/dev/sda' or 'pd0' (platform-dependent)

    Returns:
        {
            'device': '/dev/sda',
            'health_status': 'PASSED',  # or 'FAILED'
            'temperature_c': 35,
            'error': None,
        }
        OR None if smartctl unavailable or fails
    """
    try:
        # Try JSON output first (smartmontools v7+)
        result = subprocess.run(
            ['smartctl', '-j', device_path],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0 or result.returncode == 2:  # 0=ok, 2=warnings
            data = json.loads(result.stdout)
            return {
                'device': device_path,
                'health_status': data.get('smart_status', {}).get('passed', 'UNKNOWN'),
                'temperature_c': data.get('temperature', {}).get('current_celsius'),
                'error': None,
            }

    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        # smartctl not found or error; gracefully skip
        return None

    except Exception as e:
        # Unexpected error; log and skip
        return None
```

Source: [pySMART library documentation](https://pypi.org/project/pySMART/)

### Anti-Patterns to Avoid
- **Mandatory SMART data:** If smartmontools not installed, should warn but not block. Graceful degradation required.
- **Assuming `os.statvfs()` available everywhere:** Only Unix; use cross-platform `os.access()` instead.
- **Hard-coded drive paths:** Use enumeration (psutil or subprocess) to discover drives at runtime.
- **Blocking on slow benchmarks:** Run benchmark with timeout (e.g., 30-second max) and skip if slow.
- **No validation on user input:** Drive picker must loop until valid selection or abort.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cross-platform drive enumeration | Custom per-platform logic for each OS | `psutil.disk_partitions()` or subprocess fallback | Enum logic has many edge cases (mount options, virtual drives, permissions) — psutil handles this. |
| Disk space calculation | Manual math (bytes → GB → formatting) | `shutil.disk_usage()` | Returns (total, used, free) tuple; math already done. |
| SMART parsing | Hand-parse smartctl output lines/regex | pySMART library or JSON via `smartctl -j` | smartctl output format varies by tool version and drive; pySMART handles parsing. JSON (v7+) is simpler. |
| Read-only detection | Try writing test file | `os.access(path, os.W_OK)` | Direct check avoids side effects and race conditions. |
| Temporary test file | `mktemp` command via subprocess | `tempfile.mkstemp()` | Stdlib is cross-platform, secure (perms 0o600), atomic cleanup. |

**Key insight:** Disk enumeration, space calculation, and permission checks are deceptively complex — multiple platforms have quirks (NTFS on macOS read-only behavior, virtual drives, mount permissions). Use libraries/stdlib where possible.

## Common Pitfalls

### Pitfall 1: Assuming `psutil` Always Available
**What goes wrong:** Code assumes `psutil.disk_partitions()` exists; crashes if not installed.

**Why it happens:** Phase 1/2 designed zero mandatory dependencies; psutil should remain optional for Phase 3.

**How to avoid:** Wrap psutil import in try/except; implement subprocess fallback per platform.

**Warning signs:** ImportError on first run; can't use `psutil` in non-sudo environment.

### Pitfall 2: NTFS Read-Only Detection Not Caught
**What goes wrong:** User on macOS with NTFS drive sees "Writable: Yes" from `os.access()`, but drive is actually read-only via macFUSE limitations.

**Why it happens:** `os.access()` checks Unix file permissions, not filesystem-level constraints. macOS NTFS-3G mounts with r/w perms but enforces read-only at FS level.

**How to avoid:** After filesystem type detection shows "ntfs", add explicit warning: "NTFS on macOS may be read-only unless macFUSE+NTFS-3G installed with write support."

**Warning signs:** User writes to drive successfully in Finder but not in diskcomp; check fstype + platform.

### Pitfall 3: Benchmark Timeout on Slow Drives
**What goes wrong:** 128MB read test hangs on dead USB drive; user waits 5+ minutes.

**Why it happens:** No timeout on benchmark subprocess; test_size_mb too large for slow media.

**How to avoid:** Wrap benchmark in `subprocess.run(..., timeout=30)` or implement per-chunk timeout; skip benchmark if exceeds threshold.

**Warning signs:** Benchmark runs longer than 30 seconds; user can interrupt but no graceful exit.

### Pitfall 4: Interactive Picker Crashes on Mounted-But-Unreadable Drive
**What goes wrong:** `get_drives()` returns a drive path that `os.access()` can't check (permission denied on root).

**Why it happens:** `disk_partitions()` shows all mounted drives; some may not be readable by current user.

**How to avoid:** Wrap `check_drive_health()` in try/except; if inaccessible, show warning but don't crash.

**Warning signs:** OSError from `os.access()` or `shutil.disk_usage()`; user can't proceed with setup.

### Pitfall 5: Windows Drive Letter Enumeration Missing External Drives
**What goes wrong:** `wmic logicaldisk` shows C: D: but misses USB drives or network shares.

**Why it happens:** Subprocess command may filter by DriveType or exclude removable media.

**How to avoid:** Test on Windows with external drive; ensure wmic query includes all mount points.

**Warning signs:** User plugs USB drive but it doesn't appear in picker.

## Code Examples

Verified patterns from official sources:

### Check Disk Space (shutil.disk_usage)
```python
# Source: https://docs.python.org/3/library/shutil.html
import shutil

usage = shutil.disk_usage('/Volumes/MyDrive')
total_gb = usage.total / (1024 ** 3)
used_gb = usage.used / (1024 ** 3)
free_gb = usage.free / (1024 ** 3)
print(f"Total: {total_gb:.2f}GB, Used: {used_gb:.2f}GB, Free: {free_gb:.2f}GB")
```

### Check Write Permission (os.access)
```python
# Source: https://docs.python.org/3/library/os.html#os.access
import os

if os.access('/Volumes/MyDrive', os.W_OK):
    print("Drive is writable")
else:
    print("Drive is read-only")
```

### List Drives with psutil (Recommended)
```python
# Source: https://psutil.readthedocs.io/en/latest/
import psutil

for partition in psutil.disk_partitions(all=False):
    print(f"Device: {partition.device}")
    print(f"Mount: {partition.mountpoint}")
    print(f"Filesystem: {partition.fstype}")
    print()
```

### List Drives Fallback: macOS (diskutil list -plist)
```python
# Source: https://commandmasters.com/commands/diskutil-osx/
import subprocess
import plistlib

result = subprocess.run(
    ['diskutil', 'list', '-plist'],
    capture_output=True,
    text=False,
)
plist_data = plistlib.loads(result.stdout)
# Parse plist_data['AllDisksAndPartitions'] for mount points and fstype
```

### List Drives Fallback: Windows (os.listdrives or wmic)
```python
# Source: https://docs.python.org/3/library/os.html (Python 3.12+)
# Option 1: Python 3.12+
import os
drives = os.listdrives()  # Returns ['C:\\', 'D:\\', ...]

# Option 2: Older Python + wmic
import subprocess
result = subprocess.run(
    ['wmic', 'logicaldisk', 'get', 'name', '/format:csv'],
    capture_output=True,
    text=True,
)
# Parse CSV output for drive letters
```

### SMART Health Check (smartctl with JSON)
```python
# Source: https://linux.die.net/man/8/smartctl
import subprocess
import json

result = subprocess.run(
    ['smartctl', '-j', '/dev/sda'],
    capture_output=True,
    text=True,
    timeout=10,
)
if result.returncode in [0, 2]:  # 0=ok, 2=warnings OK
    data = json.loads(result.stdout)
    health = data.get('smart_status', {}).get('passed')
    temp = data.get('temperature', {}).get('current_celsius')
    print(f"Health: {health}, Temp: {temp}°C")
```

### Sequential Read Benchmark (tempfile + timing)
```python
# Source: https://realpython.com/ref/stdlib/tempfile/
import tempfile
import time
import os

mount_point = '/Volumes/MyDrive'
test_size_mb = 128
chunk_size_kb = 512

test_bytes = test_size_mb * (1024 ** 2)
chunk_bytes = chunk_size_kb * 1024

# Create temp file on target drive
fd, temp_path = tempfile.mkstemp(dir=mount_point)
try:
    # Write test data
    with os.fdopen(fd, 'wb') as f:
        f.write(b'\0' * test_bytes)

    # Measure read speed
    start = time.time()
    with open(temp_path, 'rb') as f:
        while True:
            chunk = f.read(chunk_bytes)
            if not chunk:
                break
    elapsed = time.time() - start

    speed_mbps = (test_bytes / (1024 ** 2)) / elapsed
    print(f"Read speed: {speed_mbps:.2f} MB/s")

finally:
    os.remove(temp_path)
```

### Interactive User Input with Validation
```python
# Source: https://automatetheboringstuff.com/2e/chapter8/
def prompt_for_confirmation(prompt_text):
    """Keeps asking until user enters y/n."""
    while True:
        response = input(f"{prompt_text} (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please enter 'y' or 'n'.")

# Usage
if prompt_for_confirmation("Start scan?"):
    print("Scanning...")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hand-parsed `df` output | `psutil.disk_partitions()` + fallback subprocess | psutil v5.4+ (2017) | Simpler, cross-platform code; optional dep keeps zero mandatory. |
| Single-platform hardcoding | Try/except imports + per-platform fallbacks | Throughout Phase 1/2 | Code works everywhere; degrades gracefully without optional deps. |
| No SMART data | Optional `smartctl` via subprocess (smartmontools v7 adds JSON) | smartmontools v7 (2020) | JSON parsing simpler than regex; skip gracefully if tool absent. |
| Manual write tests for read-only | Direct `os.access(path, os.W_OK)` check | Always available in stdlib | Faster, no side effects, avoids race conditions. |

**Deprecated/outdated:**
- Manual regex parsing of smartctl output: smartmontools v7+ supports JSON (`smartctl -j`); use that.
- Hardcoded `/Volumes/*` on macOS: use enumeration APIs instead.

## Open Questions

1. **Should benchmark be mandatory or optional?**
   - What we know: Requirements say "flags slow/failing drives" but also "health failures are warnings, not blockers."
   - What's unclear: Does user MUST benchmark before scan, or is it optional info?
   - Recommendation: Make it optional; show result if test succeeds/fails, but don't block scan start.

2. **How to detect NTFS write-ability on macOS reliably?**
   - What we know: macOS NTFS mounts read-only by default; macFUSE+NTFS-3G can enable write.
   - What's unclear: How to distinguish "read-only because NTFS" vs "read-only because permissions"?
   - Recommendation: Check filesystem type first (psutil/subprocess); if NTFS+macOS, show explicit warning. Use `os.access()` for base check.

3. **Should we support Python 3.8 with `os.listdrives()` fallback missing?**
   - What we know: `os.listdrives()` only available Python 3.12+; diskcomp targets 3.8+.
   - What's unclear: Which Windows enumeration approach to default to?
   - Recommendation: Use `wmic` via subprocess for Python <3.12; use `os.listdrives()` for 3.12+.

4. **Timeout strategy for slow drives:**
   - What we know: 128MB benchmark could hang on dead USB.
   - What's unclear: What timeout is user-acceptable? (5s? 30s?)
   - Recommendation: 30-second timeout per benchmark; warn if timeout exceeded, skip benchmark result. Don't block scan.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | unittest (stdlib) — consistent with Phase 1/2 |
| Config file | None — tests in `tests/test_health.py` |
| Quick run command | `python -m pytest tests/test_health.py -x` (or `unittest discover -s tests -p "test_health.py"` for no deps) |
| Full suite command | `python -m pytest tests/ -x` (all phase tests) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HLTH-01 | Space summary shown per drive before scan | unit | `unittest tests.test_health.TestDriveHealth.test_disk_usage_summary` | ❌ Wave 0 |
| HLTH-02 | Filesystem type detected with cross-platform warnings | unit | `unittest tests.test_health.TestFilesystemDetection.test_detect_ntfs_readonly_macos` | ❌ Wave 0 |
| HLTH-03 | Read benchmark 128MB, flags slow/fails | unit | `unittest tests.test_health.TestBenchmark.test_read_speed_benchmark` | ❌ Wave 0 |
| HLTH-04 | SMART data displayed or skipped gracefully | unit | `unittest tests.test_health.TestSMART.test_smart_graceful_skip` | ❌ Wave 0 |
| HLTH-05 | Health failures are warnings, not blockers | integration | `unittest tests.test_health.TestIntegration.test_health_warnings_dont_block` | ❌ Wave 0 |
| SETUP-01 | Interactive mode lists drives, asks keep/other | unit | `unittest tests.test_drive_picker.TestInteractive.test_pick_drives_with_input` | ❌ Wave 0 |
| SETUP-02 | Drive detection shows size/filesystem for picking | unit | `unittest tests.test_drive_picker.TestDriveEnum.test_enumerate_drives` | ❌ Wave 0 |
| SETUP-03 | Non-interactive `--keep/--other` flags work | integration | `unittest tests.test_cli.TestSetup.test_cli_keep_other_flags` (existing test, may extend) | ⚠️ Partial |
| SETUP-04 | Aborts with clear message if drives missing/unreadable | unit | `unittest tests.test_health.TestValidation.test_unmounted_drive_validation` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m unittest tests.test_health -v` (all health tests)
- **Per wave merge:** `python -m unittest discover -s tests -p "test_*.py" -v` (full suite)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_health.py` — test health checks (space, SMART, read-only), covers HLTH-01 through HLTH-05
- [ ] `tests/test_drive_picker.py` — test interactive drive enumeration, covers SETUP-01 through SETUP-02, SETUP-04
- [ ] `tests/test_benchmarker.py` — test read-speed benchmark with mocked tempfile, covers HLTH-03
- [ ] `diskcomp/health.py` — implement disk space check, filesystem detection, SMART retrieval (graceful skip)
- [ ] `diskcomp/drive_picker.py` — implement interactive mode, drive enumeration, user input validation
- [ ] `diskcomp/benchmarker.py` — implement 128MB read test, timing, speed calculation
- [ ] Extend `diskcomp/types.py` — add `DriveInfo`, `HealthCheckResult`, `BenchmarkResult` dataclasses
- [ ] Modify `diskcomp/cli.py` — detect no-args case, route to `drive_picker.interactive_drive_picker()`
- [ ] Framework install: stdlib unittest (no install needed)

*(Gaps identified: 9 new test files + 3 implementation modules + 1 extension + 1 cli modification)*

## Sources

### Primary (HIGH confidence)
- [Python shutil documentation](https://docs.python.org/3/library/shutil.html) — `disk_usage()` API and cross-platform support
- [Python os documentation](https://docs.python.org/3/library/os.html) — `os.access()`, `os.listdrives()`, `os.statvfs()`
- [Python tempfile documentation](https://docs.python.org/3/library/tempfile.html) — secure temp file creation
- [psutil disk_partitions documentation](https://psutil.readthedocs.io/en/latest/) — cross-platform drive enumeration
- [smartmontools smartctl man page](https://linux.die.net/man/8/smartctl) — command syntax and exit codes

### Secondary (MEDIUM confidence)
- [diskutil command reference](https://commandmasters.com/commands/diskutil-osx/) — macOS drive enumeration
- [pySMART library documentation](https://pypi.org/project/pySMART/) — SMART parsing alternative
- [Python interactive input patterns](https://automatetheboringstuff.com/2e/chapter8/) — user prompt validation

### Tertiary (LOW confidence)
- WebSearch: NTFS read-only on macOS detection — specific Python code examples limited; based on OS behavior knowledge
- WebSearch: Windows drive enumeration via wmic — parsing format varies; recommend testing on target Windows versions

## Metadata

**Confidence breakdown:**
- Standard stack (shutil, os stdlib): HIGH — official docs confirm cross-platform support in Python 3.8+
- Architecture (patterns, dataclasses): HIGH — Phase 1/2 established same patterns; replicable
- Pitfalls: MEDIUM-HIGH — known issues from web research (NTFS on macOS, psutil availability, timeouts) but some Windows-specific behaviors untested
- SMART integration: MEDIUM — pySMART exists but alternative (manual subprocess + JSON) equally viable
- Filesystem detection fallback: MEDIUM — psutil is clear, but subprocess parsing per platform needs testing

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (stable domain; psutil/smartmontools versions unlikely to change dramatically in 30 days)
