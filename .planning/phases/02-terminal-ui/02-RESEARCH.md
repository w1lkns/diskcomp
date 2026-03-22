# Phase 2: Terminal UI — Research

**Researched:** 2026-03-22
**Domain:** Cross-platform terminal UI with progress visualization
**Confidence:** HIGH

## Summary

Phase 2 requires replacing raw print() statements with beautiful, cross-platform terminal UI. The two-library approach is optimal: use **Rich** (v14.3.3) when available for professional progress bars and color support, with a **plain ANSI fallback** for environments where rich is not installed. Both approaches are production-ready and work on Windows Terminal, PowerShell, cmd.exe (Windows 10+), macOS Terminal, and Linux.

The key architectural decision is callback-based progress: scanner and hasher will accept optional callback functions to report progress, while the CLI layer handles all rendering via Rich or ANSI. This keeps business logic independent of UI.

**Primary recommendation:** Build a `ui.py` module with two classes: `RichProgressUI` (uses Rich Progress when available) and `ANSIProgressUI` (plain ANSI fallback), both sharing a common interface. CLI detects availability and instantiates the appropriate UI. This allows zero mandatory dependencies while delivering professional-grade output.

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UI-01 | Per-folder progress: cyan arrow while scanning, green tick + file count when done | Rich has SpinnerColumn + TextColumn for this; plain ANSI uses `→` / `✓` with ANSI codes |
| UI-02 | Live hash progress bar with percentage, files done/total, MB/s speed, and ETA | Rich Progress.add_task() + custom columns (BarColumn, TransferSpeedColumn, PercentageColumn); ANSI requires manual calculation |
| UI-03 | Works with `rich` if installed; falls back to plain ANSI if not | Graceful import: `try: import rich; except ImportError: use_ansi=True` |
| UI-04 | Graceful output on Windows terminal (cmd.exe, PowerShell, Windows Terminal) | Windows 10+ supports ANSI natively; Windows Terminal default since Windows 11 22H2; Rich handles all variants |
| UI-05 | Final summary banner: duplicates count + MB, unique count + MB, report path | Rich Panel/Table for summary; ANSI uses box-drawing characters (═, ║, ╔, etc.) |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Rich | 14.3.3 | Terminal rendering: Progress bars, colors, tables, panels | Industry standard for beautiful CLI; zero-dependency on macOS/Linux/Windows 10+; Python 3.8+ compatible |

### Optional (graceful fallback)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Built-in (ANSI) | N/A | Manual ANSI 256-color codes, box drawing, spinner animation | When rich not installed; no external dependency; works on all platforms |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Rich | Click's `echo()` + `style` | Click is simpler but less powerful; no progress bars without additional libs |
| Rich | tqdm | tqdm is lighter-weight but less flexible; harder to integrate fold-by-fold progress |
| Rich | Colorama | Colorama is Windows-specific; doesn't provide progress bars or tables |
| Plain ANSI | Colorama | Colorama is Windows-native conversion; unnecessary if we're already supporting raw ANSI |

**Installation (Optional):**
```bash
pip install rich  # Optional; diskcomp works without it
```

**Version verification:**
- Rich 14.3.3 (current as of 2026-03-22, released 2026-02-19)
- Python 3.8+ required by both Rich and diskcomp

---

## Architecture Patterns

### Recommended Project Structure
```
diskcomp/
├── scanner.py          # (unchanged) — calls on_folder callback
├── hasher.py           # (unchanged) — calls on_file callback
├── cli.py              # (unchanged) — instantiates UI and passes callbacks
├── ui.py               # NEW: Base UIHandler + RichProgressUI + ANSIProgressUI
├── ansi_codes.py       # NEW: ANSI color constants and helpers
└── __main__.py         # (unchanged)
```

### Pattern 1: Callback-Based Progress Reporting

**What:** Scanner and hasher accept optional callback functions (hooks) to report progress. UI handles all rendering.

**When to use:** Decouples business logic from presentation layer. Scanner/hasher are testable without UI.

