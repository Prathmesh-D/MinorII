"""Benchmark summary analysis with Welch t-test statistics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import ttest_ind, mannwhitneyu


@dataclass
class BenchmarkSummary:
    """Structured benchmark summary for UI display."""

    generated_at: str
    csv_path: Path
    total_rows: int
    total_experiments: int
    avg_ctr_enc_ms: float
    avg_gcm_enc_ms: float
    signed_overhead_mean_pct: float
    clipped_overhead_mean_pct: float
    gcm_to_ctr_throughput_ratio: float
    gcm_faster_count: int
    mean_cv_ctr_pct: float
    mean_cv_gcm_pct: float
    welch_t_stat: float
    welch_df: float
    welch_p_value: float
    welch_alpha: float
    welch_significant: bool
    welch_n_ctr: int
    welch_n_gcm: int
    mwu_stat: float
    mwu_p_value: float
    mwu_significant: bool
    conclusions: list[str]
    size_breakdown: pd.DataFrame
    filetype_breakdown: pd.DataFrame


def _parse_pipe_times(cell: Any) -> list[float]:
    if cell is None:
        return []
    text = str(cell).strip()
    if not text or text.lower() == "nan":
        return []
    out: list[float] = []
    for item in text.split("|"):
        item = item.strip()
        if not item:
            continue
        try:
            out.append(float(item))
        except ValueError:
            continue
    return out


def _mean_cv(raw_series: pd.Series, warmup_runs: int) -> float:
    values: list[float] = []
    for cell in raw_series.tolist():
        raw_ns = _parse_pipe_times(cell)
        kept = raw_ns[warmup_runs:] if len(raw_ns) > warmup_runs else raw_ns
        if len(kept) < 2:
            continue
        mean_v = float(np.mean(kept))
        if mean_v <= 0:
            continue
        std_v = float(np.std(kept, ddof=1))
        values.append((std_v / mean_v) * 100.0)

    if not values:
        return 0.0
    return float(np.mean(values))


def _extract_enc_sample_df(df: pd.DataFrame, warmup_runs: int) -> pd.DataFrame:
    """Build per-run encryption-time samples (ms) from raw pipe columns."""
    rows: list[dict[str, Any]] = []

    for _, row in df.iterrows():
        mode = str(row.get("mode", ""))
        if mode not in {"AES-CTR", "AES-GCM"}:
            continue

        size_mb = float(row.get("file_size_mb", 0) or 0)
        raw = _parse_pipe_times(row.get("raw_enc_times_ns"))
        kept = raw[warmup_runs:] if len(raw) > warmup_runs else raw

        if not kept:
            fallback_ns = float(row.get("avg_enc_time_ns", 0) or 0)
            if fallback_ns > 0:
                kept = [fallback_ns]

        for ns in kept:
            rows.append(
                {
                    "mode": mode,
                    "file_group": str(row.get("file_group", "")),
                    "file_type": str(row.get("file_type", "")),
                    "file_size_mb": size_mb,
                    "enc_ms": float(ns) / 1_000_000,
                }
            )

    return pd.DataFrame(rows)


def _welch_t_test(
    sample_a: list[float],
    sample_b: list[float],
    alpha: float = 0.05,
) -> tuple[float, float, float, bool]:
    """Run Welch's t-test and return (t_stat, df, p_value, significant)."""
    if len(sample_a) < 2 or len(sample_b) < 2:
        return float("nan"), float("nan"), float("nan"), False

    res = ttest_ind(sample_a, sample_b, equal_var=False, nan_policy="omit")
    t_stat = float(res.statistic)
    p_val = float(res.pvalue)
    df = float(getattr(res, "df", np.nan))
    significant = bool(np.isfinite(p_val) and p_val < alpha)
    return t_stat, df, p_val, significant

