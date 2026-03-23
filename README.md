# diskcomp

[![CI](https://github.com/w1lkns/diskcomp/workflows/CI/badge.svg)](https://github.com/w1lkns/diskcomp/actions)
[![PyPI version](https://img.shields.io/pypi/v/diskcomp.svg)](https://pypi.org/project/diskcomp/)

Compare two drives and find duplicate files. Zero dependencies, cross-platform, with undo.

## Quick Install

**pipx** (recommended — handles PATH automatically):
```bash
pipx install diskcomp
diskcomp --help
```

> Don't have pipx? `brew install pipx` on macOS, `pip install pipx` elsewhere.

**pip install** (once published to PyPI):
```bash
pip install diskcomp
diskcomp --help
```

**Single-file version** (no dependencies):
```bash
curl -O https://raw.githubusercontent.com/w1lkns/diskcomp/main/diskcomp.py
python3 diskcomp.py --help
```

**Development install** (from source):
```bash
git clone https://github.com/w1lkns/diskcomp.git
cd diskcomp
pip install -e .
diskcomp --help
```

## Quick Start

**Interactive mode** (no arguments, prompts for drives):
```bash
python3 -m diskcomp
```

**Command-line** (specify drives):
```bash
python3 -m diskcomp --keep /path/to/keep/drive --other /path/to/other/drive
```

**Dry-run** (preview without hashing, for quick sanity check):
```bash
python3 -m diskcomp --keep /path/A --other /path/B --dry-run
```

## Usage & Flags

| Flag | Description | Example |
|------|-------------|---------|
| `--keep PATH` | Path to the "keep" drive (files to retain). Required unless interactive mode. | `--keep /Volumes/backup` |
| `--other PATH` | Path to the "other" drive (compare against). Required unless interactive mode. | `--other /Volumes/external` |
| `--dry-run` | Walk and count files without hashing (quick preview). | `--dry-run` |
| `--limit N` | Hash only first N files per drive (testing only). | `--limit 100` |
| `--output PATH` | Custom report path (default: `~/diskcomp-report-YYYYMMDD-HHMMSS.csv`). | `--output ./my-report.csv` |
| `--format csv\|json` | Report format: `csv` or `json` (default: `csv`). | `--format json` |
| `--delete-from PATH` | Load an existing report and start deletion workflow. | `--delete-from ./diskcomp-report-20260322-235800.csv` |
| `--undo PATH` | View and understand the audit log of deleted files. | `--undo ./diskcomp-undo-20260322-235800.json` |

## How It Works

1. **Drive Health Checks** (pre-scan):
   - Space summary for both drives
   - Filesystem detection (HFS+, NTFS, ext4, etc.)
   - Read-only detection (warns if "keep" drive is read-only)
   - Read speed test (128MB)
   - Optional SMART data (if `smartmontools` available)

2. **Scanning & Hashing**:
   - Walks both drives recursively
   - Skips OS noise (System Volume Information, .DS_Store, Thumbs.db, etc.)
   - SHA256 hashes all files ≥1KB
   - Live progress bar with speed and ETA

3. **Reporting**:
   - CSV or JSON report with duplicates and unique files
   - Columns: action, keep_path, other_path, size_mb, hash
   - Atomic writes (temp → rename for crash safety)

4. **Deletion Workflow** (optional, `-—delete-from`):
   - **Mode A (Interactive):** Per-file confirmation with 4 choices (yes/no/skip/abort)
   - **Mode B (Batch):** Dry-run preview → type "DELETE" to confirm → progress callbacks
   - Undo log written BEFORE deletion (audit-first pattern)
   - Always abortable with `Ctrl+C`

5. **Undo Log** (`--undo` flag):
   - JSON file listing all deleted files with timestamps
   - Shows what was deleted and when
   - Helps verify deletion safety after-the-fact

## Safety Model

**The user is always in control.** diskcomp prioritizes safety over convenience:

- **No automatic deletion** — every destructive action requires explicit confirmation
- **Undo log first** — log written before any file is deleted (audit trail)
- **Read-only detection** — warns if "keep" drive appears read-only (prevents accidental writes)
- **Dry-run mode** — preview all operations without side effects
- **Abortable** — press `Ctrl+C` at any prompt to stop safely

## Known Limitations

### NTFS Drives on macOS and Linux

NTFS (Windows filesystem) drives are read-only on macOS and Linux by default. This means:
- diskcomp can **scan** and **identify** duplicates on NTFS drives
- diskcomp **cannot delete** files from NTFS drives (parent filesystem restriction)

**Workaround:**
If you need to delete from an NTFS drive on macOS or Linux, install a third-party NTFS driver:
- **macOS**: Use [ntfs-3g with macFUSE](https://github.com/gromgit/homebrew-fuse) or [Tuxera NTFS](https://www.tuxera.com/products/ntfs-for-mac/)
- **Linux**: Install `ntfs-3g` package: `sudo apt install ntfs-3g` (Debian/Ubuntu) or `sudo dnf install ntfs-3g` (Fedora)

diskcomp will detect this limitation and warn you during health checks.

## Optional Enhancements

**Rich library** — professional progress bars and styling:
```bash
pip install diskcomp[rich]
```

**smartmontools** — enables SMART data display (optional system package):
- **macOS:** `brew install smartmontools`
- **Linux:** `apt-get install smartmontools` (Debian/Ubuntu) or `pacman -S smartmontools` (Arch)
- **Windows:** `wmic logicaldisk` (built-in, no install needed)

Without these, diskcomp gracefully falls back to ANSI progress bars and skips SMART data.

## Reports

**CSV format** (default, spreadsheet-friendly):
```csv
action,keep_path,other_path,size_mb,hash
DUPLICATE,/Volumes/keep/photos/pic1.jpg,/Volumes/other/photos/pic1.jpg,2.5,abc123...
UNIQUE_TO_KEEP,/Volumes/keep/docs/resume.pdf,,0.1,def456...
UNIQUE_TO_OTHER,,/Volumes/other/temp/junk.tmp,5.0,ghi789...
```

**JSON format** (programmatic use):
```bash
python3 -m diskcomp --keep /Volumes/keep --other /Volumes/other --format json
```

## Cross-Platform Testing

CI validates diskcomp on **9 combinations**:
- **macOS** (latest) × Python 3.8, 3.10, 3.12
- **Linux** (Ubuntu latest) × Python 3.8, 3.10, 3.12
- **Windows** (latest) × Python 3.8, 3.10, 3.12

All tests pass and the single-file build is verified on each combo.

## Development

**Run tests locally:**
```bash
python -m unittest discover tests/
```

**Generate single-file version:**
```bash
python build_single.py
python diskcomp.py --help
```

## License

MIT — See LICENSE file for details.
