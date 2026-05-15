"""Tab 1 — Single File Encrypt / Decrypt test."""

from __future__ import annotations

import mimetypes
import os
import threading
import tkinter as tk
from datetime import datetime
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from src.benchmark.benchmark_runner import BenchmarkRunner
from src.benchmark.experiment_config import Config
from src.benchmark.generated_files import generate_single_file
from src.logging.csv_logger import CSVLogger
from src.metrics.throughput_calculator import calculate_throughput
from src.metrics.overhead_calculator import calculate_overhead_ns, calculate_overhead_percent
from src.metrics.cost_per_mb import calculate_cost_per_mb
from src.ui.theme import (
    BG_BASE, BG_SURFACE, BG_ELEVATED, BORDER,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    ACCENT_BLUE, ACCENT_RED, ACCENT_GREEN, ACCENT_ORANGE, ACCENT_PURPLE,
    FONT_HEADING, FONT_SUBHEAD, FONT_BODY, FONT_MONO,
    FONT_METRIC, FONT_LABEL,
    PAD_LG, PAD_MD, PAD_SM, PAD_XS,
)
from src.ui.components import (
    make_button, make_card, make_tag,
    make_status_indicator, BORDER_STRONG,
)


class SingleFileTab:
    """Browse a file, run AES-CTR + AES-GCM, display comparison."""

    _SPINNER = "\u25D0\u25D3\u25D1\u25D2"

    def __init__(self, parent: tk.Frame, config: Config,
                 status_var: tk.StringVar, root: tk.Tk) -> None:
        self.config = config
        self.status_var = status_var
        self.root = root
        self.runner = BenchmarkRunner()
        self.ctr_result = None
        self.gcm_result = None
        self.selected_path: str | None = None
        self.state = "idle"  # legacy state name
        self.current_state = "idle"  # "idle" | "running" | "results" | "error"
        self._spinner_idx = 0
        self._spinner_id: str | None = None
        self._loading_anim_id: str | None = None
        self._spinner_after_id: str | None = None
        self._pulse_after_id: str | None = None
        self._run_id = 0
        self._ui_state_id = 0
        self._right_state_root: tk.Frame | None = None

        self.frame = tk.Frame(parent, bg=BG_BASE)
        self._build_ui()

    # ================================================================ BUILD
    def _build_ui(self) -> None:
        outer = tk.Frame(self.frame, bg=BG_BASE)
        outer.pack(fill="both", expand=True)

        # Left panel — fixed 300px instrument panel
        self._left_col = tk.Frame(outer, bg=BG_SURFACE, width=300)
        self._left_col.pack(side="left", fill="y")
        self._left_col.pack_propagate(False)

        # 1px right border built into the panel edge
        tk.Frame(outer, bg=BORDER, width=1).pack(side="left", fill="y")

        # Right panel — expands freely
        self._right_col = tk.Frame(outer, bg=BG_BASE)
        self._right_col.pack(side="left", fill="both", expand=True)

        self._build_left()
        self._show_placeholder_state()

    # =========================================================== LEFT COLUMN
    def _build_left(self) -> None:
        col = self._left_col
        pad = tk.Frame(col, bg=BG_SURFACE)
        pad.pack(fill="both", expand=True, padx=PAD_LG, pady=PAD_LG)

        # Mode toggle (unified segmented control)
        self._left_mode = tk.StringVar(value="manual")
        mode_wrap = tk.Frame(pad, bg=BG_ELEVATED, height=36)
        mode_wrap.pack(fill="x")
        mode_wrap.pack_propagate(False)
        mode_wrap.grid_columnconfigure(0, weight=1)
        mode_wrap.grid_columnconfigure(1, weight=1)

        self._mode_btn_generate = tk.Button(
            mode_wrap, text="Generate", command=lambda: self._set_left_mode("generate"),
            relief="flat", bd=0, highlightthickness=0, cursor="hand2", font=FONT_LABEL,
        )
        self._mode_btn_generate.grid(row=0, column=0, sticky="nsew")

        self._mode_btn_manual = tk.Button(
            mode_wrap, text="Manual File", command=lambda: self._set_left_mode("manual"),
            relief="flat", bd=0, highlightthickness=0, cursor="hand2", font=FONT_LABEL,
        )
        self._mode_btn_manual.grid(row=0, column=1, sticky="nsew")

        self._left_content = tk.Frame(pad, bg=BG_SURFACE)
        self._left_content.pack(fill="x", pady=(PAD_MD, 0))

        # Generate mode panel (UI only)
        self._generate_panel = tk.Frame(self._left_content, bg=BG_SURFACE)
        tk.Label(self._generate_panel, text="Data Size", bg=BG_SURFACE,
                 fg=TEXT_MUTED, font=FONT_LABEL, anchor="w").pack(anchor="w")

        size_wrap = tk.Frame(self._generate_panel, bg=BG_ELEVATED, height=32)
        size_wrap.pack(fill="x", pady=(PAD_XS, PAD_MD))
        size_wrap.pack_propagate(False)
        self._size_values = ["1 MB", "5 MB", "10 MB", "50 MB", "100 MB"]
        self._size_value = "10 MB"
        self._size_buttons: list[tk.Button] = []
        for i, value in enumerate(self._size_values):
            size_wrap.grid_columnconfigure(i, weight=1)
            b = tk.Button(
                size_wrap, text=value, command=lambda v=value: self._set_size(v),
                relief="flat", bd=0, highlightthickness=0, cursor="hand2", font=FONT_LABEL,
            )
            b.grid(row=0, column=i, sticky="nsew")
            self._size_buttons.append(b)

        tk.Label(self._generate_panel, text="Content", bg=BG_SURFACE,
                 fg=TEXT_MUTED, font=FONT_LABEL, anchor="w").pack(anchor="w")

        content_wrap = tk.Frame(self._generate_panel, bg=BG_ELEVATED, height=32)
        content_wrap.pack(fill="x", pady=(PAD_XS, PAD_SM))
        content_wrap.pack_propagate(False)
        self._content_values = ["Random", "Zeros", "Pattern"]
        self._content_value = "Random"
        self._content_buttons: list[tk.Button] = []
        for i, value in enumerate(self._content_values):
            content_wrap.grid_columnconfigure(i, weight=1)
            b = tk.Button(
                content_wrap, text=value, command=lambda v=value: self._set_content(v),
                relief="flat", bd=0, highlightthickness=0, cursor="hand2", font=FONT_LABEL,
            )
            b.grid(row=0, column=i, sticky="nsew")
            self._content_buttons.append(b)

        self._generate_note = tk.Label(
            self._generate_panel,
            text="10 MB of random bytes · fresh key per run",
            bg=BG_SURFACE, fg=TEXT_MUTED, font=FONT_LABEL, anchor="w", justify="left",
        )
        self._generate_note.pack(anchor="w")

        # Manual mode panel
        self._manual_panel = tk.Frame(self._left_content, bg=BG_SURFACE)
        self._manual_file_line = tk.Label(
            self._manual_panel, text="No file selected",
            bg=BG_SURFACE, fg=TEXT_MUTED, font=FONT_BODY, anchor="w",
        )
        self._manual_file_line.pack(fill="x")

        self._browse_btn = make_button(self._manual_panel, text="Browse",
                                       command=self._browse, style="ghost")
        self._browse_btn.pack(anchor="w", pady=(PAD_XS, PAD_SM))

        self._manual_meta_line = tk.Label(
            self._manual_panel, text="",
            bg=BG_SURFACE, fg=TEXT_MUTED, font=FONT_LABEL, anchor="w",
        )
        self._manual_meta_line.pack(fill="x")

        # Flexible space
        tk.Frame(pad, bg=BG_SURFACE).pack(fill="both", expand=True)

        # Collapsed config reference
        tk.Label(
            pad,
            text="AES-256  ·  5 runs  ·  1 warm-up  ·  ns precision",
            bg=BG_SURFACE, fg=TEXT_MUTED, font=FONT_LABEL, anchor="w",
        ).pack(fill="x", pady=(0, PAD_MD))

        self.run_btn = make_button(pad,
                                   text="Run Test",
                                   command=self._run_test,
                                   style="disabled")
        self.run_btn.pack(fill="x")
        self.run_btn.config(pady=10)

        self.spinner_label = tk.Label(pad, text="", bg=BG_SURFACE,
                                      fg=TEXT_PRIMARY, font=FONT_BODY)
        self.spinner_label.pack(pady=(PAD_SM, 0))

        self._set_left_mode("manual")
        self._sync_left_controls_visuals()

    def _set_left_mode(self, mode: str) -> None:
        self._left_mode.set(mode)
        self._generate_panel.pack_forget()
        self._manual_panel.pack_forget()
        if mode == "generate":
            self._generate_panel.pack(fill="x")
        else:
            self._manual_panel.pack(fill="x")
        self._sync_left_controls_visuals()

    def _set_size(self, value: str) -> None:
        self._size_value = value
        self._generate_note.config(
            text=f"{self._size_value} of {self._content_value.lower()} bytes · fresh key per run"
        )
        self._sync_left_controls_visuals()

    def _set_content(self, value: str) -> None:
        self._content_value = value
        self._generate_note.config(
            text=f"{self._size_value} of {self._content_value.lower()} bytes · fresh key per run"
        )
        self._sync_left_controls_visuals()

    def _sync_left_controls_visuals(self) -> None:
        active_bg = TEXT_PRIMARY
        active_fg = BG_BASE
        inactive_bg = BG_ELEVATED
        inactive_fg = TEXT_MUTED

        if self._left_mode.get() == "generate":
            self._mode_btn_generate.config(bg=active_bg, fg=active_fg)
            self._mode_btn_manual.config(bg=inactive_bg, fg=inactive_fg)
            self._enable_run_btn()
        else:
            self._mode_btn_generate.config(bg=inactive_bg, fg=inactive_fg)
            self._mode_btn_manual.config(bg=active_bg, fg=active_fg)
            if self.selected_path:
                self._enable_run_btn()
            else:
                from src.ui.components import _BUTTON_STYLES
                bg, fg = _BUTTON_STYLES["disabled"]
                self.run_btn.config(state="disabled", bg=bg, fg=fg, cursor="", text="Run Test")

        for b, value in zip(self._size_buttons, self._size_values):
            if value == self._size_value:
                b.config(bg=active_bg, fg=active_fg)
            else:
                b.config(bg=BG_ELEVATED, fg=TEXT_SECONDARY)

        for b, value in zip(self._content_buttons, self._content_values):
            if value == self._content_value:
                b.config(bg=active_bg, fg=active_fg)
            else:
                b.config(bg=BG_ELEVATED, fg=TEXT_SECONDARY)

    # ========================================================== RIGHT COLUMN
    def _clear_right_panel(self) -> None:
        """Destroy all right-panel widgets and cancel queued panel animations."""
        self._ui_state_id += 1

        for w in self._right_col.winfo_children():
            w.destroy()

        if self._spinner_after_id:
            try:
                self.root.after_cancel(self._spinner_after_id)
            except tk.TclError:
                pass
            self._spinner_after_id = None

        if self._loading_anim_id:
            try:
                self.root.after_cancel(self._loading_anim_id)
            except tk.TclError:
                pass
            self._loading_anim_id = None

        if self._pulse_after_id:
            try:
                self.root.after_cancel(self._pulse_after_id)
            except tk.TclError:
                pass
            self._pulse_after_id = None

        self._right_state_root = tk.Frame(self._right_col, bg=BG_BASE)
        self._right_state_root.pack(fill="both", expand=True)

    def _clear_right(self) -> None:
        """Backward-compatible alias for right panel reset."""
        self._clear_right_panel()

    def _set_controls_enabled(self, enabled: bool) -> None:
        """Enable/disable user controls during benchmark execution."""
        if enabled:
            self._browse_btn.config(state="normal")
            if self._left_mode.get() == "generate" or self.selected_path:
                self._enable_run_btn()
            else:
                from src.ui.components import _BUTTON_STYLES
                bg, fg = _BUTTON_STYLES["disabled"]
                self.run_btn.config(state="disabled", bg=bg, fg=fg, cursor="", text="Run Test")
        else:
            self._disable_controls()

    # ──────────────────────────────────────────── STATE A: placeholder
    def _show_placeholder(self) -> None:
        """Right column before any test is run — minimal placeholder."""
        self._clear_right_panel()
        self.current_state = "idle"
        self.state = "idle"
        col = self._right_state_root or self._right_col

        pad = tk.Frame(col, bg=BG_BASE)
        pad.pack(fill="both", expand=True, padx=PAD_LG, pady=PAD_LG)

        tk.Frame(pad, bg=BG_BASE).pack(fill="both", expand=True)

        center = tk.Frame(pad, bg=BG_BASE)
        center.pack(fill="x")

        tk.Label(center, text="—", bg=BG_BASE, fg=TEXT_MUTED,
                 font=FONT_METRIC).pack()
        tk.Label(center, text="Run a test to see results", bg=BG_BASE,
                 fg=TEXT_MUTED, font=FONT_BODY).pack(pady=(PAD_SM, PAD_LG))

        steps = tk.Frame(center, bg=BG_BASE)
        steps.pack(anchor="w")
        tk.Label(steps, text="① File loaded before timing starts",
                 bg=BG_BASE, fg=TEXT_MUTED, font=FONT_LABEL,
                 anchor="w").pack(anchor="w", pady=(0, PAD_SM))
        tk.Label(steps, text="② gc.collect() before each run",
                 bg=BG_BASE, fg=TEXT_MUTED, font=FONT_LABEL,
                 anchor="w").pack(anchor="w", pady=(0, PAD_SM))
        tk.Label(steps, text="③ Only cipher call is measured",
                 bg=BG_BASE, fg=TEXT_MUTED, font=FONT_LABEL,
                 anchor="w").pack(anchor="w")

        tk.Frame(pad, bg=BG_BASE).pack(fill="both", expand=True)

    def _show_placeholder_state(self) -> None:
        """Backward-compatible wrapper for idle state rendering."""
        self._show_placeholder()

    @staticmethod
    def _build_ghost_card(parent: tk.Frame, *, col: int,
                          mode: str, auth_tag_label: str,
                          auth_value: str,
                          bottom_text: str) -> None:
        """Dimmed skeleton of a mode result card with 6 metric rows."""
        outer = tk.Frame(parent, bg=BORDER)
        outer.grid(row=0, column=col, sticky="nsew",
                   padx=PAD_XS, pady=PAD_XS)

        shell = tk.Frame(outer, bg=BG_SURFACE)
        shell.pack(fill="both", padx=1, pady=1)

        row0 = tk.Frame(shell, bg=BG_SURFACE)
        row0.pack(fill="both")

        # Muted left border (BORDER, not accent)
        tk.Frame(row0, bg=BORDER, width=2).pack(side="left", fill="y")

        content = tk.Frame(row0, bg=BG_SURFACE, padx=PAD_MD, pady=PAD_MD)
        content.pack(side="left", fill="both", expand=True)

        # Header row
        hdr = tk.Frame(content, bg=BG_SURFACE)
        hdr.pack(fill="x", pady=(0, PAD_SM))
        tk.Label(hdr, text=mode, bg=BG_SURFACE, fg=TEXT_MUTED,
                 font=FONT_SUBHEAD).pack(side="left", padx=(0, PAD_XS))
        make_tag(hdr, auth_tag_label, TEXT_MUTED).pack(side="left")

        # 6 placeholder metric rows with alternating bg
        _GHOST_ROWS = [
            ("Enc Time",   "\u2014 ms"),
            ("Dec Time",   "\u2014 ms"),
            ("Throughput", "\u2014 MB/s"),
            ("Cost / MB",  "\u2014 ms/MB"),
            ("Std Dev",    "\u2014 ns"),
            ("Auth Tag",   auth_value),
        ]
        for i, (label, value) in enumerate(_GHOST_ROWS):
            row_bg = BG_ELEVATED if i % 2 == 0 else BG_BASE
            row = tk.Frame(content, bg=row_bg)
            row.pack(fill="x")
            tk.Label(row, text=label, bg=row_bg, fg=TEXT_MUTED,
                     font=FONT_LABEL, anchor="w",
                     padx=PAD_SM, pady=PAD_XS).pack(side="left")
            tk.Label(row, text=value, bg=row_bg, fg=TEXT_MUTED,
                     font=FONT_BODY, anchor="e",
                     padx=PAD_SM, pady=PAD_XS).pack(side="right")

        # Bottom tag
        bt = tk.Frame(content, bg=BG_SURFACE)
        bt.pack(fill="x", pady=(PAD_SM, 0))
        make_tag(bt, bottom_text, TEXT_MUTED).pack(anchor="w")

    @staticmethod
    def _build_ghost_overhead(parent: tk.Frame) -> None:
        """Dimmed skeleton of the overhead banner."""
        outer = tk.Frame(parent, bg=BORDER)
        outer.pack(fill="x", pady=PAD_XS)

        shell = tk.Frame(outer, bg=BG_ELEVATED)
        shell.pack(fill="both", padx=1, pady=1)

        row = tk.Frame(shell, bg=BG_ELEVATED)
        row.pack(fill="both")

        # Muted left accent bar
        tk.Frame(row, bg=BORDER, width=3).pack(side="left", fill="y")

        content = tk.Frame(row, bg=BG_ELEVATED, padx=PAD_MD, pady=PAD_MD)
        content.pack(side="left", fill="both", expand=True)

        # Left section
        left = tk.Frame(content, bg=BG_ELEVATED)
        left.pack(side="left")
        tk.Label(left, text="Authentication Overhead",
                 bg=BG_ELEVATED, fg=TEXT_MUTED,
                 font=FONT_SUBHEAD).pack(anchor="w")
        tk.Label(left, text="\u2014 ms",
                 bg=BG_ELEVATED, fg=TEXT_MUTED,
                 font=FONT_METRIC).pack(anchor="w")

        # Vertical divider
        div_wrap = tk.Frame(content, bg=BG_ELEVATED, padx=PAD_MD)
        div_wrap.pack(side="left", fill="y", pady=PAD_XS)
        tk.Frame(div_wrap, bg=BORDER, width=1).pack(fill="y", expand=True)

        # Right section
        right = tk.Frame(content, bg=BG_ELEVATED)
        right.pack(side="left")
        tk.Label(right, text="\u2014%",
                 bg=BG_ELEVATED, fg=TEXT_MUTED,
                 font=FONT_METRIC).pack(anchor="w")
        tk.Label(right, text="Run a test to measure overhead",
                 bg=BG_ELEVATED, fg=TEXT_MUTED,
                 font=FONT_LABEL).pack(anchor="w")

    @staticmethod
    def _build_how_it_works(parent: tk.Frame) -> None:
        """Explainer card at bottom of right panel placeholder."""
        outer = tk.Frame(parent, bg=BORDER)
        outer.pack(fill="x", pady=(PAD_SM, 0))

        shell = tk.Frame(outer, bg=BG_BASE)
        shell.pack(fill="both", padx=1, pady=1)

        row0 = tk.Frame(shell, bg=BG_BASE)
        row0.pack(fill="both")

        # Left accent bar — purple
        tk.Frame(row0, bg=ACCENT_PURPLE, width=2).pack(side="left", fill="y")

        content = tk.Frame(row0, bg=BG_BASE, padx=PAD_MD, pady=PAD_MD)
        content.pack(side="left", fill="both", expand=True)

        tk.Label(content, text="How This Works", bg=BG_BASE,
                 fg=ACCENT_PURPLE, font=FONT_LABEL).pack(anchor="w",
                                                          pady=(0, PAD_SM))

        _STEPS = [
            ("\u2460", "File loaded into memory (I/O excluded from timing)"),
            ("\u2461", "gc.collect() called before each timed run"),
            ("\u2462", "Cipher operation timed with perf_counter_ns()"),
        ]
        for icon, text in _STEPS:
            step_row = tk.Frame(content, bg=BG_BASE)
            step_row.pack(fill="x", pady=1)
            tk.Label(step_row, text=icon, bg=BG_BASE, fg=ACCENT_PURPLE,
                     font=FONT_LABEL).pack(side="left", padx=(0, PAD_SM))
            tk.Label(step_row, text=text, bg=BG_BASE, fg=TEXT_SECONDARY,
                     font=FONT_LABEL).pack(side="left")

    # ──────────────────────────────────────────── STATE B: loading
    def _show_loading(self) -> None:
        """Right column while test is running — centered spinner + dots."""
        self._clear_right_panel()
        self.current_state = "running"
        self.state = "running"
        col = self._right_state_root or self._right_col
        state_id = self._ui_state_id

        # Vertically center everything
        spacer_top = tk.Frame(col, bg=BG_BASE)
        spacer_top.pack(fill="both", expand=True)

        center = tk.Frame(col, bg=BG_BASE)
        center.pack()

        spacer_bot = tk.Frame(col, bg=BG_BASE)
        spacer_bot.pack(fill="both", expand=True)

        # Spinner character
        self._loading_icon = tk.Label(
            center, text=self._SPINNER[0],
            bg=BG_BASE, fg=TEXT_PRIMARY, font=FONT_METRIC)
        self._loading_icon.pack()

        # Title
        tk.Label(center, text="Running encryption test\u2026",
                 bg=BG_BASE, fg=TEXT_PRIMARY,
                 font=FONT_HEADING).pack(pady=(PAD_SM, PAD_XS))

        # Current operation line (updated live)
        self._operation_var = tk.StringVar(value="Preparing test...")
        self._op_label = tk.Label(
            center, textvariable=self._operation_var,
            bg=BG_BASE, fg=TEXT_SECONDARY, font=FONT_MONO)
        self._op_label.pack(pady=(0, PAD_MD))

        # Dot indicators row
        total = self.config.runs
        dots_frame = tk.Frame(center, bg=BG_BASE)
        dots_frame.pack()
        self._dot_labels: list[tk.Label] = []
        self._dot_name_labels: list[tk.Label] = []
        for i in range(total):
            col_f = tk.Frame(dots_frame, bg=BG_BASE)
            col_f.pack(side="left", padx=PAD_XS)
            dot = tk.Label(col_f, text="\u25CB", bg=BG_BASE, fg=BORDER,
                           font=("Consolas", 14))
            dot.pack()
            name = "W" if i == 0 else str(i)
            name_lbl = tk.Label(col_f, text=name, bg=BG_BASE,
                                fg=TEXT_MUTED, font=FONT_LABEL)
            name_lbl.pack()
            self._dot_labels.append(dot)
            self._dot_name_labels.append(name_lbl)

        # Progress note
        tk.Label(center, text="First run discarded as warm-up",
                 bg=BG_BASE, fg=TEXT_MUTED,
                 font=FONT_LABEL).pack(pady=(PAD_MD, 0))

        # Track current progress for live updates
        self._current_mode = "AES-CTR"
        self._current_run = 0
        self._total_runs = total

        # Start spinner animation
        self._loading_anim_idx = 0
        self._animate_spinner(state_id)

    def _show_loading_state(self) -> None:
        """Backward-compatible wrapper for running state rendering."""
        self._show_loading()

    def _animate_spinner(self, state_id: int | None = None) -> None:
        """Animate loading spinner while current state is running."""
        if state_id is None:
            state_id = self._ui_state_id
        if state_id != self._ui_state_id:
            return
        if self.current_state != "running":
            return
        try:
            if not self._loading_icon.winfo_exists():
                return
        except Exception:
            return

        ch = self._SPINNER[self._loading_anim_idx % len(self._SPINNER)]
        self._loading_icon.config(text=ch)
        self._loading_anim_idx += 1
        self._spinner_after_id = self.root.after(
            200, lambda sid=state_id: self._animate_spinner(sid))

    def _tick_loading_anim(self) -> None:
        """Backward-compatible alias for loading spinner animation."""
        self._animate_spinner(self._ui_state_id)

    def _stop_loading_anim(self) -> None:
        if self._spinner_after_id is not None:
            try:
                self.root.after_cancel(self._spinner_after_id)
            except tk.TclError:
                pass
            self._spinner_after_id = None
        self._loading_anim_id = None

    def _update_progress(self, run_number: int, total_runs: int,
                         run_id: int | None = None) -> None:
        """Called from background thread via progress_callback."""
        if run_id is not None and run_id != self._run_id:
            return

        # CTR runs first (1..total), then GCM (1..total)
        if not hasattr(self, '_progress_call_count'):
            self._progress_call_count = 0
        self._progress_call_count += 1

        if self._progress_call_count <= total_runs:
            mode = "AES-CTR"
            run_in_mode = self._progress_call_count
        else:
            mode = "AES-GCM"
            run_in_mode = self._progress_call_count - total_runs

        self.root.after(0, lambda m=mode, r=run_in_mode, t=total_runs,
                        rid=run_id: self._apply_progress(m, r, t, rid))

    def _update_operation_label(self, text: str) -> None:
        """Safely update operation text only while loading state is active."""
        if self.current_state != "running":
            return
        try:
            if hasattr(self, "_operation_var"):
                self._operation_var.set(text)
        except Exception:
            pass

    def _update_run_dots(self, completed: int, total_runs: int | None = None) -> None:
        """Safely update run dots during loading."""
        if self.current_state != "running":
            return
        if total_runs is None:
            total_runs = len(getattr(self, "_dot_labels", []))
        try:
            if hasattr(self, "_dot_labels"):
                for i, dot in enumerate(self._dot_labels):
                    if not dot.winfo_exists():
                        return
                    if i < completed - 1:
                        dot.config(text="\u25CF", fg=TEXT_PRIMARY)
                    elif i == completed - 1:
                        dot.config(text="\u25CF", fg=TEXT_SECONDARY)
                    else:
                        dot.config(text="\u25CB", fg=BORDER)
        except Exception:
            pass

    def _apply_progress(self, mode: str, run_number: int,
                        total_runs: int, run_id: int | None = None) -> None:
        """Apply progress update on main thread."""
        if run_id is not None and run_id != self._run_id:
            return
        if self.current_state != "running":
            return
        try:
            # Update operation label
            self._update_operation_label(
                f"{mode}  \u00B7  Run {run_number} of {total_runs}")

            # Update dot indicators
            # When mode switches to GCM, reset dots
            if mode == "AES-GCM" and hasattr(self, '_last_progress_mode') \
                    and self._last_progress_mode == "AES-CTR":
                # Reset all dots for GCM phase
                for d in self._dot_labels:
                    d.config(text="\u25CB", fg=BORDER)

            self._last_progress_mode = mode

            self._update_run_dots(run_number, total_runs)
        except tk.TclError:
            pass

    # ============================================================== ACTIONS
    def _browse(self) -> None:
        if self.state == "running":
            return
        path = filedialog.askopenfilename(title="Select a file to encrypt")
        if path:
            self.selected_path = path
            size_bytes = os.path.getsize(path)
            size_mb = size_bytes / 1_048_576
            ext = Path(path).suffix or "N/A"
            mime_type, _ = mimetypes.guess_type(path)
            category = (mime_type.split("/")[0] if mime_type else "unknown")
            fname = Path(path).name

            truncated = (fname[:26] + "\u2026") if len(fname) > 26 else fname
            self._manual_file_line.config(text=f"{truncated}  ·  {size_mb:.1f} MB",
                                          fg=TEXT_PRIMARY)
            self._manual_meta_line.config(text=f"{size_mb:.1f} MB  ·  {category}  ·  {ext}")

            # Enable the run button
            self._enable_run_btn()

            self.status_var.set(f"Selected: {fname}")

    def _enable_run_btn(self) -> None:
        """Switch run button from disabled to primary style."""
        from src.ui.components import _BUTTON_STYLES, _lighten, _darken
        bg, fg = _BUTTON_STYLES["primary"]
        self.run_btn.config(
            state="normal", bg=bg, fg=fg, cursor="hand2",
            activebackground=_lighten(bg, 30),
            activeforeground=fg,
            text="Run Test",
        )
        self.run_btn._base_bg = bg
        self.run_btn._hover_bg = _lighten(bg, 20)
        self.run_btn._press_bg = _darken(bg, 15)
        self.run_btn.bind("<Enter>",
                          lambda _e, b=self.run_btn: b.config(bg=b._hover_bg))
        self.run_btn.bind("<Leave>",
                          lambda _e, b=self.run_btn: b.config(bg=b._base_bg))
        self.run_btn.bind("<ButtonPress-1>",
                          lambda _e, b=self.run_btn: b.config(bg=b._press_bg))
        self.run_btn.bind("<ButtonRelease-1>",
                          lambda _e, b=self.run_btn: b.config(bg=b._hover_bg))

    def _disable_controls(self) -> None:
        """Disable run + browse buttons during a test run."""
        from src.ui.components import _BUTTON_STYLES
        bg, fg = _BUTTON_STYLES["disabled"]
        self.run_btn.config(state="disabled", bg=bg, fg=fg, cursor="",
                            text="Running...")
        self._browse_btn.config(state="disabled")

    def _restore_controls(self) -> None:
        """Re-enable run + browse after test finishes."""
        self._set_controls_enabled(True)

    def _run_test(self) -> None:
        if self.current_state == "running":
            return
            
        if self._left_mode.get() == "generate":
            # parse size value ("10 MB" -> 10)
            size_str = self._size_value.split()[0]
            try:
                size_mb = int(size_str)
            except ValueError:
                size_mb = 10
            # generate file synchronously since single file generate is usually fast
            path_str = generate_single_file(self.config.input_dir, size_mb, self._content_value)
            self.selected_path = path_str
            self.status_var.set(f"Generated single file: {Path(path_str).name}")
        elif not self.selected_path:
            messagebox.showwarning("No File", "Please select a file first.")
            return

        self._run_id += 1
        current_run_id = self._run_id

        self._set_controls_enabled(False)
        self._start_spinner()
        self._show_loading()  # State B
        self._progress_call_count = 0
        self._last_progress_mode = ""
        self.status_var.set("Running single-file benchmark\u2026")

        def work() -> None:
            try:
                results = self.runner.run_experiment(
                    self.selected_path, "single", self.config,
                    progress_callback=lambda rn, tr: self._update_progress(
                        rn, tr, current_run_id))
                ctr_res, gcm_res = results[0], results[1]

                def deliver() -> None:
                    if self._run_id == current_run_id and self.current_state == "running":
                        self._show_results(ctr_res, gcm_res)
                        self._set_controls_enabled(True)

                self.root.after(0, deliver)
            except Exception as exc:
                self.root.after(0, lambda e=str(exc), rid=current_run_id: (
                    self._show_error(e) if self._run_id == rid else None
                ))
            finally:
                self.root.after(0, lambda rid=current_run_id: (
                    self._stop_spinner() if self._run_id == rid else None
                ))
                self.root.after(0, lambda rid=current_run_id: (
                    self._stop_loading_anim() if self._run_id == rid else None
                ))

        threading.Thread(target=work, daemon=True).start()

    # ─────────────────────────────────────────────────── spinner animation
    def _start_spinner(self) -> None:
        self._spinner_idx = 0
        self._tick_spinner()

    def _tick_spinner(self) -> None:
        ch = self._SPINNER[self._spinner_idx % len(self._SPINNER)]
        self.spinner_label.config(text=f" {ch}  Running benchmark\u2026")
        self._spinner_idx += 1
        self._spinner_id = self.root.after(200, self._tick_spinner)

    def _stop_spinner(self) -> None:
        if self._spinner_id is not None:
            self.root.after_cancel(self._spinner_id)
            self._spinner_id = None
        self.spinner_label.config(text="")

    # ============================================================== DISPLAY
    def _show_results(self, ctr, gcm) -> None:
        """State C — show real results with full right panel rebuild."""
        self._stop_loading_anim()
        self._clear_right_panel()
        self.current_state = "results"
        self.state = "results"
        state_id = self._ui_state_id
        self.ctr_result, self.gcm_result = ctr, gcm

        col = self._right_state_root or self._right_col
        pad = tk.Frame(col, bg=BG_BASE)
        pad.pack(fill="both", expand=True, padx=PAD_LG, pady=PAD_LG)

        # Flash transition: briefly show BG_ELEVATED then revert
        pad.config(bg=BG_ELEVATED)
        self.root.after(
            150,
            lambda p=pad, sid=state_id: (
                p.config(bg=BG_BASE)
                if sid == self._ui_state_id and p.winfo_exists()
                else None
            ),
        )

        # ── Section header row ──
        hdr_row = tk.Frame(pad, bg=BG_BASE)
        hdr_row.pack(fill="x")
        tk.Label(hdr_row, text="Results", bg=BG_BASE,
                 fg=TEXT_PRIMARY, font=FONT_HEADING).pack(side="left")
        complete_tag = make_tag(hdr_row, "Complete", TEXT_PRIMARY)
        complete_tag.config(fg=TEXT_PRIMARY)
        complete_tag.pack(
            side="left", padx=(PAD_SM, 0))
        timestamp_str = datetime.now().strftime("%H:%M:%S")
        tk.Label(hdr_row, text=timestamp_str, bg=BG_BASE,
                 fg=TEXT_MUTED, font=FONT_LABEL).pack(side="right")

        tk.Frame(pad, bg=BG_BASE, height=PAD_MD).pack(fill="x")

        # ── Metric values ──
        ctr_enc_ms = ctr.avg_enc_time_ns / 1e6
        ctr_dec_ms = ctr.avg_dec_time_ns / 1e6
        ctr_tp = calculate_throughput(ctr.file_size_bytes, int(ctr.avg_enc_time_ns))
        ctr_cost = calculate_cost_per_mb(ctr.avg_enc_time_ns, ctr.file_size_bytes)
        gcm_enc_ms = gcm.avg_enc_time_ns / 1e6
        gcm_dec_ms = gcm.avg_dec_time_ns / 1e6
        gcm_tp = calculate_throughput(gcm.file_size_bytes, int(gcm.avg_enc_time_ns))
        gcm_cost = calculate_cost_per_mb(gcm.avg_enc_time_ns, gcm.file_size_bytes)

        # ── Two side-by-side result cards ──
        cards_row = tk.Frame(pad, bg=BG_BASE)
        cards_row.pack(fill="x")
        cards_row.columnconfigure(0, weight=1)
        cards_row.columnconfigure(1, weight=1)

        ctr_val_labels = self._build_mode_card(
            cards_row, col=0,
            mode="AES-CTR", auth_tag_text="No Auth",
            enc_ms=ctr_enc_ms, dec_ms=ctr_dec_ms,
            throughput=ctr_tp, cost=ctr_cost,
        )
        gcm_val_labels = self._build_mode_card(
            cards_row, col=1,
            mode="AES-GCM", auth_tag_text="128-bit",
            enc_ms=gcm_enc_ms, dec_ms=gcm_dec_ms,
            throughput=gcm_tp, cost=gcm_cost,
        )

        # Flash metric values on arrival
        self._flash_metric_labels(ctr_val_labels, TEXT_PRIMARY)
        self._flash_metric_labels(gcm_val_labels, TEXT_PRIMARY)

        # ── Overhead banner ──
        self._build_overhead_banner(pad, ctr, gcm, ctr_enc_ms, gcm_enc_ms)

        note = tk.Label(
            pad,
            text="File content type has minimal effect on AES timing. Size is the dominant variable.",
            bg=BG_BASE, fg=TEXT_MUTED, font=(FONT_LABEL[0], FONT_LABEL[1], "italic"),
            anchor="w", justify="left",
        )
        note.pack(fill="x", pady=(PAD_SM, PAD_MD))

        # ── Save affordance ──
        save_row = tk.Frame(pad, bg=BG_BASE)
        save_row.pack(fill="x")

        save_btn = tk.Label(save_row, text="Save to CSV", bg=BG_BASE,
                            fg=TEXT_MUTED, font=FONT_LABEL, cursor="hand2")
        save_btn.pack(side="left")
        save_btn.bind("<Enter>", lambda _e: save_btn.config(fg=TEXT_PRIMARY))
        save_btn.bind("<Leave>", lambda _e: save_btn.config(fg=TEXT_MUTED))
        save_btn.bind("<Button-1>", lambda _e: self._save_result())

        self._save_status_frame = tk.Frame(save_row, bg=BG_BASE)
        self._save_status_frame.pack(side="left", padx=(PAD_SM, 0))

        # ── "Run another file" affordance ──
        run_again = tk.Label(
            pad, text="\u2190 Run another file",
            bg=BG_BASE, fg=TEXT_MUTED, font=FONT_LABEL, cursor="hand2")
        run_again.pack(anchor="w", pady=(PAD_MD, 0))
        run_again.bind("<Enter>", lambda _e: run_again.config(fg=ACCENT_BLUE))
        run_again.bind("<Leave>", lambda _e: run_again.config(fg=TEXT_MUTED))

        def _on_run_another(_e=None) -> None:
            self._show_placeholder()
            self._set_controls_enabled(True)

        run_again.bind("<Button-1>", _on_run_another)

        self.status_var.set(
            f"Done \u2014 CTR: {ctr_enc_ms:.3f}ms | GCM: {gcm_enc_ms:.3f}ms | "
            f"Overhead: +{calculate_overhead_percent(gcm.avg_enc_time_ns, ctr.avg_enc_time_ns):.1f}%")

    def _display_results(self) -> None:
        """Backward-compatible wrapper for results rendering."""
        if self.ctr_result is None or self.gcm_result is None:
            return
        self._show_results(self.ctr_result, self.gcm_result)

    # ──────────────────────────────────────────────── metric flash
    def _flash_metric_labels(self, labels: list[tk.Label],
                             flash_color: str) -> None:
        """Briefly set all labels to *flash_color* then restore original."""
        if self.current_state != "results":
            return
        state_id = self._ui_state_id
        for lbl in labels:
            lbl.config(fg=flash_color)
        self.root.after(
            300,
            lambda active=labels: [
                lbl.config(fg=TEXT_PRIMARY)
                for lbl in active
                if state_id == self._ui_state_id and self.current_state == "results" and lbl.winfo_exists()
            ],
        )

    def _show_error(self, message: str) -> None:
        """Render a clean error state in the right panel."""
        self._clear_right_panel()
        self.current_state = "error"
        self.state = "error"
        self._set_controls_enabled(True)

        parent = self._right_state_root or self._right_col
        tk.Label(parent, text="Test Failed", bg=BG_BASE, fg=TEXT_PRIMARY,
             font=FONT_HEADING, anchor="w").pack(anchor="w", padx=PAD_LG, pady=(PAD_LG, PAD_SM))
        card = make_card(parent)
        tk.Label(
            card,
            text=f"\u26A0  {message}",
            bg=BG_SURFACE,
            fg=TEXT_PRIMARY,
            font=FONT_BODY,
            wraplength=400,
            justify="left",
        ).pack(anchor="w", padx=PAD_MD, pady=PAD_SM)

        make_button(
            card,
            text="\u2190 Try Again",
            command=self._show_placeholder,
            style="ghost",
        ).pack(anchor="w", padx=PAD_MD, pady=PAD_SM)

    # ──────────────────────────────────────────────── mode result card
    @staticmethod
    def _build_mode_card(parent: tk.Frame, *, col: int, mode: str,
                         auth_tag_text: str,
                         enc_ms: float, dec_ms: float,
                         throughput: float, cost: float) -> list[tk.Label]:
        outer = tk.Frame(parent, bg=BG_BASE)
        outer.grid(row=0, column=col, sticky="nsew", padx=(0, PAD_MD if col == 0 else 0), pady=(0, PAD_MD))

        row0 = tk.Frame(outer, bg=BG_BASE)
        row0.pack(fill="both", expand=True)
        tk.Frame(row0, bg=BORDER_STRONG, width=2).pack(side="left", fill="y")

        content = tk.Frame(row0, bg=BG_SURFACE, padx=PAD_LG, pady=PAD_LG)
        content.pack(side="left", fill="both", expand=True)

        hdr = tk.Frame(content, bg=BG_SURFACE)
        hdr.pack(fill="x", pady=(0, PAD_MD))
        tk.Label(hdr, text=mode, bg=BG_SURFACE, fg=TEXT_PRIMARY,
                 font=FONT_SUBHEAD).pack(side="left")
        tk.Label(hdr, text=auth_tag_text, bg=BG_SURFACE, fg=TEXT_MUTED,
                 font=FONT_LABEL).pack(side="right")

        metrics = [
            ("Enc Time", f"{enc_ms:.3f} ms"),
            ("Dec Time", f"{dec_ms:.3f} ms"),
            ("Throughput", f"{throughput:.1f} MB/s"),
            ("Cost / MB", f"{cost:.2f} ms"),
        ]

        val_labels: list[tk.Label] = []
        for lbl, val in metrics:
            row = tk.Frame(content, bg=BG_SURFACE)
            row.pack(fill="x", pady=(0, PAD_SM))
            tk.Label(row, text=lbl, bg=BG_SURFACE, fg=TEXT_MUTED,
                     font=FONT_LABEL, anchor="w").pack(side="left")
            v_lbl = tk.Label(row, text=val, bg=BG_SURFACE, fg=TEXT_PRIMARY,
                             font=FONT_BODY, anchor="e")
            v_lbl.pack(side="right")
            val_labels.append(v_lbl)

        return val_labels

    # ──────────────────────────────────────────────── overhead banner
    @staticmethod
    def _build_overhead_banner(parent: tk.Frame,
                               ctr, gcm,
                               ctr_enc_ms: float,
                               gcm_enc_ms: float) -> None:
        overhead_ns = calculate_overhead_ns(gcm.avg_enc_time_ns, ctr.avg_enc_time_ns)
        overhead_pct = calculate_overhead_percent(gcm.avg_enc_time_ns, ctr.avg_enc_time_ns)
        overhead_ms = overhead_ns / 1e6

        row = tk.Frame(parent, bg=BG_BASE)
        row.pack(fill="x", pady=(PAD_SM, PAD_SM))
        tk.Label(row, text="Authentication overhead", bg=BG_BASE,
             fg=TEXT_MUTED, font=FONT_LABEL).pack(side="left")
        tk.Label(row, text=f"+{overhead_ms:.3f} ms", bg=BG_BASE,
             fg=TEXT_PRIMARY, font=FONT_METRIC).pack(side="left", padx=(PAD_MD, PAD_MD))
        tk.Label(row, text=f"(+{overhead_pct:.1f}%)", bg=BG_BASE,
             fg=TEXT_SECONDARY, font=FONT_HEADING).pack(side="left")

    # ============================================================ SAVE
    def _save_result(self) -> None:
        if not self.ctr_result or not self.gcm_result:
            return
        try:
            logger = CSVLogger(self.config)
            logger.log_single(self.ctr_result)
            logger.log_single(self.gcm_result, ctr_ref=self.ctr_result)
            # Show inline save indicator
            for w in self._save_status_frame.winfo_children():
                w.destroy()
            ind = make_status_indicator(self._save_status_frame,
                                        f"Saved to {Path(self.config.csv_file).name}",
                                        "success")
            ind.pack(anchor="w")
            self.status_var.set("Results saved to CSV \u2713")
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to save: {exc}")
