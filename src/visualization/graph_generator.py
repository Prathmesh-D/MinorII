"""Graph generator — six benchmark comparison charts.

Uses matplotlib + seaborn.  Loads data with pandas from the CSV produced
by :class:`CSVLogger`.

Color convention:
    CTR = #1a1a18 (near-black)
    GCM = #8a8a84 (muted grey)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import matplotlib
matplotlib.use("Agg")  # non-interactive backend — safe for threads / headless

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from src.benchmark.experiment_config import Config

COLOR_CTR = "#1a1a18"
COLOR_GCM = "#8a8a84"
EDGE_CTR = "#f5f5f0"
EDGE_GCM = "#4a4a46"
DPI = 150
BYTES_PER_MB = 1_048_576

_MPL_RC = {
    "figure.facecolor": "#f5f5f0",
    "axes.facecolor": "#efefea",
    "axes.edgecolor": "#c8c8c3",
    "axes.labelcolor": "#4a4a46",
    "xtick.color": "#4a4a46",
    "ytick.color": "#4a4a46",
    "text.color": "#1a1a18",
    "grid.color": "#d8d8d3",
    "grid.linestyle": "--",
    "grid.alpha": 0.7,
    "legend.facecolor": "#e5e5e0",
    "legend.edgecolor": "#c8c8c3",
    "lines.linewidth": 1.5,
    "patch.linewidth": 0.5,
}

GRAPH_FILES = (
    "enc_time_vs_size.png",
    "dec_time_vs_size.png",
    "throughput_vs_size.png",
    "overhead_percent.png",
    "cost_per_mb.png",
    "signed_overhead_percent.png",
)


class GraphGenerator:
    """Generate benchmark comparison graphs from CSV results."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._csv_path = Path(config.csv_file)
        self._graphs_dir = Path(config.graphs_dir)
        self._graphs_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Data preparation
    # ------------------------------------------------------------------

    @staticmethod
    def _load_dataframe(csv_file: Path) -> pd.DataFrame:
        if not csv_file.exists():
            return pd.DataFrame()

        df = pd.read_csv(csv_file)
        if df.empty:
            return df

        numeric_cols = [
            "file_size_mb",
            "avg_enc_time_ms",
            "avg_dec_time_ms",
            "enc_throughput_mbps",
            "overhead_percent",
            "cost_per_mb_enc",
            "std_dev_enc_ns",
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        if "mode" in df.columns:
            df["mode"] = df["mode"].astype(str)
        if "file_group" in df.columns:
            df["file_group"] = df["file_group"].astype(str)
        if "file_type" in df.columns:
            df["file_type"] = df["file_type"].astype(str)

        return df

    @staticmethod
    def _sorted_sizes(df: pd.DataFrame) -> list[float]:
        if "file_size_mb" not in df.columns:
            return []
        vals = sorted(v for v in df["file_size_mb"].dropna().unique())
        return [float(v) for v in vals]

    @staticmethod
    def _sort_groups_by_size(df: pd.DataFrame) -> list[str]:
        if "file_group" not in df.columns or "file_size_mb" not in df.columns:
            return []
        tmp = (
            df.groupby("file_group", as_index=False)["file_size_mb"]
            .mean()
            .sort_values("file_size_mb")
        )
        return tmp["file_group"].tolist()

    @staticmethod
    def _mode_size_metric(df: pd.DataFrame, metric: str) -> pd.DataFrame:
        if metric not in df.columns:
            return pd.DataFrame()
        out = (
            df.groupby(["mode", "file_size_mb"], as_index=False)[metric]
            .mean()
            .sort_values(["mode", "file_size_mb"])
        )
        return out

    @staticmethod
    def _annotate_line_points(
        ax: plt.Axes,
        x_values: list[float],
        y_values: list[float],
        color: str,
        precision: int,
    ) -> None:
        for x, y in zip(x_values, y_values):
            ax.annotate(
                f"{y:.{precision}f}",
                xy=(x, y),
                xytext=(0, 7),
                textcoords="offset points",
                ha="center",
                fontsize=8,
                color=color,
            )

    @staticmethod
    def _annotate_bars(
        ax: plt.Axes,
        bars: Any,
        precision: int = 2,
        suffix: str = "",
    ) -> None:
        for bar in bars:
            height = float(bar.get_height())
            ax.annotate(
                f"{height:.{precision}f}{suffix}",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                fontsize=8,
            )

    @staticmethod
    def _safe_pct(numerator: float, denominator: float) -> float:
        if denominator <= 0:
            return 0.0
        return ((numerator - denominator) / denominator) * 100.0

    @staticmethod
    def _parse_raw_ns(cell: Any) -> list[float]:
        if cell is None:
            return []
        text = str(cell).strip()
        if not text or text.lower() == "nan":
            return []
        values: list[float] = []
        for item in text.split("|"):
            item = item.strip()
            if not item:
                continue
            try:
                values.append(float(item))
            except ValueError:
                continue
        return values

    @staticmethod
    def _ci95_half_width(values: list[float]) -> float:
        if len(values) < 2:
            return 0.0
        std = float(np.std(values, ddof=1))
        return 1.96 * (std / np.sqrt(len(values)))

    def _kept_ns(self, raw_cell: Any, fallback_ns: float) -> list[float]:
        raw = self._parse_raw_ns(raw_cell)
        kept = raw[self._config.warmup_runs:] if len(raw) > self._config.warmup_runs else raw
        if kept:
            return kept
        if fallback_ns > 0:
            return [fallback_ns]
        return []

    def _build_sample_frame(self, df: pd.DataFrame) -> pd.DataFrame:
        samples: list[dict[str, Any]] = []

        for _, row in df.iterrows():
            mode = str(row.get("mode", ""))
            if not mode:
                continue

            file_size_bytes = float(row.get("file_size_bytes", 0) or 0)
            file_size_mb = float(row.get("file_size_mb", 0) or 0)
            if file_size_mb <= 0 and file_size_bytes > 0:
                file_size_mb = file_size_bytes / BYTES_PER_MB

            enc_kept = self._kept_ns(
                row.get("raw_enc_times_ns"),
                float(row.get("avg_enc_time_ns", 0) or 0),
            )
            dec_kept = self._kept_ns(
                row.get("raw_dec_times_ns"),
                float(row.get("avg_dec_time_ns", 0) or 0),
            )
            run_count = min(len(enc_kept), len(dec_kept))
            if run_count == 0:
                continue

            for i in range(run_count):
                enc_ns = enc_kept[i]
                dec_ns = dec_kept[i]
                enc_ms = enc_ns / 1_000_000
                dec_ms = dec_ns / 1_000_000

                enc_tp = 0.0
                cost_per_mb = 0.0
                if enc_ns > 0 and file_size_bytes > 0:
                    enc_tp = (file_size_bytes / BYTES_PER_MB) / (enc_ns / 1_000_000_000)
                if file_size_mb > 0:
                    cost_per_mb = enc_ms / file_size_mb

                samples.append(
                    {
                        "mode": mode,
                        "file_group": str(row.get("file_group", "")),
                        "file_type": str(row.get("file_type", "")),
                        "file_size_mb": file_size_mb,
                        "enc_ms": enc_ms,
                        "dec_ms": dec_ms,
                        "enc_throughput_mbps": enc_tp,
                        "cost_per_mb_enc": cost_per_mb,
                    }
                )

        return pd.DataFrame(samples)

    def _build_overhead_samples(self, df: pd.DataFrame) -> pd.DataFrame:
        if "mode" not in df.columns:
            return pd.DataFrame()

        samples: list[dict[str, Any]] = []
        key_cols = ["timestamp", "file_group", "file_type", "file_size_mb", "file_size_bytes"]
        available_keys = [c for c in key_cols if c in df.columns]
        if not available_keys:
            available_keys = ["file_group", "file_type", "file_size_mb", "file_size_bytes"]
            available_keys = [c for c in available_keys if c in df.columns]

        if available_keys:
            grouped = df.groupby(available_keys, dropna=False)
            for _, pair in grouped:
                ctr_rows = pair[pair["mode"] == "AES-CTR"]
                gcm_rows = pair[pair["mode"] == "AES-GCM"]
                if ctr_rows.empty or gcm_rows.empty:
                    continue

                ctr_row = ctr_rows.iloc[0]
                gcm_row = gcm_rows.iloc[0]
                ctr_kept = self._kept_ns(
                    ctr_row.get("raw_enc_times_ns"),
                    float(ctr_row.get("avg_enc_time_ns", 0) or 0),
                )
                gcm_kept = self._kept_ns(
                    gcm_row.get("raw_enc_times_ns"),
                    float(gcm_row.get("avg_enc_time_ns", 0) or 0),
                )

                for ctr_ns, gcm_ns in zip(ctr_kept, gcm_kept):
                    if ctr_ns <= 0:
                        continue
                    pct = ((gcm_ns - ctr_ns) / ctr_ns) * 100.0
                    samples.append(
                        {
                            "file_group": str(gcm_row.get("file_group", "")),
                            "file_size_mb": float(gcm_row.get("file_size_mb", 0) or 0),
                            "overhead_percent": max(0.0, pct),
                        }
                    )

        if samples:
            return pd.DataFrame(samples)

        gcm = df[df["mode"] == "AES-GCM"]
        if gcm.empty or "overhead_percent" not in gcm.columns:
            return pd.DataFrame()
        return gcm[["file_group", "file_size_mb", "overhead_percent"]].copy()

    def _aggregate_with_ci(
        self,
        sample_df: pd.DataFrame,
        group_cols: list[str],
        value_col: str,
    ) -> pd.DataFrame:
        if sample_df.empty or value_col not in sample_df.columns:
            return pd.DataFrame()

        grouped = (
            sample_df.groupby(group_cols, as_index=False)[value_col]
            .apply(list)
            .rename(columns={value_col: "_values"})
        )
        grouped["mean"] = grouped["_values"].apply(
            lambda vals: float(np.mean(vals)) if vals else 0.0
        )
        grouped["ci95"] = grouped["_values"].apply(self._ci95_half_width)
        grouped["n"] = grouped["_values"].apply(len)
        return grouped.drop(columns=["_values"])

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_all(
        self,
        csv_path: Optional[str] = None,
        output_dir: Optional[str] = None,
    ) -> list[str]:
        """Generate all six graphs and return list of saved file paths.

        When called without arguments the paths from *config.ini* are
        used (keeps backward-compat with ``main.py``).
        """
        csv_file = Path(csv_path) if csv_path else self._csv_path
        out_dir = Path(output_dir) if output_dir else self._graphs_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        df = self._load_dataframe(csv_file)
        if df.empty:
            return []

        sns.set_theme(style="whitegrid")
        plt.rcParams.update(_MPL_RC)

        saved: list[str] = []
        generators = [
            self._enc_time_vs_size,
            self._dec_time_vs_size,
            self._throughput_vs_size,
            self._overhead_percent,
            self._cost_per_mb,
            self._signed_overhead_percent,
        ]
        for gen_fn in generators:
            path = gen_fn(df, out_dir)
            if path:
                saved.append(path)

        return saved

    def build_insights(self, csv_path: Optional[str] = None) -> dict[str, dict[str, Any]]:
        """Return short per-graph tips with concrete values from the CSV."""
        csv_file = Path(csv_path) if csv_path else self._csv_path
        df = self._load_dataframe(csv_file)
        if df.empty:
            return {}

        return {
            "enc_time_vs_size.png": self._insight_enc_time(df),
            "dec_time_vs_size.png": self._insight_dec_time(df),
            "throughput_vs_size.png": self._insight_throughput(df),
            "overhead_percent.png": self._insight_overhead(df),
            "cost_per_mb.png": self._insight_cost(df),
            "signed_overhead_percent.png": self._insight_signed_overhead(df),
        }

    # ------------------------------------------------------------------
    # Individual chart builders
    # ------------------------------------------------------------------

    @staticmethod
    def _save(fig, out_dir: Path, name: str) -> str:
        path = out_dir / name
        fig.savefig(path, dpi=DPI, bbox_inches="tight")
        plt.close(fig)
        return str(path)

    # 1 ----------------------------------------------------------------
    def _enc_time_vs_size(self, df: pd.DataFrame, out_dir: Path) -> str:
        samples = self._build_sample_frame(df)
        data = self._aggregate_with_ci(samples, ["mode", "file_size_mb"], "enc_ms")
        if data.empty:
            return ""

        fig, ax = plt.subplots(figsize=(9, 5.2))
        for mode, color in [("AES-CTR", COLOR_CTR), ("AES-GCM", COLOR_GCM)]:
            sub = data[data["mode"] == mode].sort_values("file_size_mb")
            if sub.empty:
                continue
            x_vals = sub["file_size_mb"].tolist()
            y_vals = sub["mean"].tolist()
            y_err = sub["ci95"].tolist()
            ax.errorbar(
                x_vals,
                y_vals,
                yerr=y_err,
                fmt="-o",
                capsize=4,
                color=color,
                label=mode,
            )
            self._annotate_line_points(ax, x_vals, y_vals, color=color, precision=2)

        ax.set_title("Encryption Time vs File Size (95% CI)")
        ax.set_xlabel("File Size (MB)")
        ax.set_ylabel("Avg Encryption Time (ms)")
        ax.set_xticks(self._sorted_sizes(df))
        ax.legend()
        ax.grid(True, axis="y")
        return self._save(fig, out_dir, "enc_time_vs_size.png")

    # 2 ----------------------------------------------------------------
    def _dec_time_vs_size(self, df: pd.DataFrame, out_dir: Path) -> str:
        samples = self._build_sample_frame(df)
        data = self._aggregate_with_ci(samples, ["mode", "file_size_mb"], "dec_ms")
        if data.empty:
            return ""

        fig, ax = plt.subplots(figsize=(9, 5.2))
        for mode, color in [("AES-CTR", COLOR_CTR), ("AES-GCM", COLOR_GCM)]:
            sub = data[data["mode"] == mode].sort_values("file_size_mb")
            if sub.empty:
                continue
            x_vals = sub["file_size_mb"].tolist()
            y_vals = sub["mean"].tolist()
            y_err = sub["ci95"].tolist()
            ax.errorbar(
                x_vals,
                y_vals,
                yerr=y_err,
                fmt="-o",
                capsize=4,
                color=color,
                label=mode,
            )
            self._annotate_line_points(ax, x_vals, y_vals, color=color, precision=2)

        ax.set_title("Decryption Time vs File Size (95% CI)")
        ax.set_xlabel("File Size (MB)")
        ax.set_ylabel("Avg Decryption Time (ms)")
        ax.set_xticks(self._sorted_sizes(df))
        ax.legend()
        ax.grid(True, axis="y")
        return self._save(fig, out_dir, "dec_time_vs_size.png")

    # 3 ----------------------------------------------------------------
    def _throughput_vs_size(self, df: pd.DataFrame, out_dir: Path) -> str:
        samples = self._build_sample_frame(df)
        data = self._aggregate_with_ci(samples, ["mode", "file_size_mb"], "enc_throughput_mbps")
        if data.empty:
            return ""

        pivot = data.pivot(index="file_size_mb", columns="mode", values="mean").sort_index()
        ci_pivot = data.pivot(index="file_size_mb", columns="mode", values="ci95").sort_index()
        if pivot.empty:
            return ""

        x = np.arange(len(pivot.index))
        width = 0.36

        fig, ax = plt.subplots(figsize=(9, 5.2))

        if "AES-CTR" in pivot.columns:
            bars_ctr = ax.bar(
                x - width / 2,
                pivot["AES-CTR"],
                width,
                label="AES-CTR",
                color=COLOR_CTR,
                edgecolor=EDGE_CTR,
                yerr=ci_pivot["AES-CTR"] if "AES-CTR" in ci_pivot.columns else None,
                capsize=4,
            )
            self._annotate_bars(ax, bars_ctr, precision=1)

        if "AES-GCM" in pivot.columns:
            bars_gcm = ax.bar(
                x + width / 2,
                pivot["AES-GCM"],
                width,
                label="AES-GCM",
                color=COLOR_GCM,
                edgecolor=EDGE_GCM,
                hatch="//",
                yerr=ci_pivot["AES-GCM"] if "AES-GCM" in ci_pivot.columns else None,
                capsize=4,
            )
            self._annotate_bars(ax, bars_gcm, precision=1)

        ax.set_title("Encryption Throughput Comparison by File Size (95% CI)")
        ax.set_xlabel("File Size (MB)")
        ax.set_ylabel("Throughput (MB/s)")
        ax.set_xticks(x)
        ax.set_xticklabels([f"{size:g}" for size in pivot.index])
        ax.legend()
        ax.grid(True, axis="y")
        return self._save(fig, out_dir, "throughput_vs_size.png")

    # 4 ----------------------------------------------------------------
    def _overhead_percent(self, df: pd.DataFrame, out_dir: Path) -> str:
        samples = self._build_overhead_samples(df)
        if samples.empty:
            return ""

        grouped = self._aggregate_with_ci(
            samples,
            ["file_group", "file_size_mb"],
            "overhead_percent",
        ).sort_values("file_size_mb")
        labels = [f"{grp}\n({size:g} MB)" for grp, size in zip(grouped["file_group"], grouped["file_size_mb"])]

        fig, ax = plt.subplots(figsize=(9, 5.2))
        bars = ax.bar(
            labels,
            grouped["mean"],
            color=COLOR_GCM,
            edgecolor=EDGE_GCM,
            hatch="//",
            width=0.55,
            yerr=grouped["ci95"],
            capsize=4,
        )
        ax.axhline(y=0, color="grey", linestyle="--", linewidth=0.8)
        ax.set_title("Authentication Overhead by File Size Group (95% CI)")
        ax.set_xlabel("File Group")
        ax.set_ylabel("Overhead %")
        self._annotate_bars(ax, bars, precision=1, suffix="%")
        ax.tick_params(axis="x", rotation=0)
        ax.grid(True, axis="y")
        return self._save(fig, out_dir, "overhead_percent.png")

    # 5 ----------------------------------------------------------------
    def _cost_per_mb(self, df: pd.DataFrame, out_dir: Path) -> str:
        samples = self._build_sample_frame(df)
        data = self._aggregate_with_ci(samples, ["mode", "file_size_mb"], "cost_per_mb_enc")
        if data.empty:
            return ""

        pivot = data.pivot(index="file_size_mb", columns="mode", values="mean").sort_index()
        ci_pivot = data.pivot(index="file_size_mb", columns="mode", values="ci95").sort_index()
        if pivot.empty:
            return ""

        fig, ax = plt.subplots(figsize=(9, 5.2))
        x = np.arange(len(pivot.index))
        width = 0.35

        if "AES-CTR" in pivot.columns:
            bars_ctr = ax.bar(
                x - width / 2,
                pivot["AES-CTR"],
                width,
                label="AES-CTR",
                color=COLOR_CTR,
                edgecolor=EDGE_CTR,
                yerr=ci_pivot["AES-CTR"] if "AES-CTR" in ci_pivot.columns else None,
                capsize=4,
            )
            self._annotate_bars(ax, bars_ctr, precision=3)

        if "AES-GCM" in pivot.columns:
            bars_gcm = ax.bar(
                x + width / 2,
                pivot["AES-GCM"],
                width,
                label="AES-GCM",
                color=COLOR_GCM,
                edgecolor=EDGE_GCM,
                hatch="//",
                yerr=ci_pivot["AES-GCM"] if "AES-GCM" in ci_pivot.columns else None,
                capsize=4,
            )
            self._annotate_bars(ax, bars_gcm, precision=3)

        ax.set_xticks(list(x))
        ax.set_xticklabels([f"{size:g}" for size in pivot.index])
        ax.set_title("Encryption Cost per MB by File Size (95% CI)")
        ax.set_xlabel("File Size (MB)")
        ax.set_ylabel("Cost per MB (ms/MB)")
        ax.legend()
        ax.grid(True, axis="y")
        return self._save(fig, out_dir, "cost_per_mb.png")

    # 6 ----------------------------------------------------------------
    def _variance_by_filetype(self, df: pd.DataFrame, out_dir: Path) -> str:
        if "std_dev_enc_ns" not in df.columns:
            return ""

        pivot = df.pivot_table(
            index="file_type",
            columns="file_group",
            values="std_dev_enc_ns",
            aggfunc="mean",
        )
        if pivot.empty:
            return ""

        ordered_groups = self._sort_groups_by_size(df)
        if ordered_groups:
            pivot = pivot.reindex(columns=ordered_groups)
        pivot = pivot.fillna(0.0)

        fig, ax = plt.subplots(figsize=(9.2, 5.2))
        sns.heatmap(
            pivot,
            cmap=sns.color_palette("Greys", as_cmap=True),
            annot=True,
            fmt=".0f",
            linewidths=0.5,
            linecolor="#d8d8d3",
            cbar_kws={"label": "Std Dev (ns)"},
            ax=ax,
        )
        ax.set_title("Encryption Time Variability Heatmap")
        ax.set_xlabel("File Group")
        ax.set_ylabel("File Type")
        return self._save(fig, out_dir, "variance_by_filetype.png")

    # ------------------------------------------------------------------
    # Insight builders for Graphs tab
    # ------------------------------------------------------------------

    def _insight_enc_time(self, df: pd.DataFrame) -> dict[str, Any]:
        metric = "avg_enc_time_ms"
        data = self._mode_size_metric(df, metric)
        if data.empty:
            return {"chart_type": "Line chart", "purpose": "Encryption trend by size", "values": []}

        fastest = data.loc[data[metric].idxmin()]
        slowest = data.loc[data[metric].idxmax()]
        largest_size = float(data["file_size_mb"].max())
        largest_slice = data[data["file_size_mb"] == largest_size].set_index("mode")
        gap_txt = "Not enough mode data at largest size."
        if {"AES-CTR", "AES-GCM"}.issubset(largest_slice.index):
            ctr_val = float(largest_slice.loc["AES-CTR", metric])
            gcm_val = float(largest_slice.loc["AES-GCM", metric])
            gap = self._safe_pct(gcm_val, ctr_val)
            gap_txt = f"At {largest_size:g} MB: CTR {ctr_val:.2f} ms vs GCM {gcm_val:.2f} ms ({gap:+.1f}%)."

        return {
            "chart_type": "Line chart",
            "purpose": "Shows timing trend as file size grows; error bars show 95% confidence intervals.",
            "values": [
                f"Fastest point: {fastest['mode']} at {float(fastest['file_size_mb']):g} MB = {float(fastest[metric]):.2f} ms.",
                f"Slowest point: {slowest['mode']} at {float(slowest['file_size_mb']):g} MB = {float(slowest[metric]):.2f} ms.",
                gap_txt,
            ],
        }

    def _insight_dec_time(self, df: pd.DataFrame) -> dict[str, Any]:
        metric = "avg_dec_time_ms"
        data = self._mode_size_metric(df, metric)
        if data.empty:
            return {"chart_type": "Line chart", "purpose": "Decryption trend by size", "values": []}

        fastest = data.loc[data[metric].idxmin()]
        slowest = data.loc[data[metric].idxmax()]
        mean_by_mode = data.groupby("mode", as_index=False)[metric].mean()
        mode_values = ", ".join(
            f"{row['mode']} {float(row[metric]):.2f} ms"
            for _, row in mean_by_mode.iterrows()
        )

        return {
            "chart_type": "Line chart",
            "purpose": "Compares decryption scaling for CTR and GCM with 95% CI error bars.",
            "values": [
                f"Fastest point: {fastest['mode']} at {float(fastest['file_size_mb']):g} MB = {float(fastest[metric]):.2f} ms.",
                f"Slowest point: {slowest['mode']} at {float(slowest['file_size_mb']):g} MB = {float(slowest[metric]):.2f} ms.",
                f"Average across sizes: {mode_values}.",
            ],
        }

    def _insight_throughput(self, df: pd.DataFrame) -> dict[str, Any]:
        metric = "enc_throughput_mbps"
        data = self._mode_size_metric(df, metric)
        if data.empty:
            return {"chart_type": "Grouped bar chart", "purpose": "Throughput by size", "values": []}

        best = data.loc[data[metric].idxmax()]
        mean_by_mode = data.groupby("mode", as_index=False)[metric].mean()
        mode_values = ", ".join(
            f"{row['mode']} {float(row[metric]):.1f} MB/s"
            for _, row in mean_by_mode.iterrows()
        )

        largest_size = float(data["file_size_mb"].max())
        largest_slice = data[data["file_size_mb"] == largest_size].set_index("mode")
        diff_txt = "Not enough mode data at largest size."
        if {"AES-CTR", "AES-GCM"}.issubset(largest_slice.index):
            ctr_val = float(largest_slice.loc["AES-CTR", metric])
            gcm_val = float(largest_slice.loc["AES-GCM", metric])
            diff_txt = (
                f"At {largest_size:g} MB: CTR {ctr_val:.1f} MB/s vs GCM {gcm_val:.1f} MB/s "
                f"(delta {gcm_val - ctr_val:+.1f} MB/s)."
            )

        return {
            "chart_type": "Grouped bar chart",
            "purpose": "Best for direct mode-to-mode comparison at each size; bars include 95% CI.",
            "values": [
                f"Highest throughput: {best['mode']} at {float(best['file_size_mb']):g} MB = {float(best[metric]):.1f} MB/s.",
                f"Mean throughput by mode: {mode_values}.",
                diff_txt,
            ],
        }

    def _insight_overhead(self, df: pd.DataFrame) -> dict[str, Any]:
        gcm = df[df["mode"] == "AES-GCM"].copy()
        if gcm.empty or "overhead_percent" not in gcm.columns:
            return {"chart_type": "Bar chart", "purpose": "Authentication overhead per size", "values": []}

        grouped = (
            gcm.groupby(["file_group", "file_size_mb"], as_index=False)["overhead_percent"]
            .mean()
            .sort_values("file_size_mb")
        )
        if grouped.empty:
            return {"chart_type": "Bar chart", "purpose": "Authentication overhead per size", "values": []}

        peak = grouped.loc[grouped["overhead_percent"].idxmax()]
        low = grouped.loc[grouped["overhead_percent"].idxmin()]
        avg = float(grouped["overhead_percent"].mean())

        return {
            "chart_type": "Bar chart",
            "purpose": "Shows extra encryption cost of GCM authentication over CTR with 95% CI.",
            "values": [
                f"Highest overhead: {peak['file_group']} ({float(peak['file_size_mb']):g} MB) = {float(peak['overhead_percent']):.1f}%.",
                f"Lowest overhead: {low['file_group']} ({float(low['file_size_mb']):g} MB) = {float(low['overhead_percent']):.1f}%.",
                f"Average overhead across sizes: {avg:.1f}%.",
            ],
        }

    def _insight_cost(self, df: pd.DataFrame) -> dict[str, Any]:
        metric = "cost_per_mb_enc"
        data = self._mode_size_metric(df, metric)
        if data.empty:
            return {"chart_type": "Grouped bar chart", "purpose": "Efficiency by MB", "values": []}

        mean_by_mode = data.groupby("mode", as_index=False)[metric].mean()
        mode_values = ", ".join(
            f"{row['mode']} {float(row[metric]):.3f} ms/MB"
            for _, row in mean_by_mode.iterrows()
        )

        worst = data.loc[data[metric].idxmax()]

        return {
            "chart_type": "Grouped bar chart",
            "purpose": "Normalizes encryption time by data size for fair efficiency comparison with 95% CI.",
            "values": [
                f"Average cost by mode: {mode_values}.",
                f"Most expensive point: {worst['mode']} at {float(worst['file_size_mb']):g} MB = {float(worst[metric]):.3f} ms/MB.",
                "Lower bars indicate better per-MB efficiency.",
            ],
        }

    def _insight_variance(self, df: pd.DataFrame) -> dict[str, Any]:
        if "std_dev_enc_ns" not in df.columns:
            return {"chart_type": "Heatmap", "purpose": "Stability map", "values": []}

        data = (
            df.groupby(["file_type", "file_group"], as_index=False)["std_dev_enc_ns"]
            .mean()
        )
        if data.empty:
            return {"chart_type": "Heatmap", "purpose": "Stability map", "values": []}

        low = data.loc[data["std_dev_enc_ns"].idxmin()]
        high = data.loc[data["std_dev_enc_ns"].idxmax()]
        avg_by_type = data.groupby("file_type", as_index=False)["std_dev_enc_ns"].mean()
        stable_type = avg_by_type.loc[avg_by_type["std_dev_enc_ns"].idxmin()]

        return {
            "chart_type": "Heatmap",
            "purpose": "Compares timing stability by file type (rows) and size group (columns).",
            "values": [
                f"Most stable cell: {low['file_type']} in {low['file_group']} = {float(low['std_dev_enc_ns']):.0f} ns.",
                f"Most variable cell: {high['file_type']} in {high['file_group']} = {float(high['std_dev_enc_ns']):.0f} ns.",
                f"Most stable file type overall: {stable_type['file_type']} ({float(stable_type['std_dev_enc_ns']):.0f} ns average).",
            ],
        }

    # 7 ----------------------------------------------------------------
    def _signed_overhead_percent(self, df: pd.DataFrame, out_dir: Path) -> str:
        """Bar chart of signed overhead % (can go negative) with CI error bars."""
        if "mode" not in df.columns:
            return ""

        samples: list[dict] = []
        key_cols = [c for c in ["timestamp", "file_group", "file_type", "file_size_mb"] if c in df.columns]
        if not key_cols:
            return ""

        for _, pair in df.groupby(key_cols, dropna=False):
            ctr_rows = pair[pair["mode"] == "AES-CTR"]
            gcm_rows = pair[pair["mode"] == "AES-GCM"]
            if ctr_rows.empty or gcm_rows.empty:
                continue

            ctr_row = ctr_rows.iloc[0]
            gcm_row = gcm_rows.iloc[0]
            ctr_kept = self._kept_ns(
                ctr_row.get("raw_enc_times_ns"),
                float(ctr_row.get("avg_enc_time_ns", 0) or 0),
            )
            gcm_kept = self._kept_ns(
                gcm_row.get("raw_enc_times_ns"),
                float(gcm_row.get("avg_enc_time_ns", 0) or 0),
            )

            for ctr_ns, gcm_ns in zip(ctr_kept, gcm_kept):
                if ctr_ns <= 0:
                    continue
                signed_pct = ((gcm_ns - ctr_ns) / ctr_ns) * 100.0
                samples.append({
                    "file_group": str(gcm_row.get("file_group", "")),
                    "file_size_mb": float(gcm_row.get("file_size_mb", 0) or 0),
                    "signed_overhead_pct": signed_pct,
                })

        if not samples:
            return ""

        sdf = pd.DataFrame(samples)
        grouped = self._aggregate_with_ci(
            sdf, ["file_group", "file_size_mb"], "signed_overhead_pct"
        ).sort_values("file_size_mb")

        if grouped.empty:
            return ""

        labels = [
            f"{grp}\n({size:g} MB)"
            for grp, size in zip(grouped["file_group"], grouped["file_size_mb"])
        ]
        means = grouped["mean"].tolist()
        ci95  = grouped["ci95"].tolist()
        colors = [COLOR_GCM if v >= 0 else "#6a6a6a" for v in means]

        fig, ax = plt.subplots(figsize=(9, 5.2))
        bars = ax.bar(
            labels, means,
            color=colors,
            edgecolor=EDGE_GCM,
            hatch="//",
            width=0.55,
            yerr=ci95,
            capsize=4,
        )
        ax.axhline(y=0, color="grey", linestyle="--", linewidth=0.9)
        ax.set_title("Signed Authentication Overhead by File Size Group (95% CI)")
        ax.set_xlabel("File Group")
        ax.set_ylabel("Signed Overhead %  (negative = GCM faster)")
        self._annotate_bars(ax, bars, precision=1, suffix="%")
        ax.tick_params(axis="x", rotation=0)
        ax.grid(True, axis="y")
        return self._save(fig, out_dir, "signed_overhead_percent.png")

    def _insight_signed_overhead(self, df: pd.DataFrame) -> dict:
        """Insight for the signed overhead chart."""
        if "mode" not in df.columns:
            return {"chart_type": "Bar chart", "purpose": "Signed overhead", "values": []}

        # Quick aggregate from avg columns as approximation for insight text
        keys = ["file_group", "file_size_mb"]
        ctr = df[df["mode"] == "AES-CTR"].groupby(keys, as_index=False)["avg_enc_time_ms"].mean()
        gcm = df[df["mode"] == "AES-GCM"].groupby(keys, as_index=False)["avg_enc_time_ms"].mean()
        if ctr.empty or gcm.empty:
            return {"chart_type": "Bar chart", "purpose": "Signed overhead", "values": []}

        merged = ctr.merge(gcm, on=keys, suffixes=("_ctr", "_gcm"))
        if merged.empty:
            return {"chart_type": "Bar chart", "purpose": "Signed overhead", "values": []}

        merged["signed_pct"] = (
            (merged["avg_enc_time_ms_gcm"] - merged["avg_enc_time_ms_ctr"])
            / merged["avg_enc_time_ms_ctr"]
        ) * 100.0

        neg_count = int((merged["signed_pct"] < 0).sum())
        mean_pct  = float(merged["signed_pct"].mean())
        peak_row  = merged.loc[merged["signed_pct"].idxmax()]

        return {
            "chart_type": "Bar chart",
            "purpose": "Shows signed overhead — bars below zero mean GCM was faster in that group. Unlike the clipped chart, negatives are visible.",
            "values": [
                f"Mean signed overhead across all groups: {mean_pct:+.2f}%.",
                f"Groups where GCM was faster (negative overhead): {neg_count}.",
                f"Highest overhead: {peak_row['file_group']} = {float(peak_row['signed_pct']):+.1f}%.",
            ],
        }
