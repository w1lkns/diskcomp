"""
Terminal UI classes for progress display and reporting.

This module provides two UI implementations: RichProgressUI (uses Rich library
when available for professional progress bars) and ANSIProgressUI (plain ANSI
fallback for environments without Rich installed).

Both classes implement the same interface, allowing them to be used interchangeably
via the UIHandler factory. This architecture decouples UI presentation from business
logic (scanner and hasher modules can accept UI callbacks without knowing whether
Rich is available).
"""

from typing import Union, Optional
from diskcomp.ansi_codes import CYAN, GREEN, RED, YELLOW, RESET, BOLD, ARROW, TICK, CROSS, colored, progress_bar, format_speed, format_eta

# Graceful Rich import with fallback
try:
    from rich.progress import Progress, BarColumn, TransferSpeedColumn, TimeRemainingColumn, PercentageColumn, TextColumn
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class UIHandler:
    """
    Factory class for creating appropriate UI instances.

    Detects Rich availability and returns either RichProgressUI or ANSIProgressUI.
    """

    _current_ui = None

    @staticmethod
    def create(force_ansi: bool = False) -> Union["RichProgressUI", "ANSIProgressUI"]:
        """
        Create and return appropriate UI instance.

        Args:
            force_ansi: If True, always use ANSIProgressUI even if Rich is available

        Returns:
            RichProgressUI if Rich available and not force_ansi, else ANSIProgressUI
        """
        if force_ansi or not RICH_AVAILABLE:
            UIHandler._current_ui = ANSIProgressUI()
        else:
            UIHandler._current_ui = RichProgressUI()
        return UIHandler._current_ui

    @staticmethod
    def get_available() -> str:
        """
        Get the name of the currently available UI backend.

        Returns:
            "rich" if Rich is available, "ansi" otherwise
        """
        return "rich" if RICH_AVAILABLE else "ansi"


class RichProgressUI:
    """
    Terminal UI using Rich library for professional progress bars and colors.

    Used when Rich is available. Provides progress bars with live updates,
    color support, and formatted output using Rich's Panel and Table widgets.
    """

    def __init__(self):
        """Initialize RichProgressUI with Progress context."""
        self.progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            PercentageColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
        )
        self.progress_context = None
        self.scan_task_id = None
        self.hash_task_id = None
        self.console = Console()

    def start_scan(self, drive_path: str):
        """
        Start scanning display.

        Args:
            drive_path: Path to the drive being scanned
        """
        if not self.progress_context:
            self.progress_context = self.progress.__enter__()

        self._scan_total_files = 0
        self.scan_task_id = self.progress_context.add_task(
            f"[cyan]→ Scanning {drive_path}...",
            total=None
        )

    def on_folder_done(self, folder_path: str, file_count: int):
        """
        Update progress when a folder is done scanning.

        Args:
            folder_path: Path to the completed folder
            file_count: Number of files found in this folder
        """
        if self.progress_context and self.scan_task_id is not None:
            self._scan_total_files = getattr(self, '_scan_total_files', 0) + file_count
            self.progress_context.update(
                self.scan_task_id,
                description=f"[cyan]→[/cyan] Scanning... {self._scan_total_files:,} files | [dim]{folder_path}[/dim]"
            )

    def start_hash(self, total_files: int):
        """
        Start hash progress display.

        Args:
            total_files: Total number of files to hash (actually candidates from size filter)
        """
        if not self.progress_context:
            self.progress_context = self.progress.__enter__()

        self.hash_task_id = self.progress_context.add_task(
            f"[cyan]Hashing 0 / {total_files} candidates",
            total=total_files
        )

    def on_file_hashed(self, current: int, total: int, speed_mbps: float, eta_secs: Optional[int] = None):
        """
        Update hash progress after hashing a file.

        Args:
            current: Number of files hashed so far
            total: Total number of files to hash
            speed_mbps: Current hashing speed in MB/s
            eta_secs: Estimated seconds remaining
        """
        if self.progress_context and self.hash_task_id is not None:
            # Rich's TransferSpeedColumn handles speed display automatically
            # Update current progress
            self.progress_context.update(
                self.hash_task_id,
                completed=current
            )

    def show_summary(self, duplicates_mb: float, duplicates_count: int,
                     unique_keep_mb: float, unique_keep_count: int,
                     unique_other_mb: float, unique_other_count: int,
                     report_path: str):
        """
        Display summary statistics in a formatted table.

        Args:
            duplicates_mb: Size of duplicate files in MB
            duplicates_count: Count of duplicate files
            unique_keep_mb: Size of unique files on keep drive in MB
            unique_keep_count: Count of unique files on keep drive
            unique_other_mb: Size of unique files on other drive in MB
            unique_other_count: Count of unique files on other drive
            report_path: Path to the generated report file
        """
        if not self.console:
            self.console = Console()

        table = Table(title="Disk Comparison Summary")
        table.add_column("Category", style="cyan")
        table.add_column("Count", style="magenta")
        table.add_column("Size (MB)", style="green")

        table.add_row("Duplicates", str(duplicates_count), f"{duplicates_mb:.2f}")
        table.add_row("Unique (Keep)", str(unique_keep_count), f"{unique_keep_mb:.2f}")
        table.add_row("Unique (Other)", str(unique_other_count), f"{unique_other_mb:.2f}")

        self.console.print(table)
        self.console.print(f"\n[bold]Report saved to:[/bold] {report_path}")

    def start_deletion(self, total_files: int):
        """
        Start deletion progress display.

        Args:
            total_files: Total number of files to delete
        """
        if not self.progress_context:
            self.progress_context = self.progress.__enter__()

        self.deletion_task_id = self.progress_context.add_task(
            "[cyan]Deleting files...",
            total=total_files
        )

    def on_file_deleted(self, current: int, total: int, space_freed_mb: float):
        """
        Update deletion progress after deleting a file.

        Args:
            current: Number of files deleted so far
            total: Total number of files to delete
            space_freed_mb: Cumulative space freed in MB
        """
        if self.progress_context and hasattr(self, 'deletion_task_id') and self.deletion_task_id is not None:
            self.progress_context.update(
                self.deletion_task_id,
                completed=current,
                description=f"[cyan]Deleting files... ({space_freed_mb:.2f} MB freed)"
            )

    def section(self, title: str):
        """Print a styled section header."""
        self.console.rule(f"[bold cyan]{title}[/bold cyan]")

    def drive_header(self, label: str, path: str):
        """Print a drive sub-header with path."""
        self.console.print(f"\n  [bold]{label}[/bold]  [dim cyan]{path}[/dim cyan]")

    def kv(self, key: str, value: str, status: str = 'normal'):
        """Print an indented key-value line with optional status coloring."""
        if status == 'ok':
            val_str = f"[green]{value}[/green]"
        elif status == 'warn':
            val_str = f"[yellow]{value}[/yellow]"
        elif status == 'error':
            val_str = f"[red]{value}[/red]"
        else:
            val_str = value
        self.console.print(f"    [bold]{key:<12}[/bold]  {val_str}")

    def warn(self, msg: str):
        """Print an indented warning line."""
        self.console.print(f"    [yellow]![/yellow]  {msg}")

    def error(self, msg: str):
        """Print an indented error line."""
        self.console.print(f"    [red]✗[/red]  {msg}")

    def ok(self, msg: str):
        """Print a success/info line."""
        self.console.print(f"  [green]✓[/green]  {msg}")

    def blank(self):
        """Print a blank line."""
        self.console.print()

    def close(self):
        """Close the progress context."""
        if self.progress_context:
            self.progress_context.__exit__(None, None, None)
            self.progress_context = None


