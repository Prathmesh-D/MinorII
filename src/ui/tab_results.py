"""Tab 4 — Results table with filtering and sorting."""

from __future__ import annotations

import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

import pandas as pd

from src.benchmark.experiment_config import Config
from src.ui.theme import (
    BG_BASE, BG_SURFACE, BG_ELEVATED, BORDER,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    ACCENT_BLUE, ACCENT_RED, ACCENT_PURPLE,
    FONT_HEADING, FONT_BODY, FONT_LABEL,
    PAD_LG, PAD_MD, PAD_SM, PAD_XS,
)
from src.ui.components import make_button

# Columns: (csv_col, heading, width)
DISPLAY_COLS: list[tuple[str, str, int]] = [
    ("timestamp",           "Timestamp",   130),
    ("file_group",          "Group",        90),
    ("file_type",           "Type",         70),
    ("mode",                "Mode",         60),
    ("file_size_mb",        "Size MB",      70),
    ("avg_enc_time_ms",     "Enc ms",       80),
    ("avg_dec_time_ms",     "Dec ms",       80),
    ("enc_throughput_mbps", "Throughput",    90),
    ("overhead_percent",    "Overhead %",   90),
    ("cost_per_mb_enc",     "Cost/MB",      80),
]

_EMPTY_ICON = "\U0001F4CB"
_EMPTY_TITLE = "No Results Yet"
_EMPTY_SUBTITLE = "Run a benchmark first, then come back here to view the data table."


