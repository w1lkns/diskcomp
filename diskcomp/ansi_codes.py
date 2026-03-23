"""
ANSI escape code constants and helper functions for terminal UI.

This module provides ANSI color constants and utility functions for rendering
colored text and progress indicators in terminal applications. It serves as
the foundation for the UIHandler and both RichProgressUI and ANSIProgressUI classes.

ANSI codes are supported on:
- macOS: Terminal, iTerm2, etc. (native support)
- Linux: gnome-terminal, xterm, etc. (native support)
- Windows: Windows Terminal, PowerShell (Windows 10+), cmd.exe (Windows 10+ with VT100 enabled)

This module uses no external dependencies and provides graceful fallback rendering
for environments where Rich is not installed.
"""


# Standard 16-color ANSI codes
CYAN = "\033[36m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
RESET = "\033[0m"
BOLD = "\033[1m"

# Unicode symbols for progress indicators
ARROW = "→"
TICK = "✓"
CROSS = "✗"


def colored(text: str, color: str) -> str:
    """
    Wrap text with ANSI color code and reset.

    Args:
        text: The text to colorize
        color: ANSI color constant (e.g., CYAN, GREEN, RED)

    Returns:
        Text wrapped with color code prefix and RESET suffix

    Example:
        >>> colored("Scanning...", CYAN)
        '\033[36mScanning...\033[0m'
    """
    return f"{color}{text}{RESET}"


def progress_bar(current: int, total: int, width: int = 40) -> str:
    """
    Render a simple ANSI progress bar with percentage.

    Args:
        current: Current progress count
        total: Total count
        width: Width of the bar in characters (default 40)

    Returns:
        A string like "[████████░░░░░░░░░░░░░░░░░░░░░░░░] 50%"

    Example:
        >>> progress_bar(50, 100)
        '[████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 50%'
    """
    if total <= 0:
        filled_width = 0
    else:
        filled_width = int((current / total) * width)

    filled = "█" * filled_width
    empty = "░" * (width - filled_width)
    percentage = int((current / total) * 100) if total > 0 else 0

    return f"[{filled}{empty}] {percentage}%"


def format_speed(bytes_per_sec: float) -> str:
    """
    Convert speed in bytes/sec to human-readable format.

    Args:
        bytes_per_sec: Speed in bytes per second

    Returns:
        Formatted string like "1.0 MB/s" or "512.0 KB/s"

    Example:
        >>> format_speed(1048576)
        '1.0 MB/s'
        >>> format_speed(10240)
        '10.0 KB/s'
    """
    if bytes_per_sec >= 1073741824:  # GB/s threshold (1GB)
        return f"{bytes_per_sec / 1073741824:.1f} GB/s"
    elif bytes_per_sec >= 1048576:  # MB/s threshold (1MB)
        return f"{bytes_per_sec / 1048576:.1f} MB/s"
    else:  # KB/s
        return f"{bytes_per_sec / 1024:.1f} KB/s"


def format_eta(seconds: float) -> str:
    """
    Convert remaining seconds to human-readable format.

    Args:
        seconds: Remaining time in seconds

    Returns:
        Formatted string like "2m 5s" or "1h 30m" or "45s"

    Example:
        >>> format_eta(125)
        '2m 5s'
        >>> format_eta(30)
        '30s'
    """
    seconds = int(seconds)

    if seconds < 60:
        return f"{seconds}s"

    minutes = seconds // 60
    remaining_secs = seconds % 60

    if minutes < 60:
        return f"{minutes}m {remaining_secs}s"

    hours = minutes // 60
    remaining_mins = minutes % 60

    return f"{hours}h {remaining_mins}m"
