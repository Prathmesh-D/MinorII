"""Statistical helpers — operate on raw time lists, skipping warm-up runs."""

from __future__ import annotations

import numpy as np


def mean(times: list[int], warmup_runs: int = 1) -> float:
    """Mean of *times[warmup_runs:]* (warm-up samples discarded)."""
    kept = times[warmup_runs:]
    if not kept:
        return 0.0
    return float(np.mean(kept))


def std_deviation(times: list[int], warmup_runs: int = 1) -> float:
    """Sample standard deviation of *times[warmup_runs:]* (ddof=1)."""
    kept = times[warmup_runs:]
    if len(kept) < 2:
        return 0.0
    return float(np.std(kept, ddof=1))


def minimum(times: list[int], warmup_runs: int = 1) -> int:
    """Minimum of *times[warmup_runs:]*."""
    kept = times[warmup_runs:]
    if not kept:
        return 0
    return int(np.min(kept))


def maximum(times: list[int], warmup_runs: int = 1) -> int:
    """Maximum of *times[warmup_runs:]*."""
    kept = times[warmup_runs:]
    if not kept:
        return 0
    return int(np.max(kept))
