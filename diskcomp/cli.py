"""
Command-line interface for diskcomp.

This module provides the argparse CLI and main orchestration logic that ties
together the scanner, hasher, and reporter modules into a complete workflow.
"""

import argparse
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
    print("\n=== Drive Health Checks ===\n", file=sys.stderr)

    # Check keep drive
    print(f"Checking '{keep_path}'...", file=sys.stderr)
    keep_health = check_drive_health(keep_path)
    _display_health_result("Keep", keep_health)

    # Check other drive
    print(f"Checking '{other_path}'...", file=sys.stderr)
    other_health = check_drive_health(other_path)
    _display_health_result("Other", other_health)

    # If both drives are readable, proceed (warnings don't block)
    if keep_health.is_writable and other_health.is_writable:
        print("\nBoth drives readable. Proceeding with scan.", file=sys.stderr)
        return True

    # If keep drive is not writable, block (can't write scan results)
    if not keep_health.is_writable:
        print("Error: Keep drive is not writable. Cannot proceed.", file=sys.stderr)
        return False

    # Other drive read-only is OK (we only read from it)
    print("\nOther drive is read-only, but scan can proceed (read-only is OK).", file=sys.stderr)
    return True


def _display_health_result(drive_name, health):
    """Helper to print health check results."""
    print(f"\n{drive_name} Drive:", file=sys.stderr)
    print(f"  Space: {health.used_gb}GB used / {health.total_gb}GB total ({health.free_gb}GB free)", file=sys.stderr)
    print(f"  Filesystem: {health.fstype}", file=sys.stderr)
    print(f"  Writable: {'Yes' if health.is_writable else 'NO (READ-ONLY)'}", file=sys.stderr)

    if health.warnings:
        for warning in health.warnings:
            print(f"  WARNING: {warning}", file=sys.stderr)

    if health.errors:
        for error in health.errors:
            print(f"  ERROR: {error}", file=sys.stderr)


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

    # Instantiate UI
    ui = UIHandler.create()

    try:
        # If no paths provided, launch interactive drive picker
        if not args.keep or not args.other:
            print("\n=== Interactive Drive Setup ===\n", file=sys.stderr)
            print("Available mounted drives:\n", file=sys.stderr)

            selected = interactive_drive_picker()
            if selected is None:
                print("Error: Could not complete drive selection.", file=sys.stderr)
                ui.close()
                return 1

            args.keep = selected['keep']
            args.other = selected['other']

            print(f"\nSelected: Keep={args.keep}, Other={args.other}\n", file=sys.stderr)

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
        print("\n=== Ready to Scan ===\n", file=sys.stderr)
        confirm = input("Start scan? (y/n): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("Scan cancelled.", file=sys.stderr)
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

        # Hash all files with UI callback
        ui.start_hash(len(keep_result.files) + len(other_result.files))
        all_records = keep_result.files + other_result.files

        def on_file_hashed_callback(current, total, speed_mbps, eta_secs):
            ui.on_file_hashed(current, total, speed_mbps, eta_secs)

        hasher = FileHasher()
        hashed_records = hasher.hash_files(all_records, on_file_hashed_callback)

        # Split back into keep/other
        keep_count = len(keep_result.files)
        keep_result.files = hashed_records[:keep_count]
        other_result.files = hashed_records[keep_count:]

        # Count files with errors
        keep_errors = sum(1 for f in keep_result.files if f.error)
        other_errors = sum(1 for f in other_result.files if f.error)
        if keep_errors > 0 or other_errors > 0:
            print(f"  Warning: {keep_errors} errors hashing keep files, {other_errors} errors in other files", file=sys.stderr)

        # Classify duplicates
        print("Classifying duplicates...", file=sys.stderr)
        classifier = DuplicateClassifier(keep_result, other_result)
        classification = classifier.classify()

        # Write report
        print("Writing report...", file=sys.stderr)
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
