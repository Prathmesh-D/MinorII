"""Tab 5 — Benchmark summary with KPI cards and Welch t-test insights."""

from __future__ import annotations

import platform
import tkinter as tk
from pathlib import Path

from src.benchmark.experiment_config import Config
from src.reporting.benchmark_report import (
    BenchmarkSummary,
    compute_benchmark_summary,
    load_benchmark_dataframe,
)
from src.ui.theme import (
    BG_BASE,
    BG_SURFACE,
    BG_ELEVATED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
    ACCENT_BLUE,
    ACCENT_GREEN,
    ACCENT_ORANGE,
    ACCENT_RED,
    FONT_HEADING,
    FONT_SUBHEAD,
    FONT_BODY,
    FONT_LABEL,
    PAD_LG,
    PAD_MD,
    PAD_SM,
    PAD_XS,
)
from src.ui.components import make_button, make_metric_card, make_section_label


class SummaryTab:
    """Display benchmark KPIs, auto conclusions, and Welch test metrics."""

    def __init__(self, parent: tk.Frame, config: Config,
                 status_var: tk.StringVar, root: tk.Tk,
                 app=None) -> None:
        self.config = config
        self.status_var = status_var
        self.root = root
        self.app = app
        self._csv_path = Path(config.csv_file)
        self._summary: BenchmarkSummary | None = None

        self.frame = tk.Frame(parent, bg=BG_BASE)
        self._build_ui()
        self.load_summary()

    # ================================================================ BUILD
    def _build_ui(self) -> None:
        outer = tk.Frame(self.frame, bg=BG_BASE)
        outer.pack(fill="both", expand=True)

        self._build_header(outer)

        scroll_wrap = tk.Frame(outer, bg=BG_BASE)
        scroll_wrap.pack(fill="both", expand=True, padx=PAD_LG, pady=(0, PAD_MD))

        self._canvas = tk.Canvas(scroll_wrap, bg=BG_BASE, highlightthickness=0)
        self._vscroll = tk.Scrollbar(scroll_wrap, orient="vertical", command=self._canvas.yview,
                                     bg=BG_ELEVATED, troughcolor=BG_BASE,
                                     highlightthickness=0, bd=0)
        self._canvas.configure(yscrollcommand=self._vscroll.set)
        self._vscroll.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self._content = tk.Frame(self._canvas, bg=BG_BASE)
        self._content_id = self._canvas.create_window((0, 0), window=self._content, anchor="nw")

        self._content.bind("<Configure>", self._on_content_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self._canvas.bind("<MouseWheel>", self._on_mousewheel)

        self._kpi_host = tk.Frame(self._content, bg=BG_BASE)
        self._kpi_host.pack(fill="x", pady=(0, PAD_SM))

        make_section_label(self._content, "Auto Conclusions")
        self._conclusion_text = tk.Text(
            self._content,
            height=7,
            bg=BG_SURFACE,
            fg=TEXT_PRIMARY,
            font=FONT_BODY,
            relief="flat",
            bd=0,
            wrap="word",
            highlightthickness=0,
            state="disabled",
            padx=PAD_SM,
            pady=PAD_SM,
        )
        self._conclusion_text.pack(fill="x", pady=(0, PAD_MD))

        make_section_label(self._content, "By File Size")
        self._size_text = tk.Text(
            self._content,
            height=8,
            bg=BG_SURFACE,
            fg=TEXT_PRIMARY,
            font=("Consolas", 9),
            relief="flat",
            bd=0,
            wrap="none",
            highlightthickness=0,
            state="disabled",
            padx=PAD_SM,
            pady=PAD_SM,
        )
        self._size_text.pack(fill="x", pady=(0, PAD_MD))

        make_section_label(self._content, "By File Type")
        self._type_text = tk.Text(
            self._content,
            height=7,
            bg=BG_SURFACE,
            fg=TEXT_PRIMARY,
            font=("Consolas", 9),
            relief="flat",
            bd=0,
            wrap="none",
            highlightthickness=0,
            state="disabled",
            padx=PAD_SM,
            pady=PAD_SM,
        )
        self._type_text.pack(fill="x")

        make_section_label(self._content, "Environment")
        self._env_text = tk.Text(
            self._content,
            height=5,
            bg=BG_SURFACE,
            fg=TEXT_MUTED,
            font=("Consolas", 9),
            relief="flat",
            bd=0,
            wrap="none",
            highlightthickness=0,
            state="disabled",
            padx=PAD_SM,
            pady=PAD_SM,
        )
        self._env_text.pack(fill="x", pady=(0, PAD_MD))
        self._populate_env_block()

        self._bind_scroll_events(self._content)

    def _on_content_configure(self, _event) -> None:
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event) -> None:
        self._canvas.itemconfig(self._content_id, width=event.width)

    def _on_mousewheel(self, event) -> None:
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _bind_scroll_events(self, widget: tk.Widget) -> None:
        widget.bind("<MouseWheel>", self._on_mousewheel)
        for child in widget.winfo_children():
            self._bind_scroll_events(child)

    def _build_header(self, parent: tk.Frame) -> None:
        bar = tk.Frame(parent, bg=BG_BASE)
        bar.pack(fill="x", padx=PAD_LG, pady=PAD_MD)

        left = tk.Frame(bar, bg=BG_BASE)
        left.pack(side="left")

        tk.Label(left, text="Summary", bg=BG_BASE, fg=TEXT_PRIMARY,
                 font=FONT_HEADING).pack(anchor="w")
        self._subtitle = tk.Label(left, text="No CSV loaded", bg=BG_BASE,
                                  fg=TEXT_MUTED, font=FONT_LABEL)
        self._subtitle.pack(anchor="w", pady=(PAD_XS, 0))

        right = tk.Frame(bar, bg=BG_BASE)
        right.pack(side="right")

        make_button(right, text="Refresh",
                    command=self.load_summary, style="ghost").pack(side="left", padx=(0, PAD_SM))

    # ================================================================ LOAD
    def load_summary(self) -> None:
        df = load_benchmark_dataframe(self._csv_path)
        self._summary = compute_benchmark_summary(
            df,
            csv_path=self._csv_path,
            warmup_runs=self.config.warmup_runs,
        )
        self._render_summary(self._summary)

        if df.empty:
            self.status_var.set("Summary: no benchmark data yet")
        else:
            self.status_var.set(
                f"Summary refreshed - {self._summary.total_rows} rows, "
                f"{self._summary.total_experiments} experiments"
            )

    # ================================================================ ENV BLOCK
    def _populate_env_block(self) -> None:
        """Gather system info once on startup and render into the env text box."""
        try:
            from cryptography.hazmat.backends.openssl.backend import backend as _be
            openssl_ver = _be.openssl_version_text()
        except Exception:
            openssl_ver = "unknown"

        try:
            import psutil
            ram_gb = psutil.virtual_memory().total / 1_073_741_824
            ram_str = f"{ram_gb:.1f} GB"
        except ImportError:
            ram_str = "n/a (install psutil)"

        cpu   = platform.processor() or platform.machine() or "unknown"
        py_v  = platform.python_version()
        os_v  = f"{platform.system()} {platform.release()}"
        lines = [
            f"  CPU      : {cpu}",
            f"  RAM      : {ram_str}",
            f"  OS       : {os_v}",
            f"  Python   : {py_v}",
            f"  OpenSSL  : {openssl_ver}",
            f"  Runs     : {self.config.runs}  |  Warmup: {self.config.warmup_runs}  "
            f"|  Groups: {', '.join(self.config.file_groups)}",
        ]
        self._set_text(self._env_text, "\n".join(lines))

    # ================================================================ RENDER
    def _render_summary(self, summary: BenchmarkSummary) -> None:
        self._subtitle.config(
            text=(
                f"CSV: {self._csv_path.name}  |  "
                f"Rows: {summary.total_rows}  |  "
                f"Paired experiments: {summary.total_experiments}"
            )
        )
        self._render_kpis(summary)
        self._set_bulleted_text(self._conclusion_text, summary.conclusions)

        size_text = (
            summary.size_breakdown.to_string(index=False)
            if not summary.size_breakdown.empty
            else "No size breakdown available."
        )
        type_text = (
            summary.filetype_breakdown.to_string(index=False)
            if not summary.filetype_breakdown.empty
            else "No file type breakdown available."
        )
        self._set_text(self._size_text, size_text)
        self._set_text(self._type_text, type_text)

    def _render_kpis(self, summary: BenchmarkSummary) -> None:
        for w in self._kpi_host.winfo_children():
            w.destroy()

        row1 = tk.Frame(self._kpi_host, bg=BG_BASE)
        row1.pack(fill="x")
        row2 = tk.Frame(self._kpi_host, bg=BG_BASE)
        row2.pack(fill="x")

        make_metric_card(
            row1,
            label="CTR Avg Enc",
            value=f"{summary.avg_ctr_enc_ms:.2f}",
            unit="ms",
            color=ACCENT_BLUE,
        )
        make_metric_card(
            row1,
            label="GCM Avg Enc",
            value=f"{summary.avg_gcm_enc_ms:.2f}",
            unit="ms",
            color=ACCENT_BLUE,
        )
        make_metric_card(
            row1,
            label="Signed Overhead",
            value=f"{summary.signed_overhead_mean_pct:+.2f}",
            unit="%",
            color=ACCENT_ORANGE,
        )
        make_metric_card(
            row1,
            label="GCM / CTR TP",
            value=f"{summary.gcm_to_ctr_throughput_ratio:.3f}",
            unit="ratio",
            color=ACCENT_GREEN,
        )

        make_metric_card(
            row2,
            label="GCM Faster Cases",
            value=str(summary.gcm_faster_count),
            unit="pairs",
            color=ACCENT_ORANGE,
        )
        make_metric_card(
            row2,
            label="CTR Stability",
            value=f"{summary.mean_cv_ctr_pct:.2f}",
            unit="CV %",
            color=ACCENT_GREEN,
        )
        make_metric_card(
            row2,
            label="GCM Stability",
            value=f"{summary.mean_cv_gcm_pct:.2f}",
            unit="CV %",
            color=ACCENT_GREEN,
        )
        make_metric_card(
            row2,
            label="Rows",
            value=str(summary.total_rows),
            unit="records",
            color=ACCENT_BLUE,
        )

        self._bind_scroll_events(self._kpi_host)

    @staticmethod
    def _set_text(widget: tk.Text, text: str) -> None:
        widget.config(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.config(state="disabled")

    def _set_bulleted_text(self, widget: tk.Text, items: list[str]) -> None:
        if not items:
            self._set_text(widget, "No conclusions available.")
            return
        text = "\n".join(f"- {item}" for item in items)
        self._set_text(widget, text)

