"""Throughput calculator — MB/s from file size and elapsed time."""

from __future__ import annotations


def calculate_throughput(file_size_bytes: int, time_ns: int) -> float:
    """Return throughput in MB/s.

    Formula: (file_size_bytes / 1_048_576) / (time_ns / 1_000_000_000)
    """
    if time_ns <= 0:
        return 0.0
    size_mb = file_size_bytes / 1_048_576
    time_s = time_ns / 1_000_000_000
    return size_mb / time_s
