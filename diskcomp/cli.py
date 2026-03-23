"""
Command-line interface for diskcomp.

This module provides the argparse CLI and main orchestration logic that ties
together the scanner, hasher, and reporter modules into a complete workflow.
"""

import argparse
import json
import os
import sys
from datetime import datetime

from diskcomp.scanner import FileScanner
from diskcomp.hasher import FileHasher
from diskcomp.reporter import DuplicateClassifier, ReportWriter
from diskcomp.ui import UIHandler
from diskcomp.types import ScanError, InvalidPathError, FileNotReadableError
from diskcomp.drive_picker import interactive_drive_picker
from diskcomp.health import check_drive_health
from diskcomp.benchmarker import benchmark_read_speed


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
        other_path = candidate['other_path']
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
    """.strip()

    print(banner)
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

    # Detect interactive (no-args) mode: no --keep, --other, --delete-from, --undo
    is_interactive_mode = (
        not args.keep
        and not args.other
        and not args.delete_from
        and not args.undo
    )

    if is_interactive_mode:
        show_startup_banner()


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
        keep_scanner = FileScanner(args.keep)
        keep_result = keep_scanner.scan(
            dry_run=args.dry_run,
            limit=args.limit,
            on_folder_done=lambda folder_path, count: ui.on_folder_done(folder_path, count)
        )

        # Scan other drive with UI callback
        ui.start_scan(args.other)
        other_scanner = FileScanner(args.other)
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
