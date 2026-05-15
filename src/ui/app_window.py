"""Main Tkinter window — custom tab controller and theming."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from src.benchmark.experiment_config import load_config
from src.ui.theme import (
    BG_BASE, BG_SURFACE, BG_ELEVATED, BORDER, BORDER_GLOW,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    ACCENT_BLUE, ACCENT_RED, ACCENT_GREEN, ACCENT_ORANGE, ACCENT_PURPLE,
    FONT_DISPLAY, FONT_HEADING, FONT_SUBHEAD, FONT_BODY, FONT_LABEL,
    PAD_LG, PAD_MD, PAD_SM, PAD_XS,
    configure_tkinter_style,
)
from src.ui.tab_single_file import SingleFileTab
from src.ui.tab_benchmark import BenchmarkTab
from src.ui.tab_graphs import GraphsTab
from src.ui.tab_results import ResultsTab
from src.ui.tab_summary import SummaryTab
from src.ui.tab_tamper import TamperTab
from src.ui.tab_sysinfo import SysInfoTab

BG_BASE = "#f5f5f0"
BG_SURFACE = "#efefea"
BG_ELEVATED = "#e5e5e0"
BG_HOVER = "#dcdcd6"

BORDER = "#c8c8c3"
BORDER_SUBTLE = "#d8d8d3"
BORDER_WHITE = "#2c2c2a"
BORDER_GLOW = "#2c2c2a"

TEXT_PRIMARY = "#1a1a18"
TEXT_SECONDARY = "#4a4a46"
TEXT_MUTED = "#8a8a84"
TEXT_PULSE = "#9a9a94"

ACCENT_BLUE = "#1a1a18"
ACCENT_RED = "#1a1a18"
ACCENT_GREEN = "#3a3a36"
ACCENT_ORANGE = "#6a6a64"
ACCENT_PURPLE = "#8a8a84"

_TAB_LABELS = [
    "Single File",
    "Benchmark",
    "Graphs",
    "Results",
    "Summary",
    "Tamper Demo",
    "System Info",
]


class AppWindow:
    """Main application window with custom header, tab bar, and status bar."""

    def __init__(self) -> None:
        self.config = load_config()
        self.root = tk.Tk()
        self.root.title(self.config.window_title)
        self.root.resizable(False, False)
        self.root.minsize(900, 600)

        # Centre on screen
        w, h = self.config.window_width, self.config.window_height
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.root.configure(bg=BG_BASE)

        # Shared status variable
        self.status_var = tk.StringVar(value="")
        self._status_level = "idle"  # idle | running | done | error
        self._status_spin_id: str | None = None
        self._status_spin_idx = 0
        _STATUS_CYCLE = "\u25D0\u25D3\u25D1\u25D2"  # ◐ ◓ ◑ ◒

        self._configure_style()
        self._build_header()
        self._build_tab_bar()
        self._build_content_area()
        self._build_status_bar()
        self._create_tabs()
        self._bind_shortcuts()
        self._set_icon()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Show first tab
        self.select_tab(0)

    # ------------------------------------------------------------------ style
    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        configure_tkinter_style(style)

    # ================================================================ HEADER
    def _build_header(self) -> None:
        header = tk.Frame(self.root, bg=BG_BASE, height=48)
        header.pack(fill="x")
        header.pack_propagate(False)

        # Left section
        left = tk.Frame(header, bg=BG_BASE)
        left.pack(side="left", fill="y")

        tk.Label(left, text="ENTROPY", font=FONT_DISPLAY,
                  bg=BG_BASE, fg=TEXT_PRIMARY).pack(side="left", padx=(PAD_LG, PAD_SM))

        # Vertical divider
        div_frame = tk.Frame(left, bg=BG_BASE, padx=PAD_MD)
        div_frame.pack(side="left", fill="y", pady=10)
        tk.Frame(div_frame, bg=BORDER, width=1).pack(fill="y", expand=True)

        tk.Label(left, text="AES Benchmark",
             font=FONT_BODY, bg=BG_BASE,
             fg=TEXT_MUTED).pack(side="left", padx=(0, PAD_MD))

        # Right section — Clear Generated button
        right = tk.Frame(header, bg=BG_BASE)
        right.pack(side="right", fill="y", padx=PAD_LG)

        clear_btn = tk.Button(
            right,
            text="\U0001F5D1  Clear Generated Files",
            command=self._clear_generated_files,
            bg=BG_BASE, fg=TEXT_MUTED,
            font=("Consolas", 9),
            relief="flat", bd=0,
            padx=8, pady=4,
            cursor="hand2",
            highlightthickness=0,
            activebackground=BG_ELEVATED,
            activeforeground=TEXT_PRIMARY,
        )
        clear_btn.pack(side="right", pady=10)
        clear_btn.bind("<Enter>", lambda _e: clear_btn.config(fg=TEXT_PRIMARY, bg=BG_ELEVATED))
        clear_btn.bind("<Leave>", lambda _e: clear_btn.config(fg=TEXT_MUTED, bg=BG_BASE))
        self._clear_btn = clear_btn

        # Bottom border
        tk.Frame(self.root, bg=BORDER_SUBTLE, height=1).pack(fill="x")

    # ============================================================== TAB BAR
    def _build_tab_bar(self) -> None:
        self._tab_bar = tk.Frame(self.root, bg=BG_BASE, height=40)
        self._tab_bar.pack(fill="x")
        self._tab_bar.pack_propagate(False)

        self._tab_buttons: list[tk.Label] = []
        self._tab_indicators: list[tk.Frame] = []
        self._active_tab = 0

        for i, label in enumerate(_TAB_LABELS):
            col = tk.Frame(self._tab_bar, bg=BG_BASE)
            col.pack(side="left")

            btn = tk.Label(
                col, text=label, font=FONT_LABEL,
                bg=BG_BASE, fg=TEXT_MUTED,
                padx=PAD_MD, pady=0, cursor="hand2",
            )
            btn.pack(pady=(10, 8))

            # 2px bottom indicator (hidden by default)
            indicator = tk.Frame(col, bg=BG_BASE, height=2)
            indicator.pack(fill="x")

            btn.bind("<Button-1>", lambda _e, idx=i: self.select_tab(idx))
            btn.bind("<Enter>", lambda _e, b=btn: self._tab_hover(b, True))
            btn.bind("<Leave>", lambda _e, b=btn, idx=i: self._tab_hover(b, False, idx))

            self._tab_buttons.append(btn)
            self._tab_indicators.append(indicator)

        # Bottom border beneath tab bar
        tk.Frame(self.root, bg=BORDER_SUBTLE, height=1).pack(fill="x")

    def _tab_hover(self, btn: tk.Label, entering: bool,
                   idx: int | None = None) -> None:
        if idx is not None and idx == self._active_tab:
            return  # don't change active tab style on hover
        if entering:
            btn.config(fg=TEXT_SECONDARY)
        else:
            btn.config(fg=TEXT_MUTED)

    # ========================================================== CONTENT AREA
    def _build_content_area(self) -> None:
        self._content = tk.Frame(self.root, bg=BG_BASE)
        self._content.pack(fill="both", expand=True)

    # ============================================================ STATUS BAR
    def _build_status_bar(self) -> None:
        bar = tk.Frame(self.root, bg=BG_BASE, height=24)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        left = tk.Frame(bar, bg=BG_BASE)
        left.pack(side="left", fill="y", padx=PAD_LG)

        tk.Label(left, textvariable=self.status_var, font=FONT_LABEL,
             bg=BG_BASE, fg=TEXT_MUTED,
             anchor="w").pack(side="left")

    def _on_status_change(self, *_args) -> None:
        """Auto-detect status level from text and recolor the dot."""
        text = self.status_var.get().lower()
        if "error" in text or "fail" in text:
            self._set_status_level("error")
        elif "running" in text or "generating" in text or "stopping" in text:
            self._set_status_level("running")
        elif "complete" in text or "done" in text or "saved" in text or "\u2713" in text:
            self._set_status_level("done")
        else:
            self._set_status_level("idle")

    def _set_status_level(self, level: str) -> None:
        """Set the status bar animation state."""
        if level == self._status_level:
            return
        self._status_level = level
        # Stop any existing spin
        if self._status_spin_id is not None:
            self.root.after_cancel(self._status_spin_id)
            self._status_spin_id = None

        if level == "running":
            self._status_spin_idx = 0
            self._tick_status_spin()
        elif level == "error":
            self._status_dot.config(text="\u25CF", fg=ACCENT_RED)
        elif level == "done":
            self._status_dot.config(text="\u25CF", fg=ACCENT_GREEN)
        else:  # idle
            self._status_dot.config(text="\u25CF", fg=TEXT_MUTED)

    _STATUS_CYCLE = "\u25D0\u25D3\u25D1\u25D2"

    def _tick_status_spin(self) -> None:
        ch = self._STATUS_CYCLE[self._status_spin_idx % 4]
        pulse_color = TEXT_PRIMARY if self._status_spin_idx % 2 else TEXT_PULSE
        self._status_dot.config(text=ch, fg=pulse_color)
        self._status_spin_idx += 1
        self._status_spin_id = self.root.after(300, self._tick_status_spin)

    # =========================================================== TAB SYSTEM
    def _create_tabs(self) -> None:
        """Instantiate all tab controllers against the shared content area."""
        self.tab_single = SingleFileTab(self._content, self.config,
                                        self.status_var, self.root)
        self.tab_benchmark = BenchmarkTab(self._content, self.config,
                                          self.status_var, self.root, self)
        self.tab_graphs = GraphsTab(self._content, self.config,
                                    self.status_var, self.root, self)
        self.tab_results = ResultsTab(self._content, self.config,
                                      self.status_var, self.root)
        self.tab_summary = SummaryTab(self._content, self.config,
                                      self.status_var, self.root, self)
        self.tab_tamper = TamperTab(self._content, self.config,
                                    self.status_var, self.root, self)
        self.tab_sysinfo = SysInfoTab(self._content, self.config,
                                      self.status_var, self.root, self)

        self._tab_frames = [
            self.tab_single.frame,
            self.tab_benchmark.frame,
            self.tab_graphs.frame,
            self.tab_results.frame,
            self.tab_summary.frame,
            self.tab_tamper.frame,
            self.tab_sysinfo.frame,
        ]

    def select_tab(self, index: int) -> None:
        """Switch to tab *index* (0-based). Public API for cross-tab navigation."""
        if hasattr(self, "tab_summary") and index == 4:
            self.tab_summary.load_summary()
        if hasattr(self, "tab_sysinfo") and index == 6:
            self.tab_sysinfo._load_info()

        # Hide all
        for f in self._tab_frames:
            f.pack_forget()

        # Show selected
        self._tab_frames[index].pack(in_=self._content, fill="both", expand=True)

        # Update button styles
        for i, (btn, ind) in enumerate(zip(self._tab_buttons, self._tab_indicators)):
            if i == index:
                btn.config(fg=TEXT_PRIMARY)
                ind.config(bg=TEXT_PRIMARY)
            else:
                btn.config(fg=TEXT_MUTED)
                ind.config(bg=BG_BASE)

        self._active_tab = index

    # -------------------------------------------------------- first launch
    def _check_first_launch(self) -> None:
        """Show a welcome dialog if all input_files subdirectories are empty."""
        input_dir = self.config.input_dir
        if not input_dir.is_dir():
            self._show_welcome()
            return
        total_files = sum(
            1 for g in self.config.file_groups
            if (input_dir / g).is_dir()
            for f in (input_dir / g).iterdir()
            if f.is_file() and f.name != ".gitkeep"
        )
        if total_files == 0:
            self._show_welcome()

    def _show_welcome(self) -> None:
        """Styled Toplevel welcome dialog guiding new users."""
        dlg = tk.Toplevel(self.root)
        dlg.title("Welcome to Entropy")
        dlg.configure(bg=BG_BASE)
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

        dw, dh = 480, 340
        x = self.root.winfo_x() + (self.config.window_width - dw) // 2
        y = self.root.winfo_y() + (self.config.window_height - dh) // 2
        dlg.geometry(f"{dw}x{dh}+{x}+{y}")

        pad = tk.Frame(dlg, bg=BG_BASE, padx=PAD_LG, pady=PAD_LG)
        pad.pack(fill="both", expand=True)

        tk.Label(pad, text="\U0001F510", bg=BG_BASE,
                 font=("Consolas", 36)).pack(pady=(0, PAD_SM))
        tk.Label(pad, text="Welcome to Entropy",
                 bg=BG_BASE, fg=ACCENT_BLUE,
                 font=FONT_DISPLAY).pack()
        tk.Label(pad, text="AES-256 Performance Benchmark Suite",
                 bg=BG_BASE, fg=TEXT_SECONDARY,
                 font=FONT_BODY).pack(pady=(PAD_XS, PAD_MD))

        steps = [
            "1.  Add test files to  data/input_files/  subfolders",
            "2.  Run the Benchmark tab to generate results",
            "3.  View graphs and results in their respective tabs",
        ]
        for step in steps:
            tk.Label(pad, text=step, bg=BG_BASE, fg=TEXT_PRIMARY,
                     font=FONT_BODY, anchor="w").pack(anchor="w",
                                                       pady=1)

        from src.ui.components import make_button
        btn = make_button(pad, text="Got it — Let\u2019s go!",
                          command=dlg.destroy)
        btn.pack(pady=(PAD_MD, 0))

    # --------------------------------------------------------------- public
    def run(self) -> None:
        """Start the Tkinter main loop."""
        self.root.mainloop()

    # ----------------------------------------------------------- shortcuts
    def _bind_shortcuts(self) -> None:
        for i in range(7):
            self.root.bind(f"<Control-Key-{i + 1}>",
                           lambda _e, idx=i: self.select_tab(idx))
        self.root.bind("<Control-q>", lambda _e: self._on_close())
        self.root.bind("<Control-Q>", lambda _e: self._on_close())

    # ---------------------------------------------------------------- icon
    def _set_icon(self) -> None:
        """Attempt to set a window icon; skip gracefully on failure."""
        try:
            img = tk.PhotoImage(width=32, height=32)
            img.put((ACCENT_BLUE,), to=(0, 0, 32, 32))
            self.root.iconphoto(False, img)
            self._icon_ref = img  # prevent GC
        except tk.TclError:
            pass

    # --------------------------------------------------------- close guard
    def _on_close(self) -> None:
        if hasattr(self, "tab_benchmark") and self.tab_benchmark._running:
            if not messagebox.askyesno(
                "Benchmark in progress",
                "A benchmark is still running.\nQuit anyway?",
            ):
                return
        self.root.destroy()

    # ---------------------------------------- clear generated files
    def _clear_generated_files(self) -> None:
        """Delete data/input_files/_generated and all its contents."""
        import shutil
        generated_root = self.config.input_dir / "_generated"
        if not generated_root.exists():
            self.status_var.set("No generated files to clear")
            return

        # Compute size before deletion
        total_bytes = sum(
            f.stat().st_size
            for f in generated_root.rglob("*")
            if f.is_file()
        )
        total_mb = total_bytes / 1_048_576

        if not messagebox.askyesno(
            "Clear Generated Files",
            f"Delete all generated benchmark files?\n"
            f"This will free approximately {total_mb:.1f} MB.\n\n"
            f"Path: {generated_root}",
        ):
            return

        try:
            shutil.rmtree(generated_root)
            self.status_var.set(
                f"Cleared generated files — freed {total_mb:.1f} MB  \u2713"
            )
        except Exception as exc:
            messagebox.showerror("Clear Failed", f"Could not delete generated files:\n{exc}")
            self.status_var.set("Clear generated files failed")
