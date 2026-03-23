"""
Command-line interface for diskcomp.

This module provides the argparse CLI and main orchestration logic that ties
together the scanner, hasher, and reporter modules into a complete workflow.
"""

import argparse
import glob
import json
import os
import sys
from datetime import datetime

from typing import List
from diskcomp.scanner import FileScanner, get_unique_parent_folders
from diskcomp.hasher import FileHasher
from diskcomp.reporter import DuplicateClassifier, ReportWriter, extract_duplicate_files
from diskcomp.ui import UIHandler
from diskcomp.types import ScanError, InvalidPathError, FileNotReadableError, NavigationContext, FileRecord
from diskcomp.drive_picker import interactive_drive_picker, interactive_single_drive_picker
from diskcomp.health import check_drive_health, get_fix_instructions
from diskcomp.benchmarker import benchmark_read_speed


def parse_size_value(value_str: str) -> int:
    """
    Parse human-readable size string to bytes.

    Accepts:
    - Plain integer: "1024" -> 1024 bytes
    - KB suffix (case-insensitive): "500KB" or "500kb" -> 512000 bytes
    - MB suffix: "10MB" or "10mb" -> 10485760 bytes
    - GB suffix: "1.5GB" or "1.5gb" -> 1610612736 bytes

    Returns:
        Integer byte count

    Raises:
        ValueError: If format is invalid or cannot parse
    """
    value_str = value_str.strip()

    # Try parsing as plain integer first
    try:
        return int(value_str)
    except ValueError:
        pass

    # Parse with suffix (check longest first to avoid ambiguity)
    multipliers = [
        ('gb', 1024 * 1024 * 1024),
        ('mb', 1024 * 1024),
        ('kb', 1024),
        ('b', 1),
    ]

    for suffix, multiplier in multipliers:
        if value_str.lower().endswith(suffix):
            try:
                num_part = value_str[:-len(suffix)].strip()
                num = float(num_part)
                return int(num * multiplier)
            except (ValueError, IndexError):
                raise ValueError(f"Invalid size format: {value_str}")

    # No valid format found
    raise ValueError(f"Invalid size format: {value_str}. Use format: 1024, 500KB, 10MB, 1.5GB")


def parse_selection_input(input_str: str, max_index: int) -> list:
    """
    Parse comma/space-separated indices and range notation into a sorted list of integers.

    Accepts multiple input formats for user convenience:
    - Comma-separated: "1,3,5" → [1, 3, 5]
    - Space-separated: "1 2 3" → [1, 2, 3]
    - Range notation: "1-3" → [1, 2, 3]
    - Mixed: "1,3-5" → [1, 3, 4, 5]

    All indices are validated to be in the range [1, max_index]. Returns a sorted list
    of unique integers.

    Args:
        input_str: User input string with indices and/or ranges
        max_index: Maximum valid index (inclusive, 1-based)

    Returns:
        Sorted list of unique integers

    Raises:
        ValueError: If input is empty, contains invalid indices, or malformed ranges

    Examples:
        parse_selection_input("1,3,5", max_index=10) → [1, 3, 5]
        parse_selection_input("1-3", max_index=10) → [1, 2, 3]
        parse_selection_input("1,3-5,10", max_index=10) → [1, 3, 4, 5, 10]
        parse_selection_input("", max_index=5) → ValueError: No valid selections made
        parse_selection_input("1,7", max_index=5) → ValueError: Index 7 out of range (1-5)
    """
    input_str = input_str.strip()
    if not input_str:
        raise ValueError("No valid selections made")

    result_set = set()

    # Split by both comma and space, handle mixed separators
    # First normalize: replace commas with spaces, then split on whitespace
    normalized = input_str.replace(',', ' ')
    tokens = normalized.split()

    for token in tokens:
        token = token.strip()
        if not token:
            continue

        # Check if this token is a range (contains '-')
        if '-' in token:
            parts = token.split('-')
            if len(parts) != 2:
                raise ValueError(f"Invalid range format: {token}")

            try:
                start = int(parts[0].strip())
                end = int(parts[1].strip())
            except ValueError:
                raise ValueError(f"Invalid range format: {token}")

            # Validate range bounds
            if start < 1 or start > max_index:
                raise ValueError(f"Index {start} out of range (1-{max_index})")
            if end < 1 or end > max_index:
                raise ValueError(f"Index {end} out of range (1-{max_index})")

            # Add all integers in the range (inclusive)
            for i in range(start, end + 1):
                result_set.add(i)
        else:
            # Single index
            try:
                index = int(token)
            except ValueError:
                raise ValueError(f"Invalid index: {token}")

            if index < 1 or index > max_index:
                raise ValueError(f"Index {index} out of range (1-{max_index})")

            result_set.add(index)

    if not result_set:
        raise ValueError("No valid selections made")

    return sorted(list(result_set))


def show_folder_selection(context: NavigationContext, ui) -> NavigationContext:
    """
    Display folder selection UI and prompt user to select folders to skip.

    After hashing completes and user sees the summary, they can navigate to option 1
    to select one or more folders to exclude before proceeding to deletion. Displays
    a numbered list of unique parent folders and accepts comma/space-separated or
    range notation input (e.g., 1,3,5 or 1-3).

    Args:
        context: NavigationContext with scan_results already populated
        ui: UIHandler instance for display and error messages

    Returns:
        Modified NavigationContext with selected_folders_skip populated as set of paths

    Behavior:
        - Extracts unique parent folders from context.scan_results
        - If 0 folders found: displays message and returns context unchanged
        - If 1+ folders found:
            - Displays numbered folder list
            - Loops until user makes valid selection or presses 'b' to go back
            - Validates input with parse_selection_input()
            - Stores selected folder paths in context.selected_folders_skip (as set)
            - Displays confirmation message
        - Handles errors gracefully: displays ui.error() and loops again

    Example:
        context = NavigationContext(scan_results={...})
        context = show_folder_selection(context, ui)
        # context.selected_folders_skip now contains ['/path/to/Photos', '/path/to/Videos']
    """
    # Extract unique parent folders from scan results
    if not context.scan_results or 'files_by_hash' not in context.scan_results:
        ui.ok("No scan results available")
        return context

    # Flatten all files from the classification dict
    all_files = []
    for files_list in context.scan_results.get('files_by_hash', {}).values():
        all_files.extend(files_list)

    folders = get_unique_parent_folders(all_files)

    # If no folders found, return early
    if not folders:
        ui.ok("No folders to skip")
        return context

    # Display the folder list
    ui.display_folder_list(folders)

    # Loop until user makes valid selection or presses 'b' to go back
    while True:
        # Build valid_keys list: all folder numbers plus 'b' for back
        valid_keys = [str(i) for i in range(1, len(folders) + 1)] + ['b']

        try:
            user_input = input(
                f"Enter folder numbers to skip (e.g., 1,3,5 or 1-3), or 'b' to go back: "
            ).strip()

            # Check for back key
            if user_input.lower() == 'b':
                return context

            # Parse the selection
            selected_indices = parse_selection_input(user_input, len(folders))

            # Convert indices (1-based) to folder paths
            selected_paths = set()
            for idx in selected_indices:
                # idx is 1-based, convert to 0-based for list indexing
                selected_paths.add(folders[idx - 1])

            # Store in context
            context.selected_folders_skip = selected_paths

            # Display confirmation
            if len(selected_paths) == 1:
                folder_list = list(selected_paths)[0]
            else:
                folder_list = ", ".join(sorted(selected_paths))
            ui.ok(f"Selected {len(selected_paths)} folder(s) to skip: {folder_list}")

            return context

        except ValueError as e:
            # Invalid input - display error and loop again
            ui.error(str(e))


