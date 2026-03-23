"""
Duplicate classification and report generation for diskcomp.

This module provides classes for identifying duplicate files across two drives
and generating CSV and JSON reports with atomic writes to prevent partial writes
on crashes.

Key features:
- DuplicateClassifier: Identifies duplicates by hash and classifies files
- ReportWriter: Writes CSV and JSON reports atomically using temp → rename pattern
"""

import csv
import json
import os
import tempfile
from datetime import datetime
from diskcomp.types import FileRecord, ScanResult


class DuplicateClassifier:
    """
    Classifies files as DUPLICATE or UNIQUE based on hash comparison.

    This classifier takes two ScanResult objects (from the keep and other drives)
    and identifies which files are duplicated (same hash on both) and which are
    unique to each drive.

    The output includes a structured classification dict with duplicates, unique
    files, and summary statistics.

    Attributes:
        keep_result: ScanResult from the "keep" drive
        other_result: ScanResult from the "other" drive
    """

    def __init__(self, keep_result: ScanResult, other_result: ScanResult):
        """
        Initialize the classifier with two ScanResult objects.

        Args:
            keep_result: ScanResult from the drive to keep
            other_result: ScanResult from the other drive
        """
        self.keep_result = keep_result
        self.other_result = other_result

    def classify(self) -> dict:
        """
        Classify files as DUPLICATE or UNIQUE.

        Analyzes both ScanResult objects and returns a classification dict
        with duplicates (files on both drives with same hash) and unique files
        (files on only one drive).

        Returns:
            Classification dict with structure:
            {
                'duplicates': [
                    {
                        'action': 'DELETE_FROM_OTHER',
                        'keep_path': str,
                        'other_path': str,
                        'size_mb': float,
                        'hash': str,
                    },
                    ...
                ],
                'unique_in_keep': [
                    {
                        'action': 'UNIQUE_IN_KEEP',
                        'keep_path': str,
                        'other_path': None,
                        'size_mb': float,
                        'hash': str,
                    },
                    ...
                ],
                'unique_in_other': [
                    {
                        'action': 'UNIQUE_IN_OTHER',
                        'keep_path': None,
                        'other_path': str,
                        'size_mb': float,
                        'hash': str,
                    },
                    ...
                ],
                'summary': {
                    'duplicate_count': int,
                    'duplicate_size_mb': float,
                    'unique_in_keep_count': int,
                    'unique_in_keep_size_mb': float,
                    'unique_in_other_count': int,
                    'unique_in_other_size_mb': float,
                }
            }
        """
        # Build hash → FileRecord mapping for keep drive
        keep_hash_map = {}
        for record in self.keep_result.files:
            if record.hash:
                if record.hash not in keep_hash_map:
                    keep_hash_map[record.hash] = []
                keep_hash_map[record.hash].append(record)

        # Build hash → FileRecord mapping for other drive
        other_hash_map = {}
        for record in self.other_result.files:
            if record.hash:
                if record.hash not in other_hash_map:
                    other_hash_map[record.hash] = []
                other_hash_map[record.hash].append(record)

        duplicates = []
        unique_in_other = []
        unique_in_keep = []

        # Track total sizes in bytes for accurate summary calculation
        duplicate_size_bytes = 0
        unique_in_other_size_bytes = 0
        unique_in_keep_size_bytes = 0

        # Process files in other drive
        for hash_val, records in other_hash_map.items():
            if hash_val in keep_hash_map:
                # Duplicate: exists in both drives
                for other_rec in records:
                    keep_rec = keep_hash_map[hash_val][0]  # Use first match
                    duplicates.append({
                        'action': 'DELETE_FROM_OTHER',
                        'keep_path': keep_rec.path,
                        'other_path': other_rec.path,
                        'size_mb': round(other_rec.size_bytes / (1024 ** 2), 2),
                        'hash': hash_val,
                    })
                    duplicate_size_bytes += other_rec.size_bytes
            else:
                # Unique in other
                for other_rec in records:
                    unique_in_other.append({
                        'action': 'UNIQUE_IN_OTHER',
                        'keep_path': None,
                        'other_path': other_rec.path,
                        'size_mb': round(other_rec.size_bytes / (1024 ** 2), 2),
                        'hash': hash_val,
                    })
                    unique_in_other_size_bytes += other_rec.size_bytes

        # Process files in keep drive that aren't in other drive
        for hash_val, records in keep_hash_map.items():
            if hash_val not in other_hash_map:
                # Unique in keep
                for keep_rec in records:
                    unique_in_keep.append({
                        'action': 'UNIQUE_IN_KEEP',
                        'keep_path': keep_rec.path,
                        'other_path': None,
                        'size_mb': round(keep_rec.size_bytes / (1024 ** 2), 2),
                        'hash': hash_val,
                    })
                    unique_in_keep_size_bytes += keep_rec.size_bytes

        # Calculate summary statistics (convert bytes to MB for summary)
        duplicate_size_mb = duplicate_size_bytes / (1024 ** 2)
        unique_in_keep_size_mb = unique_in_keep_size_bytes / (1024 ** 2)
        unique_in_other_size_mb = unique_in_other_size_bytes / (1024 ** 2)

        return {
            'duplicates': duplicates,
            'unique_in_keep': unique_in_keep,
            'unique_in_other': unique_in_other,
            'summary': {
                'duplicate_count': len(duplicates),
                'duplicate_size_mb': round(duplicate_size_mb, 2),
                'unique_in_keep_count': len(unique_in_keep),
                'unique_in_keep_size_mb': round(unique_in_keep_size_mb, 2),
                'unique_in_other_count': len(unique_in_other),
                'unique_in_other_size_mb': round(unique_in_other_size_mb, 2),
            }
        }


