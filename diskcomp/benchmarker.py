"""
Read speed benchmarking module for diskcomp.

This module benchmarks sequential read speed on a drive by creating a temporary
test file, writing test data, and measuring read throughput.
"""

import tempfile
import os
import time

from diskcomp.types import BenchmarkResult


def benchmark_read_speed(
    mount_point: str,
    test_size_mb: int = 128,
    chunk_size_kb: int = 512
) -> BenchmarkResult:
    """
    Benchmark sequential read speed on a drive.

    Creates a temporary test file on the drive, writes test data, measures
    sequential read speed, and cleans up. Returns detailed timing and speed metrics.

    Args:
        mount_point: Path to drive to test
        test_size_mb: Size of test file in MB (default 128)
        chunk_size_kb: Read chunk size in KB (default 512)

    Returns:
        BenchmarkResult with speed_mbps, duration_secs, bytes_read, success, error
    """
    test_size_bytes = test_size_mb * (1024 ** 2)
    chunk_size_bytes = chunk_size_kb * 1024
    fd = None
    temp_path = None

    try:
        # Create temporary test file
        fd, temp_path = tempfile.mkstemp(dir=mount_point, prefix='diskcomp_bench_')

        # Write test data
        with os.fdopen(fd, 'wb') as f:
            fd = None  # os.fdopen now owns and will close fd
            bytes_written = 0
            while bytes_written < test_size_bytes:
                chunk = b'\0' * min(chunk_size_bytes, test_size_bytes - bytes_written)
                f.write(chunk)
                bytes_written += len(chunk)

        # Allow disk cache to settle
        time.sleep(0.1)

        # Measure read speed (perf_counter has nanosecond resolution on all platforms)
        start_time = time.perf_counter()
        bytes_read = 0

        with open(temp_path, 'rb') as f:
            while True:
                chunk = f.read(chunk_size_bytes)
                if not chunk:
                    break
                bytes_read += len(chunk)

        elapsed = time.perf_counter() - start_time

        # Calculate speed in MB/s
        if elapsed > 0:
            speed_mbps = (bytes_read / (1024 ** 2)) / elapsed
        else:
            speed_mbps = 0.0

        return BenchmarkResult(
            mountpoint=mount_point,
            speed_mbps=speed_mbps,
            duration_secs=elapsed,
            bytes_read=bytes_read,
            success=True,
            error=None
        )

    except Exception as e:
        return BenchmarkResult(
            mountpoint=mount_point,
            speed_mbps=0.0,
            duration_secs=0.0,
            bytes_read=0,
            success=False,
            error=str(e)
        )

    finally:
        # Clean up temporary file
        if temp_path:
            try:
                os.remove(temp_path)
            except Exception:
                pass