def show_file_flagging(context: NavigationContext, ui) -> NavigationContext:
    """
    Display file flagging UI and prompt user to select files to protect.

    After hashing completes and user sees the summary, they can navigate to select
    individual files to flag (mark as "do not delete"). Displays a numbered list of
    all candidate files (from duplicates and unique files) with their sizes and accepts
    comma/space-separated or range notation input (e.g., 1,3,5 or 1-3).

    Args:
        context: NavigationContext with scan_results already populated
        ui: UIHandler instance for display and error messages

    Returns:
        Modified NavigationContext with flagged_files updated (set of absolute paths)

    Behavior:
        - Extracts all files from context.scan_results using extract_duplicate_files()
        - If 0 files found: displays message and returns context unchanged
        - If 1+ files found:
            - Displays numbered file list with sizes
            - Loops until user makes valid selection or presses 'b' to go back
            - Validates input with parse_selection_input()
            - Stores selected file paths in context.flagged_files (as set, union with existing)
            - Displays confirmation message
        - Handles errors gracefully: displays ui.error() and loops again

    Example:
        context = NavigationContext(scan_results={...})
        context = show_file_flagging(context, ui)
        # context.flagged_files now contains ['/path/to/file1.txt', '/path/to/file2.txt']
    """
    # Extract all files from scan results
    if not context.scan_results:
        ui.ok("No scan results available")
        return context

    # Get all file paths from the classification results
    file_paths = extract_duplicate_files(context.scan_results)

    # If no files found, return early
    if not file_paths:
        ui.ok("No files to flag")
        return context

    # Convert file paths to FileRecord objects for display
    # Note: We only have paths here, not full FileRecord objects
    # Create minimal FileRecord objects with path and placeholder size
    files_to_display = []
    for file_path in file_paths:
        # Try to get file size from disk if it exists
        file_size_bytes = 0
        try:
            if os.path.exists(file_path):
                file_size_bytes = os.path.getsize(file_path)
        except (OSError, IOError):
            file_size_bytes = 0

        file_record = FileRecord(
            path=file_path,
            rel_path=file_path,
            size_bytes=file_size_bytes
        )
        files_to_display.append(file_record)

    # Display the file list
    ui.display_file_list(files_to_display, context.flagged_files)

    # Loop until user makes valid selection or presses 'b' to go back
    while True:
        try:
            user_input = input(
                f"Enter file numbers to flag (e.g., 1,3,5 or 1-3), or 'b' to go back: "
            ).strip()

            # Check for back key
            if user_input.lower() == 'b':
                return context

            # Parse the selection
            selected_indices = parse_selection_input(user_input, len(files_to_display))

            # Convert indices (1-based) to file paths
            selected_paths = set()
            for idx in selected_indices:
                # idx is 1-based, convert to 0-based for list indexing
                selected_paths.add(files_to_display[idx - 1].path)

            # Union with existing flagged files (add to, don't replace)
            context.flagged_files = context.flagged_files.union(selected_paths)

            # Display confirmation
            if len(selected_paths) == 1:
                file_list = list(selected_paths)[0]
            else:
                file_list = ", ".join(sorted(selected_paths))
            ui.ok(f"Flagged {len(selected_paths)} file(s). These will be excluded from deletion.")

            return context

        except ValueError as e:
            # Invalid input - display error and loop again
            ui.error(str(e))


def prompt_confirm(message: str, valid_keys: list, ui) -> str:
    """
    Validate user input against a whitelist of valid keys.

    Displays a message and loops until the user enters a non-empty value that matches
    one of the valid_keys (case-sensitive). Invalid input triggers a re-prompt with
    an error message. Empty input also triggers a re-prompt.

    Args:
        message: Prompt message to display to user (e.g., "Delete this file? (y/n/skip): ")
        valid_keys: List of acceptable input values (e.g., ['y', 'n', 'skip'])
        ui: UIHandler instance for displaying error messages

    Returns:
        The validated user input (a single string from valid_keys)

    Example:
        choice = prompt_confirm("Delete this file? (y/n/skip): ", ['y', 'n', 'skip'], ui)
    """
    while True:
        user_input = input(message).strip()

        # Check for empty input
        if not user_input:
            ui.error(f"Invalid choice. Enter one of: {', '.join(valid_keys)}")
            continue

        # Check for valid key
        if user_input in valid_keys:
            return user_input

        # Invalid key
        ui.error(f"Invalid choice. Enter one of: {', '.join(valid_keys)}")


def show_deletion_preview(context: NavigationContext, ui) -> None:
    """
    Display a preview of which files will be deleted.

    Shows the candidate files that will be deleted, taking into account any flagged files
    and folder skips. This is a read-only display with no user input required.

    Args:
        context: NavigationContext with scan_results and selections
        ui: UIHandler instance for display
    """
    if not context.scan_results:
        ui.ok("No scan results available")
        return

    # For now, show a simple message
    ui.ok("Deletion preview: Preparing candidates (will show files to be deleted)")


