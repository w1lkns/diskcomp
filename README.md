# diskcomp

[![CI](https://github.com/w1lkns/diskcomp/actions/workflows/ci.yml/badge.svg)](https://github.com/w1lkns/diskcomp/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/diskcomp.svg)](https://badge.fury.io/py/diskcomp)
[![Python versions](https://img.shields.io/pypi/pyversions/diskcomp.svg)](https://pypi.org/project/diskcomp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub release](https://img.shields.io/github/v/release/w1lkns/diskcomp.svg)](https://github.com/w1lkns/diskcomp/releases/latest)
[![Platform support](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-blue.svg)](#quick-install)
[![Standalone binaries](https://img.shields.io/badge/binaries-macOS%20%7C%20Linux%20%7C%20Windows-green.svg)](https://github.com/w1lkns/diskcomp/releases/latest)

Find and safely delete duplicate files — across two drives or within one. **Zero dependencies, cross-platform, with undo.**

## ✨ Key Features

- **🔍 Smart Detection** — SHA256 hashing finds true duplicates regardless of filename
- **⚡ Performance** — Two-pass scan: filter by size first, hash only size-collision candidates  
- **🛡️ Safety First** — Always ask before deleting, create undo logs, detect read-only files
- **🖥️ Cross-Platform** — macOS, Linux, Windows with native progress bars (Rich UI + ANSI fallback)
- **📊 Rich Reports** — CSV/JSON output with file paths, sizes, hashes, and deletion recommendations
- **🎯 Flexible Modes** — Compare two drives, clean single drive, interactive deletion, batch operations
- **⚙️ Zero Dependencies** — Pure Python, optional Rich UI, works everywhere Python runs
- **📦 Multiple Install Options** — pip, pipx, standalone binaries, or Homebrew

## 📊 Project Status

**diskcomp 1.0.0** is production-ready and actively maintained. The core deduplication engine has been tested with **285 comprehensive tests** covering edge cases, cross-platform compatibility, and error handling.

- ✅ **Feature Complete** — All planned v1.0 features implemented
- ✅ **Well Tested** — 285 tests, CI on 3 platforms × 3 Python versions  
- ✅ **Production Ready** — Used for real data cleanup with safety guarantees
- ✅ **Cross-Platform** — Native builds for macOS, Linux, Windows
- ✅ **Multiple Distribution Channels** — PyPI, GitHub Releases, Homebrew ready

## Quick Install

**Download binary** (no Python required):

**macOS:**
```bash
# Homebrew
brew tap w1lkns/diskcomp
brew install diskcomp

# Or download directly
curl -L -o diskcomp https://github.com/w1lkns/diskcomp/releases/latest/download/diskcomp-macos
chmod +x diskcomp
./diskcomp --help
```

**Linux:**
```bash
# Download directly  
curl -L -o diskcomp https://github.com/w1lkns/diskcomp/releases/latest/download/diskcomp-linux
chmod +x diskcomp
./diskcomp --help
```

**Windows:**
```cmd
# Download diskcomp-windows.exe from GitHub Releases
# https://github.com/w1lkns/diskcomp/releases/latest
diskcomp-windows.exe --help
```

**Python install** (if you have Python):

**pipx** (recommended — handles PATH automatically):
```bash
pipx install diskcomp
diskcomp --help
```

> Don't have pipx? `brew install pipx` on macOS, `pip install pipx` elsewhere.

**pip install**:
```bash
pip install diskcomp
diskcomp --help
```

**Single-file version** (no install, no dependencies):
```bash
curl -O https://raw.githubusercontent.com/w1lkns/diskcomp/main/diskcomp.py
python3 diskcomp.py --help
```

## Quick Start

**Interactive mode** (no arguments — clears screen, shows menu):
```bash
diskcomp
```

The launch menu offers:
```
  1) Compare two drives
  2) Clean up a single drive
  3) Load previous report
  4) Help
  5) Quit
```

**Compare two drives** (command-line):
```bash
diskcomp --keep /Volumes/backup --other /Volumes/external
```

**Clean up a single drive** (find internal duplicates):
```bash
diskcomp --single /Volumes/my-drive
```

**Dry-run** (count files without hashing):
```bash
diskcomp --keep /path/A --other /path/B --dry-run
```

**Load a previous report** (skip re-scanning):
```bash
diskcomp --delete-from ./diskcomp-report-20260322-235800.csv
```

## 📊 Example Output

**Interactive mode startup:**
```
 ██████╗ ██╗███████╗██╗  ██╗ ██████╗ ██████╗ ███╗   ███╗██████╗
 ██╔══██╗██║██╔════╝██║ ██╔╝██╔════╝██╔═══██╗████╗ ████║██╔══██╗
 ██║  ██║██║███████╗█████╔╝ ██║     ██║   ██║██╔████╔██║██████╔╝
 ██║  ██║██║╚════██║██╔═██╗ ██║     ██║   ██║██║╚██╔╝██║██╔═══╝
 ██████╔╝██║███████║██║  ██╗╚██████╗╚██████╔╝██║ ╚═╝ ██║██║
 ╚═════╝ ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═╝     ╚═╝╚═╝

 Find duplicates. Free space. Stay safe.
 v1.0.0

What would you like to do?
  1) Compare two drives
  2) Clean up a single drive  
  3) Load previous report
  4) Help
  5) Quit
```

**Progress display:**
```
Drive Health: Keep=/Volumes/Photos (2TB APFS), Other=/Volumes/Backup (4TB NTFS)
Scanning: ████████████████████████████████ 1,847 files found
Hashing candidates: ██████████████████████████████████ 234/234 files (23.4 MB/s)

Found 42 duplicates. You could free 1.2 GB from /Volumes/Backup. Ready to review?
```

## 🛡️ Safety Guarantees

**Interactive mode startup:**
```
 ██████╗ ██╗███████╗██╗  ██╗ ██████╗ ██████╗ ███╗   ███╗██████╗
 ██╔══██╗██║██╔════╝██║ ██╔╝██╔════╝██╔═══██╗████╗ ████║██╔══██╗
 ██║  ██║██║███████╗█████╔╝ ██║     ██║   ██║██╔████╔██║██████╔╝
 ██║  ██║██║╚════██║██╔═██╗ ██║     ██║   ██║██║╚██╔╝██║██╔═══╝
 ██████╔╝██║███████║██║  ██╗╚██████╗╚██████╔╝██║ ╚═╝ ██║██║
 ╚═════╝ ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═╝     ╚═╝╚═╝

 Find duplicates. Free space. Stay safe.
 v1.0.0

What would you like to do?
  1) Compare two drives
  2) Clean up a single drive  
  3) Load previous report
  4) Help
  5) Quit
```

**Progress display:**
```
Drive Health: Keep=/Volumes/Photos (2TB APFS), Other=/Volumes/Backup (4TB NTFS)
Scanning: ████████████████████████████████ 1,847 files found
Hashing candidates: ██████████████████████████████████ 234/234 files (23.4 MB/s)

Found 42 duplicates. You could free 1.2 GB from /Volumes/Backup. Ready to review?
```

**Your files are safe.** diskcomp prioritizes safety over convenience:

- **🔒 No Automatic Deletion** — Every file deletion requires explicit user confirmation  
- **📝 Undo Logs** — Complete audit trail written *before* any file is deleted  
- **⚠️ Read-Only Detection** — Automatically detects and warns about read-only drives  
- **🔍 Dry-Run Mode** — Preview operations without any file system changes  
- **⏹️ Abort Anytime** — Press `Ctrl+C` at any prompt to stop safely  
- **✨ Interactive Mode** — Review each file individually before deletion  
- **🔍 SHA256 Verification** — Cryptographic hashing ensures only true duplicates are identified

## Usage & Flags

| Flag | Description | Example |
|------|-------------|---------|
| `--keep PATH` | Path to the "keep" drive (files to retain). Required unless interactive. | `--keep /Volumes/backup` |
| `--other PATH` | Path to the "other" drive (duplicates deleted from here). Required unless interactive. | `--other /Volumes/external` |
| `--single PATH` | Scan one drive for internal duplicates (redundant copies on the same drive). | `--single /Volumes/photos` |
| `--dry-run` | Walk and count files without hashing (quick preview). | `--dry-run` |
| `--limit N` | Hash only first N files per drive (testing only). | `--limit 100` |
| `--output PATH` | Custom report path (default: `~/diskcomp-report-YYYYMMDD-HHMMSS.csv`). | `--output ./my-report.csv` |
| `--format csv\|json` | Report format: `csv` or `json` (default: `csv`). | `--format json` |
| `--min-size SIZE` | Minimum file size to include (default: `1KB`). Accepts bytes, KB, MB, GB. | `--min-size 10MB` |
| `--delete-from PATH` | Load an existing report and start deletion workflow (skip re-scanning). | `--delete-from ./diskcomp-report-20260322.csv` |
| `--undo PATH` | View the audit log of a previous deletion session. | `--undo ./diskcomp-undo-20260322.json` |

## How It Works

1. **Drive Health Checks** (pre-scan, two-drive mode):
   - Space summary for both drives
   - Filesystem detection (HFS+, NTFS, ext4, exFAT, etc.)
   - Read-only detection (warns if "keep" drive is read-only)
   - Read speed benchmark (128MB)
   - Optional SMART data (if `smartmontools` available)

2. **Scanning & Hashing**:
   - Walks drives recursively
   - Skips OS noise (`.DS_Store`, `Thumbs.db`, `System Volume Information`, etc.)
   - Two-pass optimization: size-filter candidates first, then SHA256 hash
   - Live progress bar with speed and ETA

3. **Reporting**:
   - CSV or JSON report saved to `~/diskcomp-report-YYYYMMDD-HHMMSS.{csv,json}`
   - Atomic writes (temp → rename, safe against crashes mid-write)

4. **Deletion Workflow** (optional):
   - **Mode A (Interactive):** Shows both copies numbered `(1)` and `(2)` — you pick which to delete, skip, or abort. Running space freed shown after each deletion.
   - **Mode B (Batch):** Dry-run preview with file type breakdown → type `DELETE` to confirm → progress bar
   - Undo log written **before** each deletion (audit-first pattern)
   - Always abortable with `Ctrl+C`
   - Can re-run from a saved report without re-scanning (option 3 in menu or `--delete-from`)

5. **Undo Log** (`--undo` flag):
   - JSON file listing all deleted files with paths, sizes, hashes, and timestamps
   - Deletion is permanent — the log is an audit trail, not a restore mechanism

## Reports

**CSV format** (default, spreadsheet-friendly):
```csv
status,original_file,duplicate_file,size_mb,verification_hash
DELETE_FROM_OTHER,/Volumes/keep/photos/pic1.jpg,/Volumes/other/photos/pic1.jpg,2.5,abc123...
UNIQUE_IN_KEEP,/Volumes/keep/docs/resume.pdf,,0.1,def456...
UNIQUE_IN_OTHER,,/Volumes/other/temp/junk.tmp,5.0,ghi789...
```

| Column | Values |
|--------|--------|
| `status` | `DELETE_FROM_OTHER`, `UNIQUE_IN_KEEP`, `UNIQUE_IN_OTHER` |
| `original_file` | Path to the copy to keep |
| `duplicate_file` | Path to the copy to delete |
| `size_mb` | File size in MB |
| `verification_hash` | SHA256 hex string |

**JSON format** (programmatic use):
```bash
diskcomp --keep /Volumes/keep --other /Volumes/other --format json
```

## Known Limitations

### NTFS Drives on macOS and Linux

NTFS (Windows filesystem) drives are read-only on macOS and Linux by default:
- diskcomp can **scan** and **identify** duplicates on NTFS drives
- diskcomp **cannot delete** files from NTFS drives without a third-party driver

**Workaround:**
- **macOS**: [ntfs-3g with macFUSE](https://github.com/gromgit/homebrew-fuse) or [Tuxera NTFS](https://www.tuxera.com/products/ntfs-for-mac/)
- **Linux**: `sudo apt install ntfs-3g` (Debian/Ubuntu) or `sudo dnf install ntfs-3g` (Fedora)

diskcomp detects this and warns during health checks.

## Optional Enhancements

**Rich library** — professional progress bars and color styling:
```bash
pip install diskcomp[rich]
```

**smartmontools** — enables SMART data display:
- **macOS:** `brew install smartmontools`
- **Linux:** `apt-get install smartmontools` or `pacman -S smartmontools`
- **Windows:** `wmic logicaldisk` (built-in, no install needed)

Without these, diskcomp uses ANSI progress bars and skips SMART data.

## Cross-Platform Testing

CI validates diskcomp on **9 combinations**:
- **macOS** (latest) × Python 3.8, 3.10, 3.12
- **Linux** (Ubuntu latest) × Python 3.8, 3.10, 3.12
- **Windows** (latest) × Python 3.8, 3.10, 3.12

All tests pass and the single-file build is verified on each combination.

## Development

**Run tests locally:**
```bash
python -m pytest tests/
```

**Generate single-file version:**
```bash
python build_single.py
python diskcomp.py --help
```

## 🤝 Support & Contributing

- **🐛 Found a bug?** [Report it on GitHub Issues](https://github.com/w1lkns/diskcomp/issues)
- **💡 Feature request?** [Share your idea](https://github.com/w1lkns/diskcomp/issues)  
- **📖 Documentation?** [Improve the README](https://github.com/w1lkns/diskcomp/edit/main/README.md)
- **🔧 Want to contribute?** [Fork & submit a PR](https://github.com/w1lkns/diskcomp/fork)

**⭐ Like diskcomp?** [Star it on GitHub](https://github.com/w1lkns/diskcomp) to show support!

## License

MIT — See LICENSE file for details.