class ReportWriter:
    """
    Writes CSV and JSON reports with atomic writes.

    This writer generates reports from classification dicts and writes them
    atomically using a temp file → rename pattern to prevent partial writes
    on system crashes.

    Reports are timestamped (YYYYMMDD-HHMMSS) and include duplicates, unique
    files, and summary statistics.

    Attributes:
        output_path: The exact path to write reports to (computed from output_dir)
    """

    def __init__(self, output_dir: str = None, output_path: str = None):
        """
        Initialize the report writer.

        Either output_path or output_dir must be provided. If output_path is
        given, it is used as-is. If output_dir is given, a timestamped filename
        is generated.

        Args:
            output_dir: Directory to write reports to (default: home directory)
                       Report filename will be generated: diskcomp-report-YYYYMMDD-HHMMSS
            output_path: Exact path to write report to (overrides output_dir)
        """
        if output_path:
            self.output_path = output_path
        else:
            # Use output_dir or default to home directory
            if output_dir is None:
                output_dir = os.path.expanduser("~")

            # Generate timestamped filename
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            base_filename = f"diskcomp-report-{timestamp}"
            self.output_path = os.path.join(output_dir, base_filename)

    def _write_atomic(self, file_path: str, content_writer) -> None:
        """
        Write content to a file atomically using temp → rename pattern.

        This method writes to a temporary file first, then renames it to the
        target path. This ensures that if the process crashes mid-write, the
        original file is not corrupted (or a partial temp file is left).

        Args:
            file_path: Target file path
            content_writer: Callable that takes a file object and writes content

        Raises:
            Exception: If write fails (temp file is cleaned up automatically)
        """
        # Create temp file in same directory as target (same filesystem)
        target_dir = os.path.dirname(file_path) or '.'
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                dir=target_dir,
                delete=False,
                suffix='.tmp'
            ) as tmp_file:
                tmp_path = tmp_file.name
                try:
                    content_writer(tmp_file)
                    tmp_file.flush()
                except Exception:
                    os.unlink(tmp_path)
                    raise

            # Atomic rename (os.replace overwrites on all platforms, including Windows)
            os.replace(tmp_path, file_path)
        except Exception as e:
            # Clean up temp file if it still exists
            try:
                if 'tmp_path' in locals() and os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except Exception:
                pass
            raise e

    def write_csv(self, classification: dict, path: str = None) -> None:
        """
        Write CSV report atomically.

        Generates a CSV with columns: action, keep_path, other_path, size_mb, hash
        Includes all duplicates followed by unique files.

        Args:
            classification: Classification dict from DuplicateClassifier.classify()
            path: Custom path for the report (overrides self.output_path)

        Raises:
            Exception: If write fails
        """
        target_path = path or self.output_path
        if not target_path.endswith('.csv'):
            target_path += '.csv'
        self.output_path = target_path

        status_map = {
            'DELETE_FROM_OTHER': 'Duplicate — safe to delete',
            'UNIQUE_IN_KEEP':    'Only on first drive (keep)',
            'UNIQUE_IN_OTHER':   'Only on second drive',
        }

        def writer_func(f):
            csv_writer = csv.DictWriter(
                f,
                fieldnames=['status', 'original_file', 'duplicate_file', 'size_mb', 'verification_hash']
            )
            csv_writer.writeheader()

            for group in ['duplicates', 'unique_in_keep', 'unique_in_other']:
                for item in classification[group]:
                    csv_writer.writerow({
                        'status':            status_map.get(item['action'], item['action']),
                        'original_file':     item.get('keep_path') or '',
                        'duplicate_file':    item.get('other_path') or '',
                        'size_mb':           item['size_mb'],
                        'verification_hash': item['hash'],
                    })

        self._write_atomic(target_path, writer_func)

    def write_json(self, classification: dict, path: str = None) -> None:
        """
        Write JSON report atomically.

        Generates a JSON file with the complete classification dict,
        pretty-printed for readability.

        Args:
            classification: Classification dict from DuplicateClassifier.classify()
            path: Custom path for the report (overrides self.output_path)

        Raises:
            Exception: If write fails
        """
        target_path = path or self.output_path
        if not target_path.endswith('.json'):
            target_path += '.json'
        self.output_path = target_path

        def writer_func(f):
            json.dump(classification, f, indent=2)

        self._write_atomic(target_path, writer_func)