def orchestrate_deletion(context: NavigationContext, ui, mode: str):
    """
    Wrapper around DeletionOrchestrator with pre-deletion filtering.

    Filters candidates by flagged files and folder skips before deletion.
    Routes to either interactive or batch mode based on mode parameter.

    Args:
        context: NavigationContext with scan_results, flagged_files, selected_folders_skip
        ui: UIHandler instance for display
        mode: 'interactive' or 'batch' for deletion mode

    Returns:
        DeletionResult from DeletionOrchestrator

    Raises:
        ValueError: If context.scan_results is None
    """
    from diskcomp.deletion import DeletionOrchestrator, filter_candidates_by_flags

    if context.scan_results is None:
        raise ValueError("No scan results available for deletion")

    # Filter candidates by flagged files
    filtered_results = filter_candidates_by_flags(context.scan_results, context.flagged_files)

    # TODO: Apply folder skip filtering when integrated

    # Create orchestrator and run deletion
    orchestrator = DeletionOrchestrator(
        candidates=filtered_results.get('duplicates', []),
        ui=ui,
        report_dir=os.path.dirname(context.report_path) if context.report_path else os.getcwd()
    )

    if mode == 'interactive':
        return orchestrator.interactive_mode()
    elif mode == 'batch':
        return orchestrator.batch_mode()
    else:
        raise ValueError(f"Invalid deletion mode: {mode}")


def run_post_scan_menu(context: NavigationContext, ui) -> str:
    """
    Main post-scan navigation hub for user actions after scanning and summary display.

    Displays a menu with 6 options and loops until user chooses deletion or exit.
    Supports navigation to folder skip, file flagging, and deletion workflows
    with state preservation across back navigation.

    Menu options:
      1) Skip certain folders (exclude before deletion)
      2) Flag individual files (mark 'do not delete')
      3) Review deletion preview
      4) Start deletion (Mode A: interactive, per-file confirmation)
      5) Start deletion (Mode B: batch, dry-run then confirm)
      6) Exit without deletion

    Args:
        context: NavigationContext with scan_results already populated
        ui: UIHandler instance for display and routing

    Returns:
        String outcome: 'deleted', 'aborted', or 'skipped_deletion'

    Note:
        - Never re-scans files (uses NavigationContext for state)
        - All selections (folder skip, file flags) preserved when navigating back
        - Returns immediately when user completes deletion or chooses to exit
    """
    while True:
        # Display menu
        ui.ok("\nNext Steps:")
        ui.ok("  1) Skip certain folders (exclude before deletion)")
        ui.ok("  2) Flag individual files (mark 'do not delete')")
        ui.ok("  3) Review deletion preview")
        ui.ok("  4) Start deletion (Mode A: interactive)")
        ui.ok("  5) Start deletion (Mode B: batch)")
        ui.ok("  6) Exit without deletion")

        # Get user choice
        choice = prompt_confirm("Enter your choice (1-6): ", ['1', '2', '3', '4', '5', '6'], ui)

        # Route based on choice
        if choice == '1':
            # Folder skip
            context = show_folder_selection(context, ui)
        elif choice == '2':
            # File flagging
            context = show_file_flagging(context, ui)
        elif choice == '3':
            # Deletion preview
            show_deletion_preview(context, ui)
        elif choice == '4':
            # Interactive deletion
            result = orchestrate_deletion(context, ui, mode='interactive')
            if result.aborted:
                return 'aborted'
            else:
                return 'deleted'
        elif choice == '5':
            # Batch deletion
            result = orchestrate_deletion(context, ui, mode='batch')
            if result.aborted:
                return 'aborted'
            else:
                return 'deleted'
        elif choice == '6':
            # Exit without deletion
            return 'skipped_deletion'


def parse_args(args=None):
    """
    Parse command-line arguments.

    Args:
        args: List of argument strings to parse (for testing). If None, uses sys.argv[1:].

    Returns:
        argparse.Namespace with parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Compare two drives and find duplicate files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 -m diskcomp --keep /Volumes/Keep --other /Volumes/Other
  python3 -m diskcomp --keep /mnt/drive1 --other /mnt/drive2 --dry-run
  python3 -m diskcomp --keep /path/A --other /path/B --limit 100
  python3 -m diskcomp --keep /path/A --other /path/B --format json
  python3 -m diskcomp --keep /path/A --other /path/B --output /tmp/report.csv
        """.strip()
    )

    parser.add_argument(
        '--keep',
        type=str,
        required=False,
        help='Path to the "keep" drive (files to retain). If omitted, uses interactive mode.'
    )

    parser.add_argument(
        '--other',
        type=str,
        required=False,
        help='Path to the "other" drive (compare against). If omitted, uses interactive mode.'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=False,
        help='Walk and count files without hashing (quick sanity check)'
    )

    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Hash only first N files per drive (for testing, default: no limit)'
    )

    parser.add_argument(
        '--min-size',
        type=str,
        default=None,
        help='Minimum file size to include (e.g. 1KB, 10MB, 1.5GB, or bytes; default: 1KB)'
    )

    parser.add_argument(
        '--single',
        type=str,
        default=None,
        help='Scan a single drive for internal duplicates (find redundant files on same drive)'
    )

    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Custom report path (default: ~/diskcomp-report-YYYYMMDD-HHMMSS.csv)'
    )

    parser.add_argument(
        '--format',
        type=str,
        choices=['csv', 'json'],
        default='csv',
        help='Report format (csv or json, default: csv)'
    )

    parser.add_argument(
        '--delete-from',
        type=str,
        default=None,
        help='Delete duplicates from an existing report CSV/JSON file'
    )

    parser.add_argument(
        '--undo',
        type=str,
        default=None,
        help='View audit log of deleted files (permanent; restore not possible)'
    )

    return parser.parse_args(args)


