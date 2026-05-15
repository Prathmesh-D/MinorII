"""
Shared Design System — Research Instrument Theme
================================================
Every tab imports and uses these values. Never hardcode colors or fonts.

Aesthetic: pure monochrome minimalism. The interface should read like an
academic instrument: black, white, and measured greys only.
"""

import tkinter as tk

# ── COLOR PALETTE ──────────────────────────────────────────────────────────

BG_BASE      = "#f5f5f0"   # warm off-white base
BG_SURFACE   = "#efefea"   # cards and panel surfaces
BG_ELEVATED  = "#e5e5e0"   # raised elements

BORDER       = "#c8c8c3"   # default borders
BORDER_GLOW  = "#2c2c2a"   # active/focus border contrast

TEXT_PRIMARY   = "#1a1a18" # main text
TEXT_SECONDARY = "#4a4a46" # labels and captions
TEXT_MUTED     = "#8a8a84" # placeholders and disabled states

ACCENT_BLUE   = "#1a1a18"  # primary semantic accent
ACCENT_RED    = "#1a1a18"  # danger semantic accent
ACCENT_GREEN  = "#3a3a36"  # success semantic accent
ACCENT_ORANGE = "#6a6a64"  # warning semantic accent
ACCENT_PURPLE = "#8a8a84"  # subtle semantic accent

GLOW_BLUE   = "#e5e5e0"    # neutral elevated tint replacement
GLOW_RED    = "#e5e5e0"    # neutral elevated tint replacement
GLOW_GREEN  = "#e5e5e0"    # neutral elevated tint replacement
GLOW_PURPLE = "#e5e5e0"    # neutral elevated tint replacement

# ── TYPOGRAPHY ─────────────────────────────────────────────────────────────
# Consolas: monospace, ships with Windows, technical + precise.
# Courier New: for raw hex / binary data.

FONT_DISPLAY = ("Consolas", 22, "bold")   # header title
FONT_HEADING = ("Consolas", 13, "bold")   # section headings
FONT_SUBHEAD = ("Consolas", 11, "bold")   # card titles
FONT_BODY    = ("Consolas", 10)           # general text
FONT_MONO    = ("Courier New", 9)         # hex values, raw data
FONT_METRIC  = ("Consolas", 20, "bold")   # large metric numbers
FONT_LABEL   = ("Consolas", 9)            # small labels, captions

# ── SPACING ────────────────────────────────────────────────────────────────

PAD_XL = 32
PAD_LG = 24
PAD_MD = 16
PAD_SM = 8
PAD_XS = 4
RADIUS = 6

# ── COMPONENT HELPERS ──────────────────────────────────────────────────────

def configure_tkinter_style(style):
    """Apply the design system to a ttk.Style instance.

    Called once from AppWindow. Handles Notebook, Treeview, Progressbar,
    Combobox — the ttk widgets we still need. Everything else is pure tk.
    """
    style.theme_use("clam")

    # Base
    style.configure(".", background=BG_BASE, foreground=TEXT_PRIMARY,
                    fieldbackground=BG_ELEVATED, borderwidth=0,
                    font=FONT_BODY)

    # Notebook
    style.configure("TNotebook", background=BG_BASE, borderwidth=0,
                    tabmargins=[0, 0, 0, 0])
    style.configure("TNotebook.Tab",
                    background=BG_ELEVATED, foreground=TEXT_SECONDARY,
                    padding=[16, 8], font=FONT_BODY)
    style.map("TNotebook.Tab",
              background=[("selected", BG_SURFACE)],
              foreground=[("selected", TEXT_PRIMARY)])

    # Frames (only for ttk.Frame still used by Notebook pages)
    style.configure("TFrame", background=BG_BASE)

    # Treeview
    style.configure("Treeview",
                    background=BG_SURFACE, foreground=TEXT_PRIMARY,
                    fieldbackground=BG_SURFACE, rowheight=26,
                    font=FONT_LABEL, borderwidth=0)
    style.configure("Treeview.Heading",
                    background=BG_ELEVATED, foreground=TEXT_PRIMARY,
                    font=FONT_LABEL, borderwidth=0, relief="flat")
    style.map("Treeview",
              background=[("selected", BG_ELEVATED)],
              foreground=[("selected", TEXT_PRIMARY)])

    # Progressbar
    style.configure("Horizontal.TProgressbar",
                    troughcolor=BG_ELEVATED, background=TEXT_PRIMARY,
                    borderwidth=0, thickness=6)
    style.configure("Green.Horizontal.TProgressbar",
                    troughcolor=BG_ELEVATED, background=TEXT_PRIMARY,
                    borderwidth=0, thickness=6)

    # Combobox
    style.configure("TCombobox",
                    fieldbackground=BG_ELEVATED, foreground=TEXT_PRIMARY,
                    background=BG_ELEVATED, arrowcolor=TEXT_SECONDARY,
                    borderwidth=0)
    style.map("TCombobox",
              fieldbackground=[("readonly", BG_ELEVATED)],
              foreground=[("readonly", TEXT_PRIMARY)])

    # Checkbutton
    style.configure("TCheckbutton",
                    background=BG_BASE, foreground=TEXT_PRIMARY,
                    font=FONT_LABEL)
    style.map("TCheckbutton",
              background=[("active", BG_BASE)])

    # Scrollbar
    style.configure("TScrollbar",
                    background=BG_ELEVATED, troughcolor=BG_BASE,
                    arrowcolor=TEXT_MUTED, borderwidth=0)


def make_entry(parent, textvariable=None, **kwargs):
    """Create a manually-styled tk.Entry."""
    return tk.Entry(
        parent, textvariable=textvariable,
        bg=BG_ELEVATED, fg=TEXT_PRIMARY,
        insertbackground=TEXT_PRIMARY,
        font=FONT_BODY, relief="flat", bd=0,
        highlightthickness=0,
        **kwargs,
    )
