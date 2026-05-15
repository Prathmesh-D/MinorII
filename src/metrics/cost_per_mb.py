"""Cost-per-MB calculator — ms/MB from time and file size."""

from __future__ import annotations


def calculate_cost_per_mb(time_ns: float, file_size_bytes: int) -> float:
    """Return cost in milliseconds per megabyte.

    Formula: (time_ns / 1_000_000) / (file_size_bytes / 1_048_576)
    """
    if file_size_bytes <= 0:
        return 0.0
    time_ms = time_ns / 1_000_000
    size_mb = file_size_bytes / 1_048_576
    return time_ms / size_mb
