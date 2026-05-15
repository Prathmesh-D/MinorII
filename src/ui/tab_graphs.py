"""Tab 3 - Graph viewer with matplotlib embedding."""

from __future__ import annotations

import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.image as mpimg

from src.benchmark.experiment_config import Config
from src.visualization.graph_generator import GraphGenerator
from src.ui.theme import (
    BG_BASE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_HEADING, FONT_BODY, FONT_LABEL,
    PAD_LG, PAD_MD, PAD_SM, PAD_XS,
)
from src.ui.components import make_button


# (filename, title, default_tip)
GRAPH_INFO: list[tuple[str, str, str]] = [
    (
        "enc_time_vs_size.png",
        "Encryption Time vs File Size",
        "Use this line chart to read scaling trend: lower points mean faster encryption.",
    ),
    (
        "dec_time_vs_size.png",
        "Decryption Time vs File Size",
        "Use this line chart to compare how decryption latency changes with file size.",
    ),
    (
        "throughput_vs_size.png",
        "Encryption Throughput by Size",
        "Grouped bars are better for direct side-by-side throughput comparison at each size.",
    ),
    (
        "overhead_percent.png",
        "Authentication Overhead",
        "This bar chart isolates the extra work added by GCM authentication over CTR.",
    ),
    (
        "cost_per_mb.png",
        "Cost per MB",
        "Read efficiency independent of file size: lower ms/MB is more efficient.",
    ),
]

_MPL_PARAMS = {
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
}