def display_health_checks(keep_path, other_path, ui):
    """
    Runs health checks on both drives and displays results to user.

    Args:
        keep_path: Path to keep drive
        other_path: Path to other drive
        ui: UIHandler instance for output

    Returns:
        True if checks pass (warnings are OK), False if critical error occurs
    """
    ui.section("Drive Health Checks")

    keep_health = check_drive_health(keep_path)
    _display_health_result(ui, "Keep Drive", keep_path, keep_health)

    if keep_health.benchmark_result and not keep_health.benchmark_result.success:
        retry = input(f"\n  Benchmark failed: {keep_health.benchmark_result.error}. Retry? (y/n): ").strip().lower()
        if retry in ['y', 'yes']:
            keep_health.benchmark_result = benchmark_read_speed(keep_path)
            if keep_health.benchmark_result.success:
                ui.kv("Speed", f"{keep_health.benchmark_result.speed_mbps:.1f} MB/s", 'ok')
            else:
                ui.warn("Benchmark failed again. Proceeding without speed check.")

    other_health = check_drive_health(other_path)
    _display_health_result(ui, "Other Drive", other_path, other_health)

    if other_health.benchmark_result and not other_health.benchmark_result.success:
        retry = input(f"\n  Benchmark failed: {other_health.benchmark_result.error}. Retry? (y/n): ").strip().lower()
        if retry in ['y', 'yes']:
            other_health.benchmark_result = benchmark_read_speed(other_path)
            if other_health.benchmark_result.success:
                ui.kv("Speed", f"{other_health.benchmark_result.speed_mbps:.1f} MB/s", 'ok')
            else:
                ui.warn("Benchmark failed again. Proceeding without speed check.")

    ui.blank()
    if keep_health.is_writable and other_health.is_writable:
        ui.ok("Both drives readable. Ready to scan.")
        return True

    if not keep_health.is_writable:
        ui.error("Keep drive is not writable. Cannot proceed.")
        return False

    ui.ok("Other drive is read-only — scan can proceed (read-only is OK).")
    return True


def _display_health_result(ui, label, path, health):
    """Helper to display health check results through the UI."""
    ui.drive_header(label, path)

    space_str = f"{health.used_gb} GB used / {health.total_gb} GB total ({health.free_gb} GB free)"
    ui.kv("Space", space_str)

    fstype = health.fstype if health.fstype and health.fstype != "UNKNOWN" else "Unknown"
    ui.kv("Filesystem", fstype, 'warn' if fstype == "Unknown" else 'normal')

    ui.kv("Writable", "Yes" if health.is_writable else "No — read-only",
          'ok' if health.is_writable else 'warn')

    # Add NTFS-on-macOS/Linux specific callout (D-19)
    if health.fstype == 'NTFS' and sys.platform in ['darwin', 'linux']:
        fix_text = get_fix_instructions(health.fstype, sys.platform, path)
        ui.warn(f"⚠ NTFS on {sys.platform}: This drive is read-only. Files cannot be deleted from it here.")
        if fix_text:
            ui.warn(f"To fix: {fix_text}")

    if health.benchmark_result:
        if health.benchmark_result.success:
            ui.kv("Speed", f"{health.benchmark_result.speed_mbps:.1f} MB/s")
        else:
            ui.kv("Speed", f"Failed: {health.benchmark_result.error}", 'warn')

    for warning in health.warnings:
        if "To fix:" in warning:
            fix_part = warning.split("To fix: ")[1] if "To fix: " in warning else warning
            ui.warn(f"Fix: {fix_part}")
        else:
            ui.warn(warning)

    for err in health.errors:
        ui.error(err)


def _check_deletion_readiness(candidates: list) -> tuple:
    """
    Check which candidate files are deletable (not read-only).

    Args:
        candidates: List of dicts from ReportReader

    Returns:
        (deletable_candidates, readonly_warnings) where deletable is filtered
        list of candidates on writable drives, readonly_warnings is list of
        paths that are read-only or on protected drives.
    """
    from diskcomp.health import check_drive_health, get_fix_instructions

    deletable = []
    readonly_warnings = []

    for candidate in candidates:
        other_path = candidate.get('duplicate_file') or candidate.get('other_path', '')
        try:
            # Check if the file's parent directory is writable
            parent_dir = os.path.dirname(os.path.abspath(other_path)) or os.sep

            # If parent doesn't exist (e.g. fake paths in tests), treat as writable
            if not os.path.exists(parent_dir) or os.access(parent_dir, os.W_OK):
                deletable.append(candidate)
            else:
                # Use health check for a richer error message (fstype, fix instructions)
                if sys.platform == 'win32':
                    drive_root = os.path.abspath(other_path)[:3]  # e.g. "C:\"
                else:
                    drive_root = parent_dir
                health = check_drive_health(drive_root)
                fix = get_fix_instructions(health.fstype, sys.platform, drive_root)
                msg = f"{other_path}: Drive is read-only."
                if fix:
                    msg += f" To fix: {fix}"
                readonly_warnings.append(msg)
        except Exception as e:
            # If health check fails, assume deletable (user can retry)
            deletable.append(candidate)

    return deletable, readonly_warnings


def _show_undo_log(log_file_path: str) -> int:
    """
    Display audit view of deleted files from undo log (D-14, D-15).

    Args:
        log_file_path: Path to undo log JSON file

    Returns:
        0 on success, 1 on error
    """
    try:
        if not os.path.isfile(log_file_path):
            print(f"Error: Undo log file not found: {log_file_path}", file=sys.stderr)
            return 1

        with open(log_file_path, 'r') as f:
            entries = json.load(f)

        if not entries:
            print("Undo log is empty.", file=sys.stderr)
            return 0

        # Display header
        print("\n=== Undo Log ===", file=sys.stderr)
        print(f"File: {log_file_path}\n", file=sys.stderr)

        # Display entries
        total_size_mb = 0.0
        for entry in entries:
            path = entry.get('path', 'UNKNOWN')
            size_mb = float(entry.get('size_mb', 0))
            hash_val = entry.get('hash', 'UNKNOWN')
            deleted_at = entry.get('deleted_at', 'UNKNOWN')

            total_size_mb += size_mb

            hash_short = hash_val[:16] + "..." if len(hash_val) > 16 else hash_val
            print(f"{path}", file=sys.stderr)
            print(f"  Size: {size_mb} MB | Hash: {hash_short} | Deleted: {deleted_at}", file=sys.stderr)

        # Summary
        print(f"\nSummary: {len(entries)} files deleted, {total_size_mb:.2f} MB freed", file=sys.stderr)
        print("\nThese files were permanently deleted. Restore is not possible.", file=sys.stderr)

        return 0

    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in undo log: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error reading undo log: {e}", file=sys.stderr)
        return 1