def load_benchmark_dataframe(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        return pd.DataFrame()

    df = pd.read_csv(csv_path)
    if df.empty:
        return df

    numeric_cols = [
        "file_size_mb",
        "avg_enc_time_ms",
        "avg_dec_time_ms",
        "enc_throughput_mbps",
        "dec_throughput_mbps",
        "overhead_percent",
        "cost_per_mb_enc",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ("mode", "file_group", "file_type", "timestamp"):
        if col in df.columns:
            df[col] = df[col].astype(str)

    return df


def compute_benchmark_summary(
    df: pd.DataFrame,
    csv_path: Path,
    warmup_runs: int = 1,
    alpha: float = 0.05,
) -> BenchmarkSummary:
    if df.empty:
        return BenchmarkSummary(
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            csv_path=csv_path,
            total_rows=0,
            total_experiments=0,
            avg_ctr_enc_ms=0.0,
            avg_gcm_enc_ms=0.0,
            signed_overhead_mean_pct=0.0,
            clipped_overhead_mean_pct=0.0,
            gcm_to_ctr_throughput_ratio=0.0,
            gcm_faster_count=0,
            mean_cv_ctr_pct=0.0,
            mean_cv_gcm_pct=0.0,
            welch_t_stat=float("nan"),
            welch_df=float("nan"),
            welch_p_value=float("nan"),
            welch_alpha=alpha,
            welch_significant=False,
            welch_n_ctr=0,
            welch_n_gcm=0,
            mwu_stat=float("nan"),
            mwu_p_value=float("nan"),
            mwu_significant=False,
            conclusions=["No benchmark rows found. Run the benchmark first."],
            size_breakdown=pd.DataFrame(),
            filetype_breakdown=pd.DataFrame(),
        )

    ctr = df[df["mode"] == "AES-CTR"].copy()
    gcm = df[df["mode"] == "AES-GCM"].copy()

    # Pair CTR and GCM rows for signed overhead calculations.
    keys = ["timestamp", "file_group", "file_type", "file_size_mb"]
    pair = (
        df.pivot_table(index=keys, columns="mode", values="avg_enc_time_ms", aggfunc="mean")
        .reset_index()
    )
    if {"AES-CTR", "AES-GCM"}.issubset(pair.columns):
        pair = pair.dropna(subset=["AES-CTR", "AES-GCM"])
        pair["signed_overhead_pct"] = (
            (pair["AES-GCM"] - pair["AES-CTR"]) / pair["AES-CTR"]
        ) * 100.0
    else:
        pair["signed_overhead_pct"] = pd.Series(dtype=float)

    avg_ctr_enc_ms = float(ctr["avg_enc_time_ms"].mean()) if not ctr.empty else 0.0
    avg_gcm_enc_ms = float(gcm["avg_enc_time_ms"].mean()) if not gcm.empty else 0.0
    clipped_overhead_mean_pct = float(gcm["overhead_percent"].mean()) if not gcm.empty else 0.0
    signed_overhead_mean_pct = float(pair["signed_overhead_pct"].mean()) if not pair.empty else 0.0

    ctr_tp = float(ctr["enc_throughput_mbps"].mean()) if not ctr.empty else 0.0
    gcm_tp = float(gcm["enc_throughput_mbps"].mean()) if not gcm.empty else 0.0
    ratio = (gcm_tp / ctr_tp) if ctr_tp > 0 else 0.0

    gcm_faster_count = int((pair["signed_overhead_pct"] < 0).sum()) if not pair.empty else 0
    total_experiments = int(len(pair)) if not pair.empty else 0

    mean_cv_ctr = _mean_cv(ctr.get("raw_enc_times_ns", pd.Series(dtype=object)), warmup_runs)
    mean_cv_gcm = _mean_cv(gcm.get("raw_enc_times_ns", pd.Series(dtype=object)), warmup_runs)

    sample_df = _extract_enc_sample_df(df, warmup_runs)
    ctr_samples = sample_df[sample_df["mode"] == "AES-CTR"]["enc_ms"].tolist()
    gcm_samples = sample_df[sample_df["mode"] == "AES-GCM"]["enc_ms"].tolist()
    welch_t_stat, welch_df, welch_p_value, welch_significant = _welch_t_test(
        ctr_samples,
        gcm_samples,
        alpha=alpha,
    )

    # Mann-Whitney U (non-parametric alternative, no normality assumption)
    mwu_stat, mwu_p_value, mwu_significant = float("nan"), float("nan"), False
    if len(ctr_samples) >= 2 and len(gcm_samples) >= 2:
        try:
            res_mwu = mannwhitneyu(ctr_samples, gcm_samples, alternative="two-sided")
            mwu_stat = float(res_mwu.statistic)
            mwu_p_value = float(res_mwu.pvalue)
            mwu_significant = bool(np.isfinite(mwu_p_value) and mwu_p_value < alpha)
        except Exception:
            pass

    size_breakdown = (
        pair.groupby("file_size_mb", as_index=False)
        .agg(
            ctr_enc_ms=("AES-CTR", "mean"),
            gcm_enc_ms=("AES-GCM", "mean"),
            signed_overhead_pct=("signed_overhead_pct", "mean"),
        )
        .sort_values("file_size_mb")
        .round(3)
    )

    # Merge throughput ratio per size.
    size_tp = (
        df.groupby(["file_size_mb", "mode"], as_index=False)["enc_throughput_mbps"]
        .mean()
        .pivot(index="file_size_mb", columns="mode", values="enc_throughput_mbps")
        .reset_index()
    )
    if {"AES-CTR", "AES-GCM"}.issubset(size_tp.columns):
        size_tp["gcm_to_ctr_tp_ratio"] = size_tp["AES-GCM"] / size_tp["AES-CTR"]
        size_tp = size_tp[["file_size_mb", "gcm_to_ctr_tp_ratio"]]
        size_breakdown = size_breakdown.merge(size_tp, on="file_size_mb", how="left")
        size_breakdown["gcm_to_ctr_tp_ratio"] = size_breakdown["gcm_to_ctr_tp_ratio"].round(3)


    filetype_breakdown = (
        pair.groupby("file_type", as_index=False)
        .agg(
            ctr_enc_ms=("AES-CTR", "mean"),
            gcm_enc_ms=("AES-GCM", "mean"),
            signed_overhead_pct=("signed_overhead_pct", "mean"),
        )
        .round(3)
        .sort_values("file_type")
    )


    size_corr = 0.0
    if not pair.empty and pair["file_size_mb"].nunique() > 1:
        size_corr = float(pair[["file_size_mb", "signed_overhead_pct"]].corr(numeric_only=True).iloc[0, 1])

    conclusions: list[str] = []
    if ratio < 0.95:
        conclusions.append(
            f"AES-CTR is faster overall: GCM throughput is {ratio * 100:.1f}% of CTR on average."
        )
    elif ratio > 1.05:
        conclusions.append(
            f"AES-GCM appears faster overall in this run: throughput ratio is {ratio:.2f}."
        )
    else:
        conclusions.append(
            f"Both modes are close overall: throughput ratio is {ratio:.2f}."
        )

    conclusions.append(
        f"Mean signed overhead is {signed_overhead_mean_pct:.2f}% and clipped overhead is {clipped_overhead_mean_pct:.2f}%."
    )

    if gcm_faster_count > 0 and total_experiments > 0:
        conclusions.append(
            f"GCM was faster in {gcm_faster_count}/{total_experiments} paired experiments, indicating expected runtime variance."
        )

    if size_corr <= -0.2:
        conclusions.append(
            f"Overhead tends to amortize with larger files (corr size vs signed overhead = {size_corr:.2f})."
        )
    elif size_corr >= 0.2:
        conclusions.append(
            f"Overhead increases with size in this run (corr = {size_corr:.2f}); re-run to verify stability."
        )
    else:
        conclusions.append(
            f"No strong size-overhead trend in this run (corr = {size_corr:.2f})."
        )

    conclusions.append(
        f"Timing stability (CV) is CTR {mean_cv_ctr:.2f}% vs GCM {mean_cv_gcm:.2f}%; lower is more stable."
    )


    return BenchmarkSummary(
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        csv_path=csv_path,
        total_rows=int(len(df)),
        total_experiments=total_experiments,
        avg_ctr_enc_ms=avg_ctr_enc_ms,
        avg_gcm_enc_ms=avg_gcm_enc_ms,
        signed_overhead_mean_pct=signed_overhead_mean_pct,
        clipped_overhead_mean_pct=clipped_overhead_mean_pct,
        gcm_to_ctr_throughput_ratio=ratio,
        gcm_faster_count=gcm_faster_count,
        mean_cv_ctr_pct=mean_cv_ctr,
        mean_cv_gcm_pct=mean_cv_gcm,
        welch_t_stat=welch_t_stat,
        welch_df=welch_df,
        welch_p_value=welch_p_value,
        welch_alpha=alpha,
        welch_significant=welch_significant,
        welch_n_ctr=len(ctr_samples),
        welch_n_gcm=len(gcm_samples),
        mwu_stat=mwu_stat,
        mwu_p_value=mwu_p_value,
        mwu_significant=mwu_significant,
        conclusions=conclusions,
        size_breakdown=size_breakdown,
        filetype_breakdown=filetype_breakdown,
    )
