"""Tests for metric calculators."""

import warnings
import pytest

from src.metrics.throughput_calculator import calculate_throughput
from src.metrics.overhead_calculator import (
    calculate_overhead_ns,
    calculate_overhead_percent,
)
from src.metrics.cost_per_mb import calculate_cost_per_mb
from src.metrics.stats_calculator import mean, std_deviation, minimum, maximum


# ------------------------------------------------------------------
# Throughput
# ------------------------------------------------------------------

def test_throughput_known_values():
    """1 MB processed in 1 second (1e9 ns) → 1.0 MB/s."""
    size = 1_048_576  # 1 MB
    time_ns = 1_000_000_000  # 1 s
    assert calculate_throughput(size, time_ns) == pytest.approx(1.0)

    # 10 MB in 0.5 s → 20 MB/s
    assert calculate_throughput(10 * 1_048_576, 500_000_000) == pytest.approx(20.0)


# ------------------------------------------------------------------
# Overhead
# ------------------------------------------------------------------

def test_overhead_percent_correct():
    """GCM 150 ns, CTR 100 ns → 50 ns overhead, 50 %."""
    assert calculate_overhead_ns(150, 100) == pytest.approx(50.0)
    assert calculate_overhead_percent(150, 100) == pytest.approx(50.0)


def test_overhead_negative_returns_zero():
    """When GCM is faster than CTR, overhead should be 0.0."""
    assert calculate_overhead_ns(80, 100) == 0.0
    assert calculate_overhead_percent(80, 100) == 0.0

    # ctr_ns == 0 edge case — should warn and return 0.0
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = calculate_overhead_percent(100, 0)
        assert result == 0.0
        assert len(w) == 1
        assert "ctr_ns <= 0" in str(w[0].message)


# ------------------------------------------------------------------
# Stats (skip warm-up at index 0)
# ------------------------------------------------------------------

def test_stats_skips_warmup():
    """Index 0 (999) must be excluded from all stat calculations."""
    times = [999, 100, 200, 300, 400]  # kept = [100, 200, 300, 400]

    assert mean(times) == pytest.approx(250.0)
    assert minimum(times) == 100
    assert maximum(times) == 400
    # sample std dev (ddof=1) of [100, 200, 300, 400]:
    # variance = sum((x-250)^2) / (n-1) = 50000/3 ≈ 16666.67 → std ≈ 129.099
    assert std_deviation(times) == pytest.approx(129.09944, rel=1e-4)


# ------------------------------------------------------------------
# Cost per MB
# ------------------------------------------------------------------

def test_cost_per_mb_known_values():
    """1 MB in 1e6 ns (= 1 ms) → 1.0 ms/MB."""
    assert calculate_cost_per_mb(1_000_000, 1_048_576) == pytest.approx(1.0)

    # 2 MB in 5e6 ns (= 5 ms) → 2.5 ms/MB
    assert calculate_cost_per_mb(5_000_000, 2 * 1_048_576) == pytest.approx(2.5)