def find_recent_reports(max_results: int = 8) -> list:
    """
    Find recent diskcomp report files in the home directory and current directory.

    Searches for diskcomp-report-*.csv and diskcomp-report-*.json files,
    sorted by modification time (most recent first).

    Args:
        max_results: Maximum number of results to return

    Returns:
        List of dicts with 'path' and 'mtime' keys, sorted newest first
    """
    search_dirs = [os.path.expanduser('~'), os.getcwd()]
    seen = set()
    found = []

    for search_dir in search_dirs:
        for pattern in ['diskcomp-report-*.csv', 'diskcomp-report-*.json']:
            matches = glob.glob(os.path.join(search_dir, pattern))
            for path in matches:
                abs_path = os.path.abspath(path)
                if abs_path not in seen and os.path.isfile(abs_path):
                    seen.add(abs_path)
                    found.append({'path': abs_path, 'mtime': os.path.getmtime(abs_path)})

    found.sort(key=lambda x: x['mtime'], reverse=True)
    return found[:max_results]


def show_report_picker():
    """
    Show a numbered list of recent reports and let user pick one.

    Returns:
        Selected report path, or None if cancelled
    """
    reports = find_recent_reports()

    if not reports:
        print("\nNo previous diskcomp reports found in home directory or current directory.")
        print("Run a scan first to generate a report.\n")
        return None

    print("\nRecent reports:")
    for i, report in enumerate(reports, 1):
        mtime_str = datetime.fromtimestamp(report['mtime']).strftime('%Y-%m-%d %H:%M')
        filename = os.path.basename(report['path'])
        print(f"  {i}) {filename}  [{mtime_str}]")
    print(f"  {len(reports) + 1}) Back")
    print()

    while True:
        choice = input(f"Select (1-{len(reports) + 1}): ").strip()
        if choice.isdigit():
            n = int(choice)
            if 1 <= n <= len(reports):
                return reports[n - 1]['path']
            elif n == len(reports) + 1:
                return None
        print(f"Invalid choice. Please enter 1-{len(reports) + 1}.")


def show_first_run_menu():
    """
    Display first-run menu and return user's selection (D-07 through D-11).

    Menu options:
      1) Compare two drives — returns 'two_drives'
      2) Clean up a single drive — returns 'single_drive'
      3) Load previous report — returns 'load_report'
      4) Help — returns 'help'
      5) Quit — returns 'quit'

    Returns:
        One of: 'two_drives', 'single_drive', 'load_report', 'help', 'quit'
    """
    while True:
        menu_text = """
What would you like to do?
  1) Compare two drives
  2) Clean up a single drive
  3) Load previous report
  4) Help
  5) Quit
        """.strip()
        print(menu_text)
        print()

        choice = input("Select (1-5): ").strip()

        if choice in ['1', '2', '3', '4', '5']:
            mapping = {'1': 'two_drives', '2': 'single_drive', '3': 'load_report', '4': 'help', '5': 'quit'}
            return mapping[choice]
        else:
            print("Invalid choice. Please enter 1, 2, 3, 4, or 5.")
            print()


def show_help_guide():
    """
    Display quick help guide (D-10) with plain English explanation.
    """
    guide = """
About diskcomp:
  diskcomp finds duplicate files on your drives and helps you safely delete them
  to free up space. You provide two drives (or one), and diskcomp shows which files
  appear in both places.

Two modes:
  - Compare two drives: Scan two separate drives (e.g., your SSD and backup)
    and find duplicates between them. Delete from the "other" drive while keeping
    the copy on the "keep" drive.

  - Clean up a single drive: Scan one drive and find files that appear more than
    once on that same drive. Keep the first copy, delete the redundant ones.

Three safety facts:
  1) No file is deleted without your explicit confirmation — diskcomp never
     deletes automatically.
  2) Every deletion is recorded in an undo log. You can review what was deleted
     and (manually) restore files if needed.
  3) diskcomp works with read-only drives (backups) safely — you can't delete
     from a read-only drive even if you wanted to.

More info: Run diskcomp --help for detailed flag reference.
    """.strip()

    print()
    print(guide)
    print()


def show_startup_banner():
    """
    Display startup banner with logo, tagline, and version (D-04, D-05, D-06).

    Shown only in interactive (no-args) mode, not when flags are passed.
    Tagline: "Find duplicates. Free space. Stay safe."
    Version: read from importlib.metadata with fallback to "1.1.0"
    """
    try:
        from importlib.metadata import version
        ver = version('diskcomp')
    except Exception:
        ver = '1.1.0'  # Fallback for single-file builds or uninstalled

    banner = f"""

 ██████╗ ██╗███████╗██╗  ██╗ ██████╗ ██████╗ ███╗   ███╗██████╗
 ██╔══██╗██║██╔════╝██║ ██╔╝██╔════╝██╔═══██╗████╗ ████║██╔══██╗
 ██║  ██║██║███████╗█████╔╝ ██║     ██║   ██║██╔████╔██║██████╔╝
 ██║  ██║██║╚════██║██╔═██╗ ██║     ██║   ██║██║╚██╔╝██║██╔═══╝
 ██████╔╝██║███████║██║  ██╗╚██████╗╚██████╔╝██║ ╚═╝ ██║██║
 ╚═════╝ ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═╝     ╚═╝╚═╝

 Find duplicates. Free space. Stay safe.
 v{ver}

    """

    try:
        print(banner)
    except UnicodeEncodeError:
        # Fallback for terminals without Unicode support (e.g. Windows cp1252)
        print(f"\ndiskcomp v{ver} - Find duplicates. Free space. Stay safe.\n")


def show_plain_language_summary(summary_dict: dict, mode: str = 'two_drives',
                                keep_label: str = 'Keep', other_label: str = 'Other'):
    """
    Display plain-language results summary (D-16, D-17).

    Args:
        summary_dict: From DuplicateClassifier.classify()['summary']
        mode: 'two_drives' or 'single_drive'
        keep_label: Label for keep drive (e.g., 'MySSD')
        other_label: Label for other/single drive (e.g., 'Backup')
    """
    duplicate_count = summary_dict.get('duplicate_count', 0)
    duplicate_mb = summary_dict.get('duplicate_size_mb', 0)

    if duplicate_count == 0:
        if mode == 'two_drives':
            msg = "No duplicates found. Both drives are already clean."
        else:
            msg = "No duplicates found. This drive has no redundant files."
        print()
        print(msg)
        print()
        return

    # Format size: use GB if >= 1000 MB, otherwise MB
    if duplicate_mb >= 1000:
        size_str = f"{duplicate_mb / 1000:.1f} GB"
    else:
        size_str = f"{duplicate_mb:.1f} MB"

    # Choose label: use other_label for two-drive, "this drive" for single
    if mode == 'two_drives':
        drive_label = other_label
    else:
        drive_label = "this drive"

    msg = f"Found {duplicate_count} duplicates. You could free {size_str} from {drive_label}. Ready to review?"

    print()
    print(msg)
    print()