class ReportReader:
    """
    Reads CSV or JSON reports and extracts deletion candidates.

    Reports from Phase 1–3 contain rows with action column (DELETE_FROM_OTHER,
    UNIQUE_IN_KEEP, UNIQUE_IN_OTHER). This reader filters for DELETE_FROM_OTHER
    entries only, which are candidates for deletion in Mode A and Mode B workflows.

    Static factory methods handle both CSV and JSON formats with auto-detection.
    """

    @staticmethod
    def load_csv(file_path: str) -> list:
        """
        Load CSV report and extract deletion candidates.

        Args:
            file_path: Path to report CSV file

        Returns:
            List of dicts with keys: action, keep_path, other_path, size_mb, hash

        Raises:
            FileNotFoundError: If report file doesn't exist
            ValueError: If CSV format is invalid
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Report file not found: {file_path}")

        candidates = []
        try:
            with open(file_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not row:
                        continue
                    # Support both new friendly format and old technical format
                    status = row.get('status') or row.get('action', '')
                    if status in ('Duplicate — safe to delete', 'DELETE_FROM_OTHER'):
                        # Normalise to new key names
                        if 'duplicate_file' not in row:
                            row['duplicate_file'] = row.get('other_path', '')
                            row['original_file'] = row.get('keep_path', '')
                            row['verification_hash'] = row.get('hash', '')
                        candidates.append(row)
        except csv.Error as e:
            raise ValueError(f"CSV format error: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to read CSV report: {e}") from e

        return candidates

    @staticmethod
    def load_json(file_path: str) -> list:
        """
        Load JSON report and extract deletion candidates.

        Args:
            file_path: Path to report JSON file

        Returns:
            List of dicts with keys: action, keep_path, other_path, size_mb, hash

        Raises:
            FileNotFoundError: If report file doesn't exist
            ValueError: If JSON format is invalid
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Report file not found: {file_path}")

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON format error: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to read JSON report: {e}") from e

        # JSON format has 'duplicates' key with list of items
        duplicates = data.get('duplicates', [])
        candidates = [item for item in duplicates if item.get('action') == 'DELETE_FROM_OTHER']
        return candidates

    @staticmethod
    def load(file_path: str) -> list:
        """
        Auto-detect format and load report.

        Args:
            file_path: Path to report (CSV or JSON)

        Returns:
            List of deletion candidate dicts

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If format is invalid
        """
        if file_path.endswith('.json'):
            return ReportReader.load_json(file_path)
        else:
            # Default to CSV
            return ReportReader.load_csv(file_path)


# Example usage (commented out):
# classifier = DuplicateClassifier(keep_result, other_result)
# classification = classifier.classify()
# writer = ReportWriter(output_dir="/tmp")
# writer.write_csv(classification)
# writer.write_json(classification)