class GraphsTab:
    """Generate, browse, and export benchmark graphs."""

    def __init__(self, parent: tk.Frame, config: Config,
                 status_var: tk.StringVar, root: tk.Tk,
                 app=None) -> None:
        self.config = config
        self.status_var = status_var
        self.root = root
        self.app = app
        self._graphs_dir = Path(config.graphs_dir)
        self._current_index = 0
        self._available: list[tuple[str, str, str]] = []
        self._canvas_widget: FigureCanvasTkAgg | None = None
        self._insights: dict[str, dict[str, Any]] = {}

        self._graph_title_var = tk.StringVar(value="Graphs")
        self.caption_var = tk.StringVar(value="")
        self._values_var = tk.StringVar(value="")

        self.frame = tk.Frame(parent, bg=BG_BASE)
        self._build_ui()
        self._refresh_insights()
        self._load_available()
        if self._available:
            self._show_graph(0)
        else:
            self._build_placeholder()

    def _build_ui(self) -> None:
        self._build_header()

        self.graph_frame = tk.Frame(self.frame, bg=BG_BASE)
        self.graph_frame.pack(fill="both", expand=True)

        self._graph_canvas_host = tk.Frame(self.graph_frame, bg=BG_BASE)
        self._graph_canvas_host.pack(fill="both", expand=True)

        tip_wrap = tk.Frame(self.graph_frame, bg=BG_BASE)
        tip_wrap.pack(fill="x", padx=PAD_LG, pady=(0, PAD_MD))

        tip_panel = tk.Frame(tip_wrap, bg="#efefea", padx=PAD_MD, pady=PAD_SM)
        tip_panel.pack(fill="x")

        tk.Label(
            tip_panel,
            text="How to Read This Graph",
            bg="#efefea",
            fg=TEXT_MUTED,
            font=FONT_LABEL,
            anchor="w",
        ).pack(fill="x")

        tk.Label(
            tip_panel,
            textvariable=self.caption_var,
            bg="#efefea",
            fg=TEXT_SECONDARY,
            font=FONT_BODY,
            anchor="w",
            justify="left",
            wraplength=980,
        ).pack(fill="x", pady=(PAD_XS, PAD_XS))

        tk.Label(
            tip_panel,
            textvariable=self._values_var,
            bg="#efefea",
            fg=TEXT_PRIMARY,
            font=FONT_LABEL,
            anchor="w",
            justify="left",
            wraplength=980,
        ).pack(fill="x")

    def _build_header(self) -> None:
        bar = tk.Frame(self.frame, bg=BG_BASE)
        bar.pack(fill="x")

        inner = tk.Frame(bar, bg=BG_BASE, padx=PAD_LG, pady=PAD_MD)
        inner.pack(fill="x")

        left = tk.Frame(inner, bg=BG_BASE)
        left.pack(side="left")
        tk.Label(left, textvariable=self._graph_title_var, bg=BG_BASE,
                 fg=TEXT_PRIMARY, font=FONT_HEADING).pack(side="left")

        nav = tk.Frame(inner, bg=BG_BASE)
        nav.pack(side="right")

        self.prev_btn = tk.Label(nav, text="<- prev", bg=BG_BASE,
                                 fg=TEXT_MUTED, font=FONT_LABEL, cursor="hand2")
        self.prev_btn.pack(side="left", padx=(0, PAD_SM))
        self.prev_btn.bind("<Button-1>", lambda _e: self._prev())
        self.prev_btn.bind("<Enter>", lambda _e: self.prev_btn.config(fg=TEXT_PRIMARY))
        self.prev_btn.bind("<Leave>", lambda _e: self.prev_btn.config(fg=TEXT_MUTED))

        self.counter_label = tk.Label(nav, text="0/0", bg=BG_BASE,
                                      fg=TEXT_SECONDARY, font=FONT_LABEL)
        self.counter_label.pack(side="left", padx=(0, PAD_SM))

        self.next_btn = tk.Label(nav, text="next ->", bg=BG_BASE,
                                 fg=TEXT_MUTED, font=FONT_LABEL, cursor="hand2")
        self.next_btn.pack(side="left", padx=(0, PAD_SM))
        self.next_btn.bind("<Button-1>", lambda _e: self._next())
        self.next_btn.bind("<Enter>", lambda _e: self.next_btn.config(fg=TEXT_PRIMARY))
        self.next_btn.bind("<Leave>", lambda _e: self.next_btn.config(fg=TEXT_MUTED))

        self.export_btn = tk.Label(nav, text="Export", bg=BG_BASE,
                                   fg=TEXT_MUTED, font=FONT_LABEL, cursor="hand2")
        self.export_btn.pack(side="left")
        self.export_btn.bind("<Button-1>", lambda _e: self._export_all())
        self.export_btn.bind("<Enter>", lambda _e: self.export_btn.config(fg=TEXT_PRIMARY))
        self.export_btn.bind("<Leave>", lambda _e: self.export_btn.config(fg=TEXT_MUTED))

    def _build_placeholder(self) -> None:
        for w in self._graph_canvas_host.winfo_children():
            w.destroy()
        placeholder = tk.Frame(self._graph_canvas_host, bg=BG_BASE)
        placeholder.pack(expand=True)

        tk.Label(placeholder, text="No graphs yet", bg=BG_BASE,
                 fg=TEXT_MUTED, font=FONT_HEADING).pack()
        tk.Label(placeholder, text="Run the benchmark first, then generate graphs",
                 bg=BG_BASE, fg=TEXT_MUTED, font=FONT_BODY).pack(pady=(PAD_SM, PAD_MD))

        make_button(placeholder, text="Go to Benchmark",
                    command=self._goto_benchmark, style="ghost").pack()

    def refresh_graphs(self) -> None:
        self.status_var.set("Generating graphs...")
        self.root.update_idletasks()

        plt.rcParams.update(_MPL_PARAMS)
        generator = GraphGenerator(self.config)
        generator.generate_all()
        self._insights = generator.build_insights()

        self._load_available()
        if self._available:
            self._show_graph(0)
            self.status_var.set(f"Graphs ready - {len(self._available)} generated")
        else:
            self._build_placeholder()
            self.caption_var.set("")
            self._values_var.set("")
            self.status_var.set("No graphs generated (CSV may be missing)")

    def _refresh_insights(self) -> None:
        self._insights = GraphGenerator(self.config).build_insights()

    @staticmethod
    def _format_values(values: list[str]) -> str:
        if not values:
            return ""
        return "\n".join(f"- {line}" for line in values)

    def _load_available(self) -> None:
        self._available = []
        for fname, label, caption in GRAPH_INFO:
            p = self._graphs_dir / fname
            if p.exists():
                self._available.append((str(p), label, caption))

    def _show_graph(self, index: int) -> None:
        if not self._available:
            return
        index = max(0, min(index, len(self._available) - 1))
        self._current_index = index
        path, label, caption = self._available[index]
        file_name = Path(path).name
        insight = self._insights.get(file_name, {})

        self._graph_title_var.set(label)
        self.counter_label.config(text=f"{index + 1}/{len(self._available)}")

        chart_type = insight.get("chart_type")
        purpose = insight.get("purpose")
        values = insight.get("values") if isinstance(insight.get("values"), list) else []

        if chart_type and purpose:
            self.caption_var.set(f"{chart_type}: {purpose}")
        elif purpose:
            self.caption_var.set(str(purpose))
        else:
            self.caption_var.set(caption)

        self._values_var.set(self._format_values(values))

        for w in self._graph_canvas_host.winfo_children():
            w.destroy()

        img = mpimg.imread(path)
        fig = Figure(figsize=(10, 6), dpi=100, facecolor=BG_BASE)
        ax = fig.add_subplot(111)
        ax.imshow(img)
        ax.axis("off")
        fig.tight_layout(pad=0)

        self._canvas_widget = FigureCanvasTkAgg(fig, master=self._graph_canvas_host)
        self._canvas_widget.draw()
        self._canvas_widget.get_tk_widget().pack(fill="both", expand=True)

    def _prev(self) -> None:
        if self._available and self._current_index > 0:
            self._show_graph(self._current_index - 1)

    def _next(self) -> None:
        if self._available and self._current_index < len(self._available) - 1:
            self._show_graph(self._current_index + 1)

    def _goto_benchmark(self) -> None:
        if self.app is not None:
            self.app.select_tab(1)

    def _export_all(self) -> None:
        dest = filedialog.askdirectory(title="Select export folder")
        if not dest:
            return
        copied = 0
        for fname, _, _ in GRAPH_INFO:
            src = self._graphs_dir / fname
            if src.exists():
                shutil.copy2(src, Path(dest) / fname)
                copied += 1
        self.status_var.set(f"Exported {copied} graph(s) to {dest}")
        messagebox.showinfo("Export", f"Exported {copied} graph(s) to:\n{dest}")