class ResultsTab:
    """Load, filter, sort, and export benchmark CSV results."""

    def __init__(self, parent: tk.Frame, config: Config,
                 status_var: tk.StringVar, root: tk.Tk) -> None:
        self.config = config
        self.status_var = status_var
        self.root = root
        self._csv_path = Path(config.csv_file)
        self._df: pd.DataFrame = pd.DataFrame()
        self._filtered: pd.DataFrame = pd.DataFrame()
        self._sort_col: str = ""
        self._sort_asc: bool = True
        self._mode_options = ["AES-CTR", "AES-GCM", "All"]
        self._mode_idx = 0
        self._group_options = ["All"]
        self._group_idx = 0

        self.frame = tk.Frame(parent, bg=BG_BASE)
        self._build_ui()

    # ================================================================ BUILD
    def _build_ui(self) -> None:
        # ── Top bar ──
        self._build_top_bar()

        # Container for table + empty overlay (stacked via place)
        self._table_container = tk.Frame(self.frame, bg=BG_BASE)
        self._table_container.pack(fill="both", expand=True)

        # ── Table ──
        self._build_table()

        # ── Empty state overlay (shown by default) ──
        self._build_empty_state()

        # ── Summary bar (at bottom) ──
        self._build_summary_bar()

    # ========================================================== TOP BAR
    def _build_top_bar(self) -> None:
        bar = tk.Frame(self.frame, bg=BG_BASE)
        bar.pack(fill="x")

        inner = tk.Frame(bar, bg=BG_BASE, padx=PAD_LG, pady=PAD_MD)
        inner.pack(fill="x")

        # Left: result count
        left = tk.Frame(inner, bg=BG_BASE)
        left.pack(side="left")
        self._results_count_lbl = tk.Label(left, text="0 results", bg=BG_BASE,
                                           fg=TEXT_MUTED, font=FONT_LABEL)
        self._results_count_lbl.pack(side="left")

        # Right: filter controls
        right = tk.Frame(inner, bg=BG_BASE)
        right.pack(side="right")

        self._mode_lbl = tk.Label(right, text="CTR ▾", bg=BG_BASE,
                                  fg=TEXT_MUTED, font=FONT_LABEL, cursor="hand2")
        self._mode_lbl.pack(side="left", padx=(0, PAD_MD))
        self._mode_lbl.bind("<Button-1>", lambda _e: self._cycle_mode())
        self._mode_lbl.bind("<Enter>", lambda _e: self._mode_lbl.config(fg=TEXT_PRIMARY))
        self._mode_lbl.bind("<Leave>", lambda _e: self._mode_lbl.config(fg=TEXT_MUTED))

        self._group_lbl = tk.Label(right, text="Group ▾", bg=BG_BASE,
                                   fg=TEXT_MUTED, font=FONT_LABEL, cursor="hand2")
        self._group_lbl.pack(side="left", padx=(0, PAD_MD))
        self._group_lbl.bind("<Button-1>", lambda _e: self._cycle_group())
        self._group_lbl.bind("<Enter>", lambda _e: self._group_lbl.config(fg=TEXT_PRIMARY))
        self._group_lbl.bind("<Leave>", lambda _e: self._group_lbl.config(fg=TEXT_MUTED))

        export_lbl = tk.Label(right, text="Export", bg=BG_BASE,
                              fg=TEXT_MUTED, font=FONT_LABEL, cursor="hand2")
        export_lbl.pack(side="left")
        export_lbl.bind("<Button-1>", lambda _e: self._export_csv())
        export_lbl.bind("<Enter>", lambda _e: export_lbl.config(fg=TEXT_PRIMARY))
        export_lbl.bind("<Leave>", lambda _e: export_lbl.config(fg=TEXT_MUTED))



    # ============================================================ TABLE
    def _build_table(self) -> None:
        tree_frame = tk.Frame(self._table_container, bg=BG_BASE)
        tree_frame.pack(fill="both", expand=True)

        style = ttk.Style(tree_frame)
        style.configure("Results.Treeview",
                        rowheight=32,
                        background=BG_BASE,
                        fieldbackground=BG_BASE,
                        borderwidth=0,
                        font=FONT_BODY)
        style.configure("Results.Treeview.Heading",
                        background=BG_BASE,
                        foreground=TEXT_MUTED,
                        borderwidth=0,
                        relief="flat",
                        font=FONT_LABEL)

        col_ids = [c[0] for c in DISPLAY_COLS]
        self.tree = ttk.Treeview(tree_frame, columns=col_ids, show="headings", style="Results.Treeview")

        for cid, heading, w in DISPLAY_COLS:
            self.tree.heading(cid, text=heading,
                              command=lambda _c=cid: self._sort_by(_c))
            self.tree.column(cid, width=w, anchor="center")

        vsb = tk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview,
                           bg=BG_ELEVATED, troughcolor=BG_BASE,
                           highlightthickness=0, bd=0)
        self.tree.config(yscrollcommand=vsb.set)

        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # Row tags (flat rows)
        self.tree.tag_configure("row", background=BG_BASE)
        self.tree.tag_configure("ctr", foreground=ACCENT_BLUE)
        self.tree.tag_configure("gcm", foreground=ACCENT_RED)

    # ========================================================== EMPTY STATE
    def _build_empty_state(self) -> None:
        self._empty_overlay = tk.Frame(self._table_container, bg=BG_BASE)
        self._empty_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

        center = tk.Frame(self._empty_overlay, bg=BG_BASE)
        center.place(relx=0.5, rely=0.45, anchor="center")

        tk.Label(center, text=_EMPTY_ICON, bg=BG_BASE,
                 font=("Consolas", 48)).pack(pady=(0, PAD_SM))
        tk.Label(center, text=_EMPTY_TITLE, bg=BG_BASE,
                 fg=TEXT_MUTED,
                 font=FONT_HEADING).pack()
        tk.Label(center, text=_EMPTY_SUBTITLE, bg=BG_BASE,
                 fg=TEXT_MUTED,
                 font=FONT_BODY).pack(pady=(PAD_XS, PAD_MD))

        reload_btn = make_button(center, text="Reload CSV",
                                 command=self.load_csv, style="ghost")
        reload_btn.pack()

    def _show_empty_state(self, show: bool) -> None:
        if show:
            self._empty_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        else:
            self._empty_overlay.place_forget()

    # ====================================================== SUMMARY BAR
    def _build_summary_bar(self) -> None:
        bar = tk.Frame(self.frame, bg=BG_BASE, height=28)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        self._summary_frame = tk.Frame(bar, bg=BG_BASE)
        self._summary_frame.pack(fill="both", expand=True, padx=PAD_MD)

        # Default label (overwritten by _update_summary)
        self._summary_default = tk.Label(
            self._summary_frame, text="No data loaded",
            bg=BG_BASE, fg=TEXT_MUTED, font=FONT_LABEL, anchor="w")
        self._summary_default.pack(side="left", pady=PAD_XS)

    def _update_summary(self, df: pd.DataFrame) -> None:
        """Render one-line summary stats."""
        for w in self._summary_frame.winfo_children():
            w.destroy()

        n = len(df)
        if n == 0:
            tk.Label(self._summary_frame, text="No rows match the current filter",
                     bg=BG_BASE, fg=TEXT_MUTED, font=FONT_LABEL,
                     anchor="w").pack(side="left", pady=PAD_XS)
            return

        ctr = df[df["mode"] == "AES-CTR"]
        gcm = df[df["mode"] == "AES-GCM"]
        avg_ctr = ctr["avg_enc_time_ms"].mean() if not ctr.empty else 0
        avg_gcm = gcm["avg_enc_time_ms"].mean() if not gcm.empty else 0
        avg_oh = gcm["overhead_percent"].mean() if not gcm.empty else 0
        avg_tp_ctr = ctr["enc_throughput_mbps"].mean() if not ctr.empty else 0

        line = (
            f"Rows {n}    "
            f"CTR {avg_ctr:.2f}ms    "
            f"GCM {avg_gcm:.2f}ms    "
            f"Overhead {avg_oh:.1f}%    "
            f"CTR Throughput {avg_tp_ctr:.0f} MB/s"
        )
        tk.Label(self._summary_frame, text=line, bg=BG_BASE,
                 fg=TEXT_MUTED, font=FONT_LABEL, anchor="w").pack(side="left", pady=PAD_XS)

    # ============================================================= LOAD
    def load_csv(self) -> None:
        """Read the benchmark CSV into the table."""
        if not self._csv_path.exists():
            self.status_var.set("No CSV file found yet")
            self._update_summary(pd.DataFrame())
            self._show_empty_state(True)
            return

        self._df = pd.read_csv(self._csv_path)

        if self._df.empty:
            self._show_empty_state(True)
        else:
            self._show_empty_state(False)

        self._group_options = ["All"] + sorted(self._df["file_group"].dropna().unique().tolist())
        self._group_idx = 0
        self._group_lbl.config(text="Group ▾")

        self._apply_filter()
        self.status_var.set(f"Loaded {len(self._df)} rows from CSV")

    # =========================================================== FILTER
    def _apply_filter(self) -> None:
        df = self._df.copy()
        if df.empty:
            self._populate_tree(df)
            return

        mode = self._mode_options[self._mode_idx]
        if mode != "All":
            df = df[df["mode"] == mode]

        group = self._group_options[self._group_idx]
        if group != "All":
            df = df[df["file_group"] == group]

        self._filtered = df
        self._populate_tree(df)

    def _clear_filter(self) -> None:
        self._mode_idx = 0
        self._group_idx = 0
        self._mode_lbl.config(text="CTR ▾")
        self._group_lbl.config(text="Group ▾")
        self._apply_filter()

    def _cycle_mode(self) -> None:
        self._mode_idx = (self._mode_idx + 1) % len(self._mode_options)
        val = self._mode_options[self._mode_idx]
        if val == "AES-CTR":
            self._mode_lbl.config(text="CTR ▾")
        elif val == "AES-GCM":
            self._mode_lbl.config(text="GCM ▾")
        else:
            self._mode_lbl.config(text="All ▾")
        self._apply_filter()

    def _cycle_group(self) -> None:
        if not self._group_options:
            return
        self._group_idx = (self._group_idx + 1) % len(self._group_options)
        val = self._group_options[self._group_idx]
        self._group_lbl.config(text=("Group ▾" if val == "All" else f"{val} ▾"))
        self._apply_filter()

    # ============================================================= SORT
    def _sort_by(self, col: str) -> None:
        if self._filtered.empty:
            return
        if col == self._sort_col:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_col = col
            self._sort_asc = True

        # Update heading to show arrow
        arrow = " \u25B2" if self._sort_asc else " \u25BC"
        for cid, heading, _ in DISPLAY_COLS:
            display = heading + (arrow if cid == col else "")
            self.tree.heading(cid, text=display)

        self._filtered = self._filtered.sort_values(
            by=col, ascending=self._sort_asc,
            key=lambda s: pd.to_numeric(s, errors="coerce")
                          if s.dtype == object else s)
        self._populate_tree(self._filtered)

    # ============================================================= TREE
    def _populate_tree(self, df: pd.DataFrame) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        col_ids = [c[0] for c in DISPLAY_COLS]

        for i, (_, row) in enumerate(df.iterrows()):
            vals = []
            for cid in col_ids:
                v = row.get(cid, "")
                if isinstance(v, float):
                    v = f"{v:.4f}"
                vals.append(v)

            # Tags: flat rows + mode color
            row_tag = "row"
            mode_val = str(row.get("mode", ""))
            mode_tag = "ctr" if mode_val == "AES-CTR" else ("gcm" if mode_val == "AES-GCM" else "")
            tags = (row_tag,) if not mode_tag else (row_tag, mode_tag)
            self.tree.insert("", "end", values=vals, tags=tags)

        self._results_count_lbl.config(text=f"{len(df)} results")
        self._update_summary(df)

    # =========================================================== EXPORT
    def _export_csv(self) -> None:
        if not self._csv_path.exists():
            messagebox.showwarning("No Data", "No CSV file to export.")
            return
        dest = filedialog.asksaveasfilename(
            title="Export CSV", defaultextension=".csv",
            filetypes=[("CSV", "*.csv")])
        if dest:
            shutil.copy2(self._csv_path, dest)
            self.status_var.set(f"CSV exported to {dest}")
            messagebox.showinfo("Exported", f"Saved to:\n{dest}")
