"""Overhead calculator — GCM vs CTR authentication cost."""

from __future__ import annotations

import warnings


def calculate_overhead_ns(gcm_ns: float, ctr_ns: float) -> float:
    """Return absolute authentication overhead in nanoseconds.

    Returns 0.0 if the result would be negative.
    """
    diff = gcm_ns - ctr_ns
    if diff < 0:
        return 0.0
    return diff


def calculate_overhead_percent(gcm_ns: float, ctr_ns: float) -> float:
    """Return overhead as a percentage of CT time.

    Formula: ((gcm_ns - ctr_ns) / ctr_ns) * 100

    Returns 0.0 (with warning) when *ctr_ns* <= 0, or when the
    result would be negative.
    """
    if ctr_ns <= 0:
        warnings.warn("ctr_ns <= 0; returning 0.0 for overhead percent")
        return 0.0
    pct = ((gcm_ns - ctr_ns) / ctr_ns) * 100
    if pct < 0:
        return 0.0
    return pct