def show_next_steps(report_path: str):
    """
    Display next steps block with exact commands (D-18).

    Args:
        report_path: Path to the generated report file
    """
    # Generate undo log hint (default pattern ~/diskcomp-undo-YYYYMMDD.json)
    today = datetime.now().strftime('%Y%m%d')
    undo_hint = f"~/diskcomp-undo-{today}.json"

    print("-- Next steps " + "-" * 40)
    print(f"Review:  cat {report_path}")
    print(f"Delete:  diskcomp --delete-from {report_path}")
    print(f"Undo:    diskcomp --undo {undo_hint}")
    print("-" * 60)
    print()


def show_action_menu():
    """
    Display post-scan action menu (D-23).

    Menu options:
      1) Review and delete interactively (per-file confirmation)
      2) Batch delete (dry-run + type DELETE to confirm)
      3) Exit (report saved, no deletion)

    Returns:
        One of: 'interactive', 'batch', 'exit'
    """
    while True:
        menu_text = """
What next?
  1) Review and delete interactively
  2) Batch delete (preview + confirm)
  3) Exit (report saved)
        """.strip()
        print(menu_text)
        print()

        choice = input("Select (1-3): ").strip()

        if choice in ['1', '2', '3']:
            mapping = {'1': 'interactive', '2': 'batch', '3': 'exit'}
            return mapping[choice]
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")
            print()