**Example:**
```python
# Source: Common pattern in Python
def on_folder_done(folder_path: str, file_count: int):
    """Called when scanner completes a folder."""
    pass

def on_file_hashed(file_count: int, total: int, speed_mbps: float, eta_secs: int):
    """Called after hashing each file."""
    pass

# In scanner.py (existing scan() method, enhanced):
def scan(self, dry_run=False, limit=None, on_folder_done=None):
    ...
    for root, dirs, filenames in os.walk(self.root_path):
        ...
        # Process files...
        if on_folder_done:
            on_folder_done(root, len(files_in_folder))

# In hasher.py (new method):
def hash_files(self, records, on_file_hashed=None):
    """Hash multiple files with progress callback."""
    for i, record in enumerate(records):
        record = self.hash_file_record(record)
        if on_file_hashed:
            speed = calculate_speed(...)
            eta = calculate_eta(...)
            on_file_hashed(i + 1, len(records), speed, eta)
        yield record
```

### Pattern 2: Graceful UI Fallback

**What:** Try to import Rich; on ImportError, use plain ANSI.

**When to use:** Zero mandatory dependencies while delivering beautiful output.

**Example:**
```python
# Source: Standard Python import pattern
try:
    from rich.progress import Progress, BarColumn, TransferSpeedColumn
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

class UIHandler:
    """Factory for creating the appropriate UI handler."""
    @staticmethod
    def create(force_ansi=False):
        if RICH_AVAILABLE and not force_ansi:
            return RichProgressUI()
        else:
            return ANSIProgressUI()

class RichProgressUI:
    def __init__(self):
        self.progress = None
        self.task_ids = {}

    def start_scan(self, drive_path):
        if not self.progress:
            self.progress = Progress()
            self.progress.__enter__()
        task_id = self.progress.add_task(f"[cyan]Scanning {drive_path}...", total=None)
        self.task_ids['scan'] = task_id

    def on_folder_done(self, folder_path, file_count):
        # Update scan task with green tick
        task_id = self.task_ids['scan']
        self.progress.update(task_id, description=f"[green]✓[/green] {file_count} files")

    def close(self):
        if self.progress:
            self.progress.__exit__(None, None, None)

class ANSIProgressUI:
    """Plain ANSI fallback (no colors or progress bars)."""
    def start_scan(self, drive_path):
        print(f"→ Scanning {drive_path}...")

    def on_folder_done(self, folder_path, file_count):
        print(f"✓ {file_count} files")

    def close(self):
        pass
```

### Pattern 3: Rich Progress with Custom Columns

**What:** Rich's Progress class accepts a list of columns to display (percentage, speed, ETA, etc.).

**When to use:** Building professional progress bars with computed metrics (MB/s, ETA, etc.).

**Example:**
```python
# Source: https://rich.readthedocs.io/en/stable/progress.html
from rich.progress import (
    Progress,
    BarColumn,
    DownloadColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
    TextColumn,
    PercentageColumn,
)

progress = Progress(
    TextColumn("[bold blue]{task.description}", justify="right"),
    BarColumn(bar_width=30),
    PercentageColumn(),
    DownloadColumn(),
    TransferSpeedColumn(),
    TimeRemainingColumn(),
)

with progress:
    task_id = progress.add_task("[cyan]Hashing files...", total=file_count)
    for i, file in enumerate(files):
        hash_file(file)
        progress.update(task_id, advance=1)
```

### Anti-Patterns to Avoid

- **Printing inside loops:** Each `print()` causes terminal redraws. Use callbacks instead.
- **Rich hard dependency:** Breaks on systems without pip. Always make optional.
- **Hardcoding colors:** Use Rich or ANSI constants, not magic strings.
- **Testing UI code directly:** Test callback logic in business logic; mock UI in unit tests.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Progress bar rendering | Custom cursor movement, percentage math | Rich Progress + columns | Math is complex (speed estimation, ETA calculation, rate limiting); Rich handles all edge cases |
| ANSI color codes | Magic strings like `"\033[36m"` | ANSI module (or Rich) | Easy to misremember codes; errors are silent (just wrong colors); centralize in constants |
| Windows color support | Windows API calls via `ctypes` | Rich (handles Windows natively) | Windows 10+ supports ANSI; Rich detects capabilities automatically |
| Spinner animation | Manual character rotation | Rich SpinnerColumn | Timing is complex; Rich provides built-in spinners |
| Progress bar math | Manual ETA/speed calculation | Rich's `task.finished_time` + built-in metrics | Off-by-one errors common; Rich handles time precision |

