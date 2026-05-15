"""CSV logger — appends benchmark rows with all derived metrics."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Optional

from src.benchmark.benchmark_runner import BenchmarkResult
from src.benchmark.experiment_config import Config
from src.metrics.cost_per_mb import calculate_cost_per_mb
from src.metrics.overhead_calculator import (
    calculate_overhead_ns,
    calculate_overhead_percent,
)
from src.metrics.stats_calculator import maximum, mean, minimum, std_deviation
from src.metrics.throughput_calculator import calculate_throughput

COLUMNS = [
    "timestamp",
    "file_group",
    "file_type",
    "mode",
    "file_size_bytes",
    "file_size_mb",
    "avg_enc_time_ns",
    "avg_dec_time_ns",
    "avg_enc_time_ms",
    "avg_dec_time_ms",
    "enc_throughput_mbps",
    "dec_throughput_mbps",
    "authentication_overhead_ns",
    "overhead_percent",
    "cost_per_mb_enc",
    "cost_per_mb_dec",
    "std_dev_enc_ns",
    "std_dev_dec_ns",
    "min_enc_ns",
    "max_enc_ns",
    "min_dec_ns",
    "max_dec_ns",
    "raw_enc_times_ns",
    "raw_dec_times_ns",
]


def _pipe_join(times: list[int]) -> str:
    """Format raw times as a pipe-separated string."""
    return "|".join(str(t) for t in times)


def _build_row(
    result: BenchmarkResult,
    overhead_ns: float = 0.0,
    overhead_pct: float = 0.0,
    warmup_runs: int = 1,
) -> dict:
    """Build a single CSV row dict from a BenchmarkResult + overhead values."""
    avg_enc_ns = result.avg_enc_time_ns
    avg_dec_ns = result.avg_dec_time_ns

    return {
        "timestamp": result.timestamp,
        "file_group": result.file_group,
        "file_type": result.file_type,
        "mode": result.mode,
        "file_size_bytes": result.file_size_bytes,
        "file_size_mb": result.file_size_mb,
        "avg_enc_time_ns": round(avg_enc_ns, 2),
        "avg_dec_time_ns": round(avg_dec_ns, 2),
        "avg_enc_time_ms": round(avg_enc_ns / 1_000_000, 6),
        "avg_dec_time_ms": round(avg_dec_ns / 1_000_000, 6),
        "enc_throughput_mbps": round(
            calculate_throughput(result.file_size_bytes, int(avg_enc_ns)), 4
        ),
        "dec_throughput_mbps": round(
            calculate_throughput(result.file_size_bytes, int(avg_dec_ns)), 4
        ),
        "authentication_overhead_ns": round(overhead_ns, 2),
        "overhead_percent": round(overhead_pct, 4),
        "cost_per_mb_enc": round(
            calculate_cost_per_mb(avg_enc_ns, result.file_size_bytes), 6
        ),
        "cost_per_mb_dec": round(
            calculate_cost_per_mb(avg_dec_ns, result.file_size_bytes), 6
        ),
        "std_dev_enc_ns": round(std_deviation(result.raw_enc_times_ns, warmup_runs), 2),
        "std_dev_dec_ns": round(std_deviation(result.raw_dec_times_ns, warmup_runs), 2),
        "min_enc_ns": minimum(result.raw_enc_times_ns, warmup_runs),
        "max_enc_ns": maximum(result.raw_enc_times_ns, warmup_runs),
        "min_dec_ns": minimum(result.raw_dec_times_ns, warmup_runs),
        "max_dec_ns": maximum(result.raw_dec_times_ns, warmup_runs),
        "raw_enc_times_ns": _pipe_join(result.raw_enc_times_ns),
        "raw_dec_times_ns": _pipe_join(result.raw_dec_times_ns),
    }


class CSVLogger:
    """Append benchmark results to a CSV file with all derived metrics."""

    def __init__(self, config: Config) -> None:
        self._csv_path = Path(config.csv_file)
        self._warmup_runs = config.warmup_runs
        # Ensure parent directory exists
        self._csv_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _write_rows(self, rows: list[dict]) -> None:
        """Append *rows* to the CSV, writing the header if the file is new."""
        write_header = not self._csv_path.exists()
        with open(self._csv_path, "a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=COLUMNS)
            if write_header:
                writer.writeheader()
            writer.writerows(rows)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def log(
        self,
        ctr_result: BenchmarkResult,
        gcm_result: BenchmarkResult,
    ) -> None:
        """Log a paired CTR + GCM experiment (two rows).

        Overhead columns are populated on the GCM row only; the CTR row
        gets 0.0 for both overhead fields.
        """
        ctr_row = _build_row(ctr_result, overhead_ns=0.0, overhead_pct=0.0,
                             warmup_runs=self._warmup_runs)

        overhead_ns = calculate_overhead_ns(
            gcm_result.avg_enc_time_ns, ctr_result.avg_enc_time_ns
        )
        overhead_pct = calculate_overhead_percent(
            gcm_result.avg_enc_time_ns, ctr_result.avg_enc_time_ns
        )
        gcm_row = _build_row(gcm_result, overhead_ns=overhead_ns, overhead_pct=overhead_pct,
                             warmup_runs=self._warmup_runs)

        self._write_rows([ctr_row, gcm_row])

    def log_single(
        self,
        result: BenchmarkResult,
        ctr_ref: Optional[BenchmarkResult] = None,
    ) -> None:
        """Log a single result row (used by the single-file UI tab).

        If *ctr_ref* is provided and *result* is GCM, overhead is
        computed against the CTR reference.  Otherwise overhead is 0.0.
        """
        overhead_ns = 0.0
        overhead_pct = 0.0

        if ctr_ref is not None and result.mode == "AES-GCM":
            overhead_ns = calculate_overhead_ns(
                result.avg_enc_time_ns, ctr_ref.avg_enc_time_ns
            )
            overhead_pct = calculate_overhead_percent(
                result.avg_enc_time_ns, ctr_ref.avg_enc_time_ns
            )

        row = _build_row(result, overhead_ns=overhead_ns, overhead_pct=overhead_pct,
                         warmup_runs=self._warmup_runs)
        self._write_rows([row])
