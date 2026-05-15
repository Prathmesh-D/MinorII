"""
Reusable UI Components — Cybersecurity Terminal Theme
=====================================================
Every tab imports and uses these builders. Never build raw widgets inline.
All components source colors, fonts, and spacing from theme.py.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from src.ui.theme import (
    BG_BASE, BG_SURFACE, BG_ELEVATED, BORDER,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    ACCENT_BLUE, ACCENT_RED, ACCENT_GREEN, ACCENT_ORANGE,
    FONT_HEADING, FONT_SUBHEAD, FONT_BODY, FONT_MONO,
    FONT_METRIC, FONT_LABEL,
    PAD_LG, PAD_MD, PAD_SM, PAD_XS,
)


BG_BASE = "#f5f5f0"
BG_SURFACE = "#efefea"
BG_ELEVATED = "#e5e5e0"
BG_HOVER = "#dcdcd6"

BORDER = "#c8c8c3"
BORDER_SUBTLE = "#d8d8d3"
BORDER_STRONG = "#a0a09a"
BORDER_WHITE = "#2c2c2a"

TEXT_PRIMARY = "#1a1a18"
TEXT_SECONDARY = "#4a4a46"
TEXT_MUTED = "#8a8a84"
TEXT_INVERSE = "#f5f5f0"

ACCENT_BLUE = "#1a1a18"
ACCENT_RED = "#1a1a18"
ACCENT_GREEN = "#3a3a36"
ACCENT_ORANGE = "#6a6a64"


# ── helpers ────────────────────────────────────────────────────────────────

def _lighten(hex_color: str, amount: int = 20) -> str:
    """Return a lighter variant of *hex_color* by channel offset."""
    r = min(int(hex_color[1:3], 16) + amount, 255)
    g = min(int(hex_color[3:5], 16) + amount, 255)
    b = min(int(hex_color[5:7], 16) + amount, 255)
    return f"#{r:02x}{g:02x}{b:02x}"


def _darken(hex_color: str, amount: int = 20) -> str:
    """Return a darker variant of *hex_color* by channel offset."""
    r = max(int(hex_color[1:3], 16) - amount, 0)
    g = max(int(hex_color[3:5], 16) - amount, 0)
    b = max(int(hex_color[5:7], 16) - amount, 0)
    return f"#{r:02x}{g:02x}{b:02x}"


# ── 1. make_card ───────────────────────────────────────────────────────────

def make_card(parent):
    """Minimal surface card with only internal padding."""
    outer = tk.Frame(parent, bg=BG_SURFACE, padx=PAD_LG, pady=PAD_LG)
    outer.pack(fill="x", pady=(0, PAD_MD))
    return outer


# ── 2. make_metric_card ───────────────────────────────────────────────────

def make_metric_card(parent, label, value, unit, color):
    """Compact card showing one big metric value."""
    outer = tk.Frame(parent, bg=BG_SURFACE, padx=PAD_MD, pady=PAD_MD)
    outer.pack(side="left", fill="both", expand=True, padx=(0, PAD_MD), pady=(0, PAD_MD))

    content = tk.Frame(outer, bg=BG_SURFACE)
    content.pack(fill="both", expand=True)

    tk.Label(content, text=label, bg=BG_SURFACE, fg=TEXT_SECONDARY,
             font=FONT_LABEL).pack(anchor="w")
    tk.Label(content, text=str(value), bg=BG_SURFACE, fg=TEXT_PRIMARY,
             font=FONT_METRIC).pack(anchor="w")
    tk.Label(content, text=unit, bg=BG_SURFACE, fg=TEXT_MUTED,
             font=FONT_LABEL).pack(anchor="w")

    return outer


# ── 3. make_button ─────────────────────────────────────────────────────────

def _safe_wrap(fn):
    """Wrap a callback so exceptions show an error dialog instead of crashing."""
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            from tkinter import messagebox
            messagebox.showerror("Error", f"\u26A0 {exc}")
    return wrapper


_BUTTON_STYLES = {
    "primary": (TEXT_PRIMARY, BG_BASE),
    "danger":  (ACCENT_RED,   TEXT_INVERSE),
    "success": (ACCENT_GREEN, TEXT_INVERSE),
    "ghost":   (BG_BASE,      TEXT_MUTED),
    "disabled": (BG_ELEVATED, TEXT_MUTED),
}


def make_button(parent, text, command=None, style="primary", width=None):
    """Manually-styled tk.Button.  No ttk.

    *style*: "primary" | "danger" | "success" | "ghost" | "disabled"
    All commands are wrapped in try/except to prevent crashes.
    """
    bg, fg = _BUTTON_STYLES.get(style, _BUTTON_STYLES["primary"])
    if style == "ghost":
        active_bg = BG_BASE
        hover_bg = BG_BASE
        press_bg = BG_BASE
        hover_fg = TEXT_PRIMARY
        press_fg = TEXT_PRIMARY
        active_fg = TEXT_PRIMARY
    elif style == "disabled":
        active_bg = bg
        hover_bg = bg
        press_bg = bg
        hover_fg = fg
        press_fg = fg
        active_fg = fg
    else:
        active_bg = "#222222"
        hover_bg = "#222222"
        press_bg = "#111111"
        hover_fg = fg
        press_fg = fg
        active_fg = fg

    state = "disabled" if style == "disabled" else "normal"
    cursor = "hand2" if style != "disabled" else ""

    # Wrap command in error handler
    safe_cmd = _safe_wrap(command) if command is not None else None

    btn = tk.Button(
        parent, text=text, command=safe_cmd,
        bg=bg, fg=fg, font=FONT_SUBHEAD,
        activebackground=active_bg, activeforeground=active_fg,
        relief="flat", bd=0, cursor=cursor,
        padx=16, pady=8,
        state=state,
        highlightthickness=0,
    )
    if style == "primary":
        btn.config(height=1)
    if style == "ghost":
        btn.config(bg=BG_BASE, relief="flat", bd=0, padx=0, pady=0)
    if width is not None:
        btn.config(width=width)

    # Hover / press bindings
    if style != "disabled":
        btn._base_bg = bg  # type: ignore[attr-defined]
        btn._hover_bg = hover_bg  # type: ignore[attr-defined]
        btn._press_bg = press_bg  # type: ignore[attr-defined]
        btn._base_fg = fg  # type: ignore[attr-defined]
        btn._hover_fg = hover_fg  # type: ignore[attr-defined]
        btn._press_fg = press_fg  # type: ignore[attr-defined]
        btn.bind("<Enter>", lambda _e, b=btn: b.config(bg=b._hover_bg, fg=b._hover_fg))
        btn.bind("<Leave>", lambda _e, b=btn: b.config(bg=b._base_bg, fg=b._base_fg))
        btn.bind("<ButtonPress-1>",
                 lambda _e, b=btn: b.config(bg=b._press_bg, fg=b._press_fg))
        btn.bind("<ButtonRelease-1>",
                 lambda _e, b=btn: b.config(bg=b._hover_bg, fg=b._hover_fg))
    return btn


# ── 4. make_divider ───────────────────────────────────────────────────────

def make_divider(parent):
    """Subtle 1px divider line."""
    div = tk.Frame(parent, bg=BORDER_SUBTLE, height=1)
    div.pack(fill="x")
    return div


# ── 5. make_tag ───────────────────────────────────────────────────────────

def make_tag(parent, text, color):
    """Small flat inline tag."""
    lbl = tk.Label(
        parent, text=text,
        bg=BG_ELEVATED, fg=TEXT_SECONDARY,
        font=FONT_LABEL, padx=6, pady=2,
        bd=0, relief="flat",
        highlightthickness=0,
    )
    return lbl


# ── 6. section helpers ────────────────────────────────────────────────────

def make_section_label(parent, text):
    """Muted section label with only bottom spacing."""
    lbl = tk.Label(parent, text=text, fg=TEXT_MUTED, font=FONT_LABEL, anchor="w")
    lbl.pack(fill="x", padx=0, pady=(0, PAD_SM))
    return lbl


def make_data_row(parent, label, value, value_color=TEXT_PRIMARY):
    """Two-column data row with label left and value right."""
    row = tk.Frame(parent)
    row.pack(fill="x", pady=PAD_XS)

    tk.Label(row, text=label, fg=TEXT_MUTED, font=FONT_LABEL,
             anchor="w").pack(side="left")
    tk.Label(row, text=value, fg=value_color, font=FONT_BODY,
             anchor="e").pack(side="right")

    return row


# ── 7. make_log_window ────────────────────────────────────────────────────

def make_log_window(parent, height=10):
    """Dark terminal-style log pane with scrollbar.

    The returned Text widget has an extra ``append_line(text, tag=None)``
    helper that handles the enable→insert→disable dance automatically.
    """
    frame = tk.Frame(parent, bg=BG_BASE)
    frame.pack(fill="both", expand=True, pady=(0, PAD_MD))

    inner = tk.Frame(frame, bg=BG_BASE)
    inner.pack(fill="both", expand=True)

    txt = tk.Text(
        inner, height=height,
        bg=BG_BASE, fg=TEXT_PRIMARY, font=FONT_MONO,
        insertbackground=TEXT_PRIMARY,
        relief="flat", bd=0, wrap="none",
        state="disabled",
        highlightthickness=0,
    )
    sb = tk.Scrollbar(
        inner, orient="vertical", command=txt.yview,
        bg=BG_ELEVATED, troughcolor=BG_BASE,
        highlightthickness=0, bd=0,
    )
    txt.config(yscrollcommand=sb.set)
    txt.tag_configure("ctr", foreground=TEXT_PRIMARY)
    txt.tag_configure("gcm", foreground=TEXT_PRIMARY)
    txt.tag_configure("info", foreground=TEXT_MUTED)
    txt.tag_configure("error", foreground=TEXT_PRIMARY,
                      font=(FONT_MONO[0], FONT_MONO[1], "bold"))
    txt.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")

    # ── append helper ──
    def _append_line(line: str, tag: str | None = None) -> None:
        txt.config(state="normal")
        if tag:
            txt.insert("end", line + "\n", tag)
        else:
            txt.insert("end", line + "\n")
        txt.see("end")
        txt.config(state="disabled")

    txt.append_line = _append_line  # type: ignore[attr-defined]
    txt._outer_frame = frame        # type: ignore[attr-defined]

    return txt


# ── 8. make_progress_bar ──────────────────────────────────────────────────

def make_progress_bar(parent, label_text=""):
    """Styled progress container.

    Returns ``(container_frame, progressbar, label_var)``.
    """
    container = tk.Frame(parent, bg=BG_BASE)
    container.pack(fill="x", pady=PAD_XS)

    label_var = tk.StringVar(value=label_text)
    tk.Label(container, textvariable=label_var, bg=BG_BASE,
             fg=TEXT_SECONDARY, font=FONT_LABEL,
             anchor="w").pack(fill="x")

    style = ttk.Style(container)
    style_name = "Research.Horizontal.TProgressbar"
    style.configure(style_name,
                    troughcolor=BG_ELEVATED,
                    background=TEXT_PRIMARY,
                    borderwidth=0)

    bar = ttk.Progressbar(container, mode="determinate", style=style_name)
    bar.pack(fill="x", pady=(PAD_XS, 0))

    return container, bar, label_var


# ── 9. make_status_indicator ──────────────────────────────────────────────

_STATUS_COLORS = {
    "success": ACCENT_GREEN,
    "warning": ACCENT_ORANGE,
    "error":   ACCENT_RED,
    "neutral": TEXT_MUTED,
}


def make_status_indicator(parent, text, status="neutral"):
    """Inline indicator: colored dot + label.

    *status*: "success" | "warning" | "error" | "neutral"
    """
    color = _STATUS_COLORS.get(status, TEXT_MUTED)
    text_color = TEXT_PRIMARY
    text_font = FONT_LABEL
    if status == "warning":
        text_color = TEXT_SECONDARY
    elif status == "neutral":
        text_color = TEXT_MUTED
    elif status == "error":
        text_font = (FONT_LABEL[0], FONT_LABEL[1], "bold")

    frame = tk.Frame(parent, bg=BG_BASE)

    dot = tk.Label(frame, text="\u25CF", bg=BG_BASE, fg=color,
                   font=("Consolas", 8))
    dot.pack(side="left", padx=(0, PAD_XS))

    lbl = tk.Label(frame, text=text, bg=BG_BASE, fg=text_color,
                   font=text_font)
    lbl.pack(side="left")

    return frame


# ── 10. ToolTip ────────────────────────────────────────────────────────────

class ToolTip:
    """Simple hover tooltip using a styled Toplevel window."""

    def __init__(self, widget: tk.Widget, text: str, delay: int = 400):
        self.widget = widget
        self.text = text
        self.delay = delay
        self._tip: tk.Toplevel | None = None
        self._after_id: str | None = None

        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _event=None):
        self._cancel()
        self._after_id = self.widget.after(self.delay, self._show)

    def _show(self):
        if self._tip:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self._tip = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        frame = tk.Frame(tw, bg=BORDER, padx=1, pady=1)
        frame.pack()
        tk.Label(frame, text=self.text, bg=BG_ELEVATED, fg=TEXT_PRIMARY,
                 font=FONT_LABEL, padx=PAD_SM, pady=PAD_XS,
                 wraplength=300, justify="left").pack()

    def _hide(self, _event=None):
        self._cancel()
        if self._tip:
            self._tip.destroy()
            self._tip = None

    def _cancel(self):
        if self._after_id:
            self.widget.after_cancel(self._after_id)
            self._after_id = None


def add_tooltip(widget: tk.Widget, text: str, delay: int = 400) -> ToolTip:
    """Attach a hover tooltip to any widget."""
    return ToolTip(widget, text, delay)