**Key insight:** Terminal rendering looks simple but has many gotchas: cursor positioning, line wrapping, terminal width, color support detection, Windows compatibility. Use proven libraries.

---

## Common Pitfalls

### Pitfall 1: Color Codes as Magic Strings
**What goes wrong:** `print("\033[36m" + text)` becomes unmaintainable; colors are inconsistent.
**Why it happens:** No single source of truth for ANSI codes.
**How to avoid:** Define constants in `ansi_codes.py`: `CYAN = "\033[36m"`, `GREEN = "\033[32m"`, etc. Reference by name.
**Warning signs:** Different colors in different parts of code; typos in escape codes.

### Pitfall 2: Blocking Progress on Hash Speed
**What goes wrong:** Hashing is slow; if progress only updates after entire file, bar appears frozen.
**Why it happens:** Hash operations can take seconds for large files.
**How to avoid:** Report progress DURING hashing (e.g., every 10MB), not just on completion. This requires callback from hasher's file loop.
**Warning signs:** Progress bar frozen for 30+ seconds; user thinks tool crashed.

### Pitfall 3: Windows Console Assumptions
**What goes wrong:** ANSI codes silently fail on old Windows versions; output looks garbled.
**Why it happens:** Pre-Windows 10 cmd.exe ignores ANSI escape codes.
**How to avoid:** Detect platform and Windows version. Windows 10+ (build 1511+) supports ANSI. Windows Terminal always works. Fallback to plain text if unsure.
**Warning signs:** Reports of "weird characters" on Windows; colors missing.

### Pitfall 4: TTY Detection Misuse
**What goes wrong:** Disabling colors when piped to file, breaking log parsing. Or assuming colors work in Docker.
**Why it happens:** `sys.stdout.isatty()` returns False when piped, but some users WANT colors in logs.
**How to avoid:** Check `NO_COLOR` env var first (user override). Then check TTY. Allow `--force-color` flag.
**Warning signs:** Users piping output to file and losing color information they need.

### Pitfall 5: Callback Bloat
**What goes wrong:** Too many callbacks; business logic becomes hard to follow. Or callbacks are ignored because they're optional.
**Why it happens:** Trying to report every tiny event (per-byte hashing progress).
**How to avoid:** Define minimal callback set: `on_folder_done`, `on_file_hashed`, `on_scan_complete`. Report batch updates, not per-item.
**Warning signs:** More than 3-4 callback parameters; scanner code is tangled with progress logic.

---

## Code Examples

### Example 1: ANSI Fallback Module

```python
# Source: Standard Python ANSI escape code patterns
# ansi_codes.py

# ANSI color codes (standard 16 colors)
CYAN = "\033[36m"
GREEN = "\033[32m"
RED = "\033[31m"
RESET = "\033[0m"
BOLD = "\033[1m"

# Symbols
ARROW = "→"
TICK = "✓"
CROSS = "✗"

def colored(text, color):
    """Apply ANSI color to text."""
    return f"{color}{text}{RESET}"

def progress_line(current, total, width=40):
    """Build a simple ANSI progress line."""
    pct = int((current / total) * 100)
    filled = int(width * current / total)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {pct}%"

# Example usage:
# print(colored("Processing...", CYAN))
# print(progress_line(50, 100))
```

### Example 2: Rich Progress Wrapper

