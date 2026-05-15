"""Tests for benchmark summary outputs."""

from __future__ import annotations

from pathlib import Path
import math

import pandas as pd

from src.reporting.benchmark_report import (
    compute_benchmark_summary,
)


def _sample_df() -> pd.DataFrame:
    rows = [
        {
            "timestamp": "2026-01-01T00:00:00+00:00",
            "file_group": "F1_1MB",
            "file_type": "text",
            "mode": "AES-CTR",
            "file_size_mb": 1.0,
            "avg_enc_time_ms": 2.0,
            "enc_throughput_mbps": 500.0,
            "overhead_percent": 0.0,
            "raw_enc_times_ns": "1000|1100|1080|1120|1090",
        },
        {
            "timestamp": "2026-01-01T00:00:00+00:00",
            "file_group": "F1_1MB",
            "file_type": "text",
            "mode": "AES-GCM",
            "file_size_mb": 1.0,
            "avg_enc_time_ms": 2.4,
            "enc_throughput_mbps": 430.0,
            "overhead_percent": 20.0,
            "raw_enc_times_ns": "2000|2100|2080|2120|2090",
        },
        {
            "timestamp": "2026-01-01T00:01:00+00:00",
            "file_group": "F2_5MB",
            "file_type": "binary",
            "mode": "AES-CTR",
            "file_size_mb": 5.0,
            "avg_enc_time_ms": 10.0,
            "enc_throughput_mbps": 500.0,
            "overhead_percent": 0.0,
            "raw_enc_times_ns": "5000|5100|5080|5120|5090",
        },
        {
            "timestamp": "2026-01-01T00:01:00+00:00",
            "file_group": "F2_5MB",
            "file_type": "binary",
            "mode": "AES-GCM",
            "file_size_mb": 5.0,
            "avg_enc_time_ms": 11.0,
            "enc_throughput_mbps": 450.0,
            "overhead_percent": 10.0,
            "raw_enc_times_ns": "9000|9100|9080|9120|9090",
        },
    ]
    return pd.DataFrame(rows)


def test_compute_benchmark_summary_has_expected_fields(tmp_path: Path) -> None:
    csv_path = tmp_path / "benchmark_results.csv"
    df = _sample_df()
    summary = compute_benchmark_summary(df, csv_path=csv_path, warmup_runs=1)

    assert summary.total_rows == 4
    assert summary.total_experiments == 2
    assert summary.avg_ctr_enc_ms > 0
    assert summary.avg_gcm_enc_ms > 0
    assert summary.gcm_faster_count == 0
    # Welch fields still computed in backend (dataclass preserved)
    assert math.isfinite(summary.welch_t_stat)
    assert math.isfinite(summary.welch_p_value)
    assert isinstance(summary.welch_significant, bool)
    assert summary.welch_n_ctr > 0
    assert summary.welch_n_gcm > 0
    # Conclusions use plain-language throughput / overhead / stability lines
    assert any(
        "throughput ratio" in line or "overhead" in line.lower()
        for line in summary.conclusions
    )
    assert len(summary.conclusions) >= 3
    assert not summary.size_breakdown.empty
    assert not summary.filetype_breakdown.empty
