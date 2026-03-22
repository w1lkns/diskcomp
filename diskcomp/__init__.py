"""diskcomp — compare two drives and find duplicates."""

__version__ = "0.1.0"
__author__ = "Wilkins Morales"

from diskcomp.scanner import FileScanner
from diskcomp.hasher import FileHasher
from diskcomp.reporter import DuplicateClassifier, ReportWriter
from diskcomp.types import FileRecord, ScanResult, ScanError

__all__ = [
    "FileScanner",
    "FileHasher",
    "DuplicateClassifier",
    "ReportWriter",
    "FileRecord",
    "ScanResult",
    "ScanError",
]