```python
# Source: https://rich.readthedocs.io/en/stable/progress.html
# ui.py (RichProgressUI class)

from rich.progress import Progress, BarColumn, TransferSpeedColumn
from rich.text import Text

class RichProgressUI:
    """Professional progress UI using Rich."""

    def __init__(self):
        self.progress = Progress()
        self.running = False
        self.task_ids = {}

    def start(self):
        self.progress.__enter__()
        self.running = True

    def add_task(self, description, total=None):
        """Add a task and return task_id."""
        task_id = self.progress.add_task(description, total=total)
        return task_id

    def update(self, task_id, **kwargs):
        """Update task progress."""
        if self.running:
            self.progress.update(task_id, **kwargs)

    def stop(self):
        if self.running:
            self.progress.__exit__(None, None, None)
            self.running = False

# Usage:
# ui = RichProgressUI()
# ui.start()
# task = ui.add_task("[cyan]Scanning...", total=None)
# ui.update(task, description="[green]✓ Done!")
# ui.stop()
```

### Example 3: Callback Integration in Scanner

```python
# Source: Callback pattern integration
# scanner.py (existing method, enhanced)

def scan(self, dry_run=False, limit=None, on_folder_done=None):
    """
    Walk filesystem and collect file metadata.

    Args:
        on_folder_done: Optional callback(folder_path, file_count)
                       Called when a folder's files are collected.
    """
    result = ScanResult(drive_path=self.root_path)
    files_collected = 0

    for root, dirs, filenames in os.walk(self.root_path):
        dirs[:] = [d for d in dirs if not self._is_noise(d)]

        folder_files = 0
        for filename in filenames:
            # ... existing file processing ...
            if file_size >= self.min_size_bytes:
                result.files.append(record)
                folder_files += 1
                files_collected += 1

            if limit and files_collected >= limit:
                break

        # Report completion of this folder
        if on_folder_done and folder_files > 0:
            on_folder_done(root, folder_files)

        if limit and files_collected >= limit:
            break

    return result
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Raw `print()` statements | Progress bars with real-time updates | 2015+ | Better UX; clear visual feedback |
| Mandatory `colorama` | Optional Rich with ANSI fallback | 2020+ | Faster startup; no forced dependencies |
| Hard-coded ANSI codes | Rich abstractions (Progress, colors) | 2019+ (Rich 1.0) | Fewer bugs; easier maintenance |
| Single monolithic UI | Callback-based architecture | 2020+ | Decoupled; testable; flexible |
| Windows 7/8 support | Windows 10+ ANSI support | 2016 (Windows update) | Simplified code; consistent experience |

**Deprecated/outdated:**
- **Custom progress bar rendering:** Don't build spinner/percentage math. Too many edge cases.
- **Colorama hard dependency:** Pre-Windows 10 is EOL. Rich handles Windows natively now.
- **Blocking hash operations:** Modern UI expects fast feedback. Use chunked processing with callbacks.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | unittest (stdlib) |
| Config file | None — see Wave 0 |
| Quick run command | `python3 -m pytest tests/test_ui.py -x` (or unittest discover) |
| Full suite command | `python3 -m pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UI-01 | Per-folder progress shows cyan arrow, green tick | unit | `pytest tests/test_ui.py::TestRichUI::test_folder_done -x` | ❌ Wave 0 |
| UI-02 | Hash progress bar shows %, files, speed, ETA | unit | `pytest tests/test_ui.py::TestRichUI::test_hash_progress -x` | ❌ Wave 0 |
| UI-03 | Graceful fallback when rich not installed | unit | `pytest tests/test_ui.py::TestANSIUI::test_ansi_fallback -x` | ❌ Wave 0 |
| UI-04 | Windows Terminal output renders correctly | manual | Interactive test on Windows Terminal | ✅ Manual |
| UI-05 | Summary banner displays all stats | unit | `pytest tests/test_ui.py::TestUI::test_summary_banner -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/test_ui.py -x` (fast unit tests only)
- **Per wave merge:** Full suite `python3 -m pytest tests/ -x` (includes integration)
- **Phase gate:** Full suite green + manual Windows Terminal test before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_ui.py` — Unit tests for RichProgressUI and ANSIProgressUI classes
- [ ] `tests/test_integration_ui.py` — Integration tests: callback flow through scanner → hasher → cli → UI
- [ ] `diskcomp/ui.py` — Base UIHandler, RichProgressUI, ANSIProgressUI classes
- [ ] `diskcomp/ansi_codes.py` — ANSI constants and helper functions
- [ ] Framework detection: `import rich` try/except in cli.py

---

## Open Questions

1. **How should the scanner/hasher report per-file progress during hashing?**
   - **What we know:** FileHasher reads files in chunks (8KB default). Rich can update per-chunk.
   - **What's unclear:** Should callback fire on every chunk, or batch updates every 10 files?
   - **Recommendation:** Batch to 10 files to avoid excessive terminal redraws. Implement in `hash_files()` method.

2. **Should UI code be in a separate module or embedded in cli.py?**
   - **What we know:** Phase 5 requires single-file distribution (diskcomp.py).
   - **What's unclear:** How to keep ui.py modular but mergeable into single file?
   - **Recommendation:** Build ui.py as separate module now. Phase 5 will concatenate files when packaging.

3. **Should we detect terminal width to size progress bars?**
   - **What we know:** Rich.Progress auto-detects terminal width. ANSI version would need os.get_terminal_size().
   - **What's unclear:** Acceptable fallback if terminal width detection fails (e.g., piped output)?
   - **Recommendation:** Rich handles it. For ANSI, use width=80 as fallback.

---

## Windows Compatibility Details

### Windows Terminal
- **Support:** Full ANSI support (since 2019 release)
- **Colors:** 256-color + RGB
- **Status:** Recommended terminal for Windows 10+

### PowerShell (Core)
- **Support:** Full ANSI support in PowerShell 7.2+
- **Colors:** 256-color support
- **Status:** Recommended for modern Windows

### Windows Command Prompt (cmd.exe)
- **Support:** ANSI support since Windows 10 build 1511 (2016)
- **Colors:** Limited to 16 colors (no 256-color support)
- **Status:** Works but basic; Windows Terminal is recommended

### Windows 10/11
- **Build requirement:** 1511 or later (2016+)
- **Default terminal (Win 11 22H2+):** Windows Terminal
- **Fallback:** Rich auto-detects; ANSI code requires platform check

**Recommendation:** Use Rich when available (handles all Windows versions). Fallback ANSI is safe on Windows 10+.

---

## Sources

### Primary (HIGH confidence)
- [Rich 14.3.3 documentation](https://rich.readthedocs.io/en/stable/progress.html) — Progress class, custom columns, callbacks
- [Windows ANSI escape code support](https://learn.microsoft.com/en-us/powershell/module/Microsoft.PowerShell.Core/about/about_ansi_terminals?view=powershell-5.1) — Current Windows support (build 1511+)
- [Rich GitHub](https://github.com/Textualize/rich) — Version 14.3.3 released 2026-02-19

### Secondary (MEDIUM confidence)
- [Real Python: Python Rich Package](https://realpython.com/python-rich-package/) — Best practices for Progress integration
- [ANSI escape codes guide](https://www.lihaoyi.com/post/BuildyourownCommandLinewithANSIescapecodes.html) — ANSI code reference for fallback
- [Python TTY detection](https://eklitzke.org/ansi-color-codes) — isatty() and capability detection

### Tertiary (Reference)
- [tqdm library](https://github.com/tqdm/tqdm) — Alternative progress library (not recommended for this use case)
- [Colorama](https://pypi.org/project/colorama/) — Windows color support (Rich supersedes)

---

## Metadata

**Confidence breakdown:**
- **Standard stack:** HIGH — Rich is industry standard; ANSI is baseline supported
- **Architecture:** HIGH — Callback pattern is well-established; Rich API is stable
- **Pitfalls:** MEDIUM-HIGH — Windows compatibility verified but requires testing on actual Windows 10+ terminals
- **UI integration:** MEDIUM — Depends on scanner/hasher callback implementation (not yet coded)

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (Rich updates infrequently; ANSI standard is stable)

**Next step:** Implement ui.py with RichProgressUI and ANSIProgressUI classes; integrate callbacks into scanner.py and hasher.py.