class ANSIProgressUI:
    """
    Terminal UI using plain ANSI codes for maximum compatibility.

    Used when Rich is not available or explicitly requested. Provides progress
    bars, colors, and formatted output using ANSI escape codes and box-drawing
    characters. Works on all platforms including Windows cmd.exe (10+).
    """

    def __init__(self):
        """Initialize ANSIProgressUI with no context needed."""
        pass

    def start_scan(self, drive_path: str):
        """
        Start scanning display.

        Args:
            drive_path: Path to the drive being scanned
        """
        import sys as _sys
        self._scan_total_files = 0
        if _sys.stdout.isatty():
            print(f"\r  {colored(ARROW, CYAN)} Scanning {drive_path}...".ljust(78), end='', flush=True)
        else:
            print(f"{colored(ARROW, CYAN)} Scanning {drive_path}...")

    def on_folder_done(self, folder_path: str, file_count: int):
        """
        Update progress when a folder is done scanning.

        Args:
            folder_path: Path to the completed folder
            file_count: Number of files found in this folder
        """
        import sys as _sys
        self._scan_total_files = getattr(self, '_scan_total_files', 0) + file_count
        if _sys.stdout.isatty():
            # Truncate long folder paths to keep line within terminal width
            short_path = folder_path if len(folder_path) <= 50 else "…" + folder_path[-49:]
            line = f"  {colored(ARROW, CYAN)} Scanning... {self._scan_total_files:,} files | {short_path}"
            print(f"\r{line.ljust(78)}", end='', flush=True)
        else:
            print(f"{colored(TICK, GREEN)} {file_count} files from {folder_path}")

    def start_hash(self, total_files: int):
        """
        Start hash progress display.

        Args:
            total_files: Total number of files to hash (actually candidates from size filter)
        """
        import sys as _sys
        if _sys.stdout.isatty():
            print()  # end the in-place scan line
        print(f"{colored(ARROW, CYAN)} Hashing {total_files} candidates...")

    def on_file_hashed(self, current: int, total: int, speed_mbps: float, eta_secs: Optional[int] = None):
        """
        Update hash progress after hashing a file.

        Args:
            current: Number of files hashed so far (from candidates)
            total: Total number of files to hash (candidates from size filter)
            speed_mbps: Current hashing speed in MB/s
            eta_secs: Estimated seconds remaining
        """
        import sys as _sys
        bar = progress_bar(current, total)
        speed_str = format_speed(speed_mbps * 1048576)  # Convert MB/s to bytes/s

        output = f"{bar}  Hashing {current} / {total} candidates  {speed_str}"

        if eta_secs is not None and eta_secs > 0:
            output += f"  ETA {format_eta(eta_secs)}"

        if _sys.stdout.isatty():
            print(f"\r  {output.ljust(76)}", end='', flush=True)
            if current >= total:
                print()  # end the progress line
        else:
            print(output)

    def show_summary(self, duplicates_mb: float, duplicates_count: int,
                     unique_keep_mb: float, unique_keep_count: int,
                     unique_other_mb: float, unique_other_count: int,
                     report_path: str):
        """
        Display summary statistics using ANSI box-drawing characters.

        Args:
            duplicates_mb: Size of duplicate files in MB
            duplicates_count: Count of duplicate files
            unique_keep_mb: Size of unique files on keep drive in MB
            unique_keep_count: Count of unique files on keep drive
            unique_other_mb: Size of unique files on other drive in MB
            unique_other_count: Count of unique files on other drive
            report_path: Path to the generated report file
        """
        # Box drawing characters
        top_left = "╔"
        top_right = "╗"
        bottom_left = "╚"
        bottom_right = "╝"
        horizontal = "═"
        vertical = "║"
        mid_left = "╞"
        mid_right = "╡"

        width = 70
        inner_width = width - 2

        # Title
        title = " Disk Comparison Summary "
        title_padding = (inner_width - len(title)) // 2
        title_line = f"{vertical}{' ' * title_padding}{title}{' ' * (inner_width - title_padding - len(title))}{vertical}"

        # Data rows
        rows = [
            ("Duplicates", str(duplicates_count), f"{duplicates_mb:.2f}"),
            ("Unique (Keep)", str(unique_keep_count), f"{unique_keep_mb:.2f}"),
            ("Unique (Other)", str(unique_other_count), f"{unique_other_mb:.2f}"),
        ]

        # Build box
        lines = []
        lines.append(top_left + horizontal * inner_width + top_right)
        lines.append(title_line)
        lines.append(mid_left + horizontal * inner_width + mid_right)

        for category, count, size_mb in rows:
            row_text = f"{category:<20} | Count: {count:>10} | Size: {size_mb:>10} MB"
            row_line = f"{vertical}{row_text:<{inner_width}}{vertical}"
            lines.append(row_line)

        lines.append(bottom_left + horizontal * inner_width + bottom_right)
        lines.append(f"\nReport saved to: {report_path}")

        print("\n".join(lines))

    def start_deletion(self, total_files: int):
        """
        Start deletion progress display.

        Args:
            total_files: Total number of files to delete
        """
        print(f"{colored(ARROW, CYAN)} Deleting {total_files} files...")

    def on_file_deleted(self, current: int, total: int, space_freed_mb: float):
        """
        Update deletion progress after deleting a file.

        Args:
            current: Number of files deleted so far
            total: Total number of files to delete
            space_freed_mb: Cumulative space freed in MB
        """
        bar = progress_bar(current, total)
        output = f"{bar} | {current}/{total} files | {space_freed_mb:.2f} MB freed"
        print(output)

    def section(self, title: str):
        """Print a styled section header."""
        pad = "─" * max(0, 52 - len(title))
        print(f"\n{BOLD}{CYAN}── {title} {pad}{RESET}")

    def drive_header(self, label: str, path: str):
        """Print a drive sub-header with path."""
        print(f"\n  {BOLD}{label}{RESET}  {CYAN}{path}{RESET}")

    def kv(self, key: str, value: str, status: str = 'normal'):
        """Print an indented key-value line with optional status coloring."""
        if status == 'ok':
            val = f"{GREEN}{value}{RESET}"
        elif status == 'warn':
            val = f"{YELLOW}{value}{RESET}"
        elif status == 'error':
            val = f"{RED}{value}{RESET}"
        else:
            val = value
        print(f"    {key:<12}  {val}")

    def warn(self, msg: str):
        """Print an indented warning line."""
        print(f"    {YELLOW}! {msg}{RESET}")

    def error(self, msg: str):
        """Print an indented error line."""
        print(f"    {RED}{CROSS} {msg}{RESET}")

    def ok(self, msg: str):
        """Print a success/info line."""
        print(f"  {GREEN}{TICK}{RESET}  {msg}")

    def blank(self):
        """Print a blank line."""
        print()

    def close(self):
        """No-op for ANSI UI (no context to clean up)."""
        pass