def main(args=None):
    """
    Main orchestration function.

    Coordinates the full pipeline: validate paths → health checks → scan → hash → classify → report.

    Args:
        args: Parsed arguments (for testing). If None, parse from command line.

    Returns:
        0 on success, 1 on error
    """
    # Parse arguments
    if args is None:
        args = parse_args()

    # Validate --min-size flag if provided
    min_size_bytes = 1024  # Default 1KB
    if hasattr(args, 'min_size') and args.min_size:
        try:
            min_size_bytes = parse_size_value(args.min_size)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    # Detect interactive (no-args) mode: no --keep, --other, --delete-from, --undo, --single
    is_interactive_mode = (
        not args.keep
        and not args.other
        and not args.delete_from
        and not args.undo
        and not args.single
    )

    # Track menu selection for routing in interactive mode
    interactive_selection = None

    if is_interactive_mode:
        print("\033[2J\033[H", end='', flush=True)  # Clear screen
        show_startup_banner()

        # Display first-run menu and handle selection
        while True:
            selection = show_first_run_menu()

            if selection == 'quit':
                print("Goodbye!")
                return 0
            elif selection == 'help':
                show_help_guide()
                # Loop back to menu
                continue
            elif selection == 'load_report':
                report_path = show_report_picker()
                if report_path is None:
                    # Back to main menu
                    continue

                # Load candidates from selected report
                from diskcomp.reporter import ReportReader
                from diskcomp.deletion import DeletionOrchestrator

                try:
                    candidates = ReportReader.load(report_path)
                except Exception as e:
                    print(f"\nError reading report: {e}", file=sys.stderr)
                    continue

                if not candidates:
                    print("\nNo files marked for deletion in this report.")
                    print("The report may have already been acted on, or contains no duplicates.\n")
                    continue

                print(f"\nLoaded {len(candidates)} deletion candidates from:")
                print(f"  {report_path}\n")

                # Check for read-only drives
                deletable, readonly_warnings = _check_deletion_readiness(candidates)
                if readonly_warnings:
                    print("Some files are on read-only drives:")
                    for warning in readonly_warnings:
                        print(f"  - {warning}")
                    print(f"\nProceeding with {len(deletable)} deletable files.\n")
                    candidates = deletable

                if not candidates:
                    print("All files are on read-only drives. Cannot proceed.\n")
                    continue

                # Show action menu and run deletion workflow
                action = show_action_menu()
                if action == 'exit':
                    print("No files deleted.")
                    return 0

                ui = UIHandler.create()
                orchestrator = DeletionOrchestrator(candidates, ui, report_path)

                if action == 'interactive':
                    result = orchestrator.interactive_mode()
                else:
                    result = orchestrator.batch_mode()

                print(f"\nDeletion complete: {result.files_deleted} deleted, {result.space_freed_mb:.2f} MB freed", file=sys.stderr)
                if result.undo_log_path:
                    print(f"Undo log: {result.undo_log_path}", file=sys.stderr)
                if result.errors:
                    for error in result.errors:
                        print(f"Error: {error}", file=sys.stderr)

                ui.close()
                return 0

            elif selection == 'two_drives':
                # Proceed with two-drive flow
                interactive_selection = 'two_drives'
                break
            elif selection == 'single_drive':
                # Proceed with single-drive flow
                interactive_selection = 'single_drive'
                break


    # Handle --undo flag (audit view only, no restoration)
    if args.undo:
        return _show_undo_log(args.undo)

    # Handle --delete-from flag (deletion workflow)
    if args.delete_from:
        try:
            # Validate report file exists
            if not os.path.isfile(args.delete_from):
                print(f"Error: Report file not found: {args.delete_from}", file=sys.stderr)
                return 1

            # Load report and filter for deletion candidates
            from diskcomp.reporter import ReportReader
            from diskcomp.deletion import DeletionOrchestrator

            print(f"\nLoading report: {args.delete_from}", file=sys.stderr)
            try:
                candidates = ReportReader.load(args.delete_from)
            except Exception as e:
                print(f"Error reading report: {e}", file=sys.stderr)
                return 1

            if not candidates:
                print("No files marked for deletion in this report.", file=sys.stderr)
                return 0

            # Check for read-only drives
            print(f"\nFound {len(candidates)} files to delete.", file=sys.stderr)
            deletable, readonly_warnings = _check_deletion_readiness(candidates)

            if readonly_warnings:
                print("\nSome files are on read-only drives:", file=sys.stderr)
                for warning in readonly_warnings:
                    print(f"  - {warning}", file=sys.stderr)
                print(f"\nProceeding with {len(deletable)} deletable files.", file=sys.stderr)
                candidates = deletable

            if not candidates:
                print("Error: All files are on read-only drives. Cannot proceed.", file=sys.stderr)
                return 1

            # Prompt for deletion mode (D-04, D-03)
            mode_choice = input("\nDeletion mode? (interactive/batch/skip): ").strip().lower()
            if mode_choice == 'skip' or not mode_choice:
                print("Deletion skipped.", file=sys.stderr)
                return 0

            if mode_choice.startswith('i'):
                mode = 'interactive'
            elif mode_choice.startswith('b'):
                mode = 'batch'
            else:
                print(f"Invalid choice: {mode_choice}. Skipping deletion.", file=sys.stderr)
                return 0

            # Create UI and orchestrator
            ui = UIHandler.create()
            orchestrator = DeletionOrchestrator(candidates, ui, args.delete_from)

            if mode == 'interactive':
                result = orchestrator.interactive_mode()
            else:
                result = orchestrator.batch_mode()

            # Display results (D-10)
            print(f"\nDeletion complete.", file=sys.stderr)
            print(f"Files deleted: {result.files_deleted}", file=sys.stderr)
            print(f"Space freed: {result.space_freed_mb:.2f} MB", file=sys.stderr)
            if result.undo_log_path:
                print(f"Undo log: {result.undo_log_path}", file=sys.stderr)
            if result.aborted:
                remaining = len(candidates) - result.files_deleted
                print(f"\n^C Aborted. {result.files_deleted} files deleted ({result.space_freed_mb:.2f} MB freed) before abort.", file=sys.stderr)
                if result.undo_log_path:
                    print(f"Undo log: {result.undo_log_path}", file=sys.stderr)
                print(f"Remaining {remaining} files were not deleted.", file=sys.stderr)
            if result.errors:
                print(f"\nWarnings/errors encountered:", file=sys.stderr)
                for error in result.errors:
                    print(f"  - {error}", file=sys.stderr)

            ui.close()
            return 0

        except KeyboardInterrupt:
            print(f"\n^C Aborted by user.", file=sys.stderr)
            return 0
        except Exception as e:
            print(f"Error during deletion: {e}", file=sys.stderr)
            return 1

    # Handle --single flag OR interactive single-drive selection
    if args.single or interactive_selection == 'single_drive':
        # Single-drive mode: scan one path, find internal duplicates

        # Determine path: from --single flag or interactive picker
        if args.single:
            single_path = os.path.abspath(args.single)
        else:
            # Interactive mode: launch single-drive picker
            ui = UIHandler.create()
            ui.section("Select Drive to Clean Up")
            ui.blank()

            single_path = interactive_single_drive_picker()
            if single_path is None:
                ui.error("Could not complete drive selection.")
                ui.close()
                return 1

            ui.ok(f"Cleaning up: {single_path}")

        # Validate path
        if not os.path.isdir(single_path):
            print(f"Error: --single path is not a directory: {single_path}", file=sys.stderr)
            if 'ui' not in locals():
                ui = UIHandler.create()
            ui.close()
            return 1

        # Create UI if not already created
        if 'ui' not in locals():
            ui = UIHandler.create()

        try:
            # Scan single drive
            from diskcomp.hasher import group_by_hash_single_drive, group_by_size_single_drive

            scanner = FileScanner(single_path, min_size_bytes=min_size_bytes)
            ui.start_scan(single_path)
            scan_result = scanner.scan(
                dry_run=args.dry_run,
                limit=args.limit,
                on_folder_done=lambda folder_path, count: ui.on_folder_done(folder_path, count)
            )
            ui.on_folder_done(single_path, scan_result.file_count)

            # If dry-run, skip hashing and exit
            if args.dry_run:
                ui.close()
                return 0

            # Two-pass optimization: size filter then hash (D-03)
            candidates, size_stats = group_by_size_single_drive(scan_result.files)

            # Hash candidates
            hasher = FileHasher()
            hashed_records = hasher.hash_files(candidates, on_file_hashed=lambda *args: ui.on_file_hashed(*args))

            # Group by hash to identify duplicates
            single_drive_result = group_by_hash_single_drive(hashed_records)

            # Convert to standard classification dict format for ReportWriter
            classification = {
                'duplicates': single_drive_result['duplicates'],
                'unique_in_keep': [],
                'unique_in_other': single_drive_result['unique'],
                'summary': single_drive_result['summary'],
            }

            # Generate report
            writer = ReportWriter(output_path=args.output)
            if args.format == 'json':
                writer.write_json(classification)
            else:  # default csv
                writer.write_csv(classification)

            # Display summary
            get_drive_label = lambda p: os.path.basename(p.rstrip('/\\')) or p
            drive_label = get_drive_label(single_path)
            summary = classification['summary']
            ui.show_summary(
                duplicates_mb=summary['duplicate_size_mb'],
                duplicates_count=summary['duplicate_count'],
                unique_keep_mb=0,
                unique_keep_count=0,
                unique_other_mb=summary['unique_in_other_size_mb'],
                unique_other_count=summary['unique_in_other_count'],
                report_path=writer.output_path,
                mode='single_drive'
            )

            # Plain-language summary and next steps
            show_plain_language_summary(summary, mode='single_drive', keep_label=drive_label, other_label=drive_label)
            show_next_steps(writer.output_path)

            # Show post-scan menu if duplicates found (D-24)
            if summary.get('duplicate_count', 0) > 0:
                # Initialize NavigationContext with scan results
                context = NavigationContext(
                    scan_results=classification,
                    keep_path=single_path,
                    other_path=single_path,
                    report_path=writer.output_path
                )

                # Run post-scan menu workflow (handles folder skip, file flagging, deletion, back navigation)
                outcome = run_post_scan_menu(context, ui)

                # Handle outcome
                if outcome == 'deleted':
                    # Deletion completed successfully
                    print(f"\nDeletion workflow completed", file=sys.stderr)
                elif outcome == 'aborted':
                    # User pressed Ctrl+C during deletion
                    print(f"\nDeletion aborted by user", file=sys.stderr)
                elif outcome == 'skipped_deletion':
                    # User chose not to delete
                    print(f"\nNo deletion performed", file=sys.stderr)

            ui.close()
            return 0

        except KeyboardInterrupt:
            print(f"\n^C Aborted by user.", file=sys.stderr)
            ui.close()
            return 0
        except Exception as e:
            print(f"Error during single-drive scan: {e}", file=sys.stderr)
            ui.close()
            return 1

    # Instantiate UI
    ui = UIHandler.create()

    try:
        # If no paths provided, launch interactive drive picker
        if not args.keep or not args.other:
            ui.section("Interactive Drive Setup")
            ui.blank()

            selected = interactive_drive_picker()
            if selected is None:
                ui.error("Could not complete drive selection.")
                ui.close()
                return 1

            args.keep = selected['keep']
            args.other = selected['other']

            ui.ok(f"Keep: {args.keep}  |  Other: {args.other}")

        # Validate paths exist and are readable
        for path_name, path in [('--keep', args.keep), ('--other', args.other)]:
            if not os.path.isdir(path):
                print(f"Error: {path_name} path is not a readable directory: {path}", file=sys.stderr)
                ui.close()
                return 1
            if not os.access(path, os.R_OK):
                print(f"Error: {path_name} path is not readable: {path}", file=sys.stderr)
                ui.close()
                return 1

        # Run health checks on both drives
        if not display_health_checks(args.keep, args.other, ui):
            ui.close()
            return 1

        # Ask user to confirm before scan starts
        ui.section("Ready to Scan")
        confirm = input("\n  Start scan? (y/n): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("Scan cancelled.")
            ui.close()
            return 0

        # Scan keep drive with UI callback
        ui.start_scan(args.keep)
        keep_scanner = FileScanner(args.keep, min_size_bytes=min_size_bytes)
        keep_result = keep_scanner.scan(
            dry_run=args.dry_run,
            limit=args.limit,
            on_folder_done=lambda folder_path, count: ui.on_folder_done(folder_path, count)
        )

        # Scan other drive with UI callback
        ui.start_scan(args.other)
        other_scanner = FileScanner(args.other, min_size_bytes=min_size_bytes)
        other_result = other_scanner.scan(
            dry_run=args.dry_run,
            limit=args.limit,
            on_folder_done=lambda folder_path, count: ui.on_folder_done(folder_path, count)
        )

        # If dry-run, skip hashing and exit
        if args.dry_run:
            ui.close()
            return 0

        # Apply size filter (two-pass optimization)
        from diskcomp.hasher import filter_by_size_collision

        keep_filtered, other_filtered, filter_stats = filter_by_size_collision(
            keep_result.files,
            other_result.files
        )

        # Print size filter status line per D-03
        pct_skipped = filter_stats['pct_skipped']
        total_files = filter_stats['total_scanned']
        candidates = filter_stats['candidate_count']
        status_line = f"Size filter: {total_files:,} files → {candidates:,} candidates ({pct_skipped}% skipped)"
        ui.ok(status_line)

        # Combine filtered records for hashing
        all_records_filtered = keep_filtered + other_filtered

        # Hash only candidates with UI callback
        ui.start_hash(len(all_records_filtered))
        all_records = all_records_filtered

        def on_file_hashed_callback(current, total, speed_mbps, eta_secs):
            ui.on_file_hashed(current, total, speed_mbps, eta_secs)

        hasher = FileHasher()
        hashed_records = hasher.hash_files(all_records, on_file_hashed_callback)

        # Split back into keep/other
        keep_count_filtered = len(keep_filtered)
        keep_result.files = hashed_records[:keep_count_filtered]
        other_result.files = hashed_records[keep_count_filtered:]

        # Count files with errors
        keep_errors = sum(1 for f in keep_result.files if f.error)
        other_errors = sum(1 for f in other_result.files if f.error)
        if keep_errors > 0 or other_errors > 0:
            ui.warn(f"{keep_errors} errors hashing keep files, {other_errors} errors in other files")

        # Classify duplicates
        ui.ok("Classifying duplicates...")
        classifier = DuplicateClassifier(keep_result, other_result)
        classification = classifier.classify()

        # Write report
        ui.ok("Writing report...")
        writer = ReportWriter(output_path=args.output)
        if args.format == 'json':
            writer.write_json(classification)
        else:  # default csv
            writer.write_csv(classification)

        # Display summary using UI
        summary = classification['summary']
        ui.show_summary(
            duplicates_mb=summary['duplicate_size_mb'],
            duplicates_count=summary['duplicate_count'],
            unique_keep_mb=summary['unique_in_keep_size_mb'],
            unique_keep_count=summary['unique_in_keep_count'],
            unique_other_mb=summary['unique_in_other_size_mb'],
            unique_other_count=summary['unique_in_other_count'],
            report_path=writer.output_path
        )

        # Show plain-language summary (D-16)
        show_plain_language_summary(summary, mode='two_drives', keep_label='Keep', other_label='Other')

        # Show next steps (D-18)
        show_next_steps(writer.output_path)

        # Show post-scan menu if duplicates found (D-24)
        if summary.get('duplicate_count', 0) > 0:
            # Initialize NavigationContext with scan results
            context = NavigationContext(
                scan_results=classification,
                keep_path=args.keep,
                other_path=args.other,
                report_path=writer.output_path
            )

            # Run post-scan menu workflow (handles folder skip, file flagging, deletion, back navigation)
            outcome = run_post_scan_menu(context, ui)

            # Handle outcome
            if outcome == 'deleted':
                # Deletion completed successfully
                print(f"\nDeletion workflow completed", file=sys.stderr)
            elif outcome == 'aborted':
                # User pressed Ctrl+C during deletion
                print(f"\nDeletion aborted by user", file=sys.stderr)
            elif outcome == 'skipped_deletion':
                # User chose not to delete
                print(f"\nNo deletion performed", file=sys.stderr)

        # Close UI
        ui.close()
        return 0

    except InvalidPathError as e:
        print(f"Error: {e}", file=sys.stderr)
        ui.close()
        return 1
    except ScanError as e:
        print(f"Error: {e}", file=sys.stderr)
        ui.close()
        return 1
    except FileNotReadableError as e:
        print(f"Error: {e}", file=sys.stderr)
        ui.close()
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        ui.close()
        return 1


if __name__ == '__main__':
    sys.exit(main())
