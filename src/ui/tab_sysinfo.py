"""Tab 7 — System Information & Run Configuration."""

from __future__ import annotations

import platform
import subprocess
import sys
import tkinter as tk
from pathlib import Path

from src.benchmark.experiment_config import Config
from src.ui.theme import (
    BG_BASE, BG_SURFACE, BG_ELEVATED,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    ACCENT_BLUE, ACCENT_GREEN, ACCENT_ORANGE,
    FONT_HEADING, FONT_SUBHEAD, FONT_BODY, FONT_LABEL, FONT_MONO,
    PAD_LG, PAD_MD, PAD_SM, PAD_XS,
)
from src.ui.components import make_button, make_metric_card, make_section_label


def _get_openssl_version() -> str:
    try:
        from cryptography.hazmat.backends.openssl.backend import backend as _be
        return _be.openssl_version_text()
    except Exception:
        return "unknown"


def _get_cpu() -> str:
    return platform.processor() or platform.machine() or "unknown"


def _get_ram_str() -> str:
    try:
        import psutil
        gb = psutil.virtual_memory().total / 1_073_741_824
        return f"{gb:.1f} GB"
    except ImportError:
        return "n/a  (pip install psutil)"


def _get_cpu_cores() -> str:
    try:
        import psutil
        phys = psutil.cpu_count(logical=False) or "?"
        logi = psutil.cpu_count(logical=True) or "?"
        return f"{phys} physical / {logi} logical"
    except ImportError:
        import os
        count = os.cpu_count()
        return f"{count} logical" if count else "unknown"


def _check_aes_ni() -> tuple[str, str]:
    """Return (status_text, color) for AES-NI availability."""
    cpu_flags = ""
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["wmic", "cpu", "get", "Caption"],
                capture_output=True, text=True, timeout=3,
            )
            cpu_flags = result.stdout.lower()
        else:
            with open("/proc/cpuinfo", "r") as f:
                cpu_flags = f.read().lower()
    except Exception:
        pass

    if "aes" in cpu_flags or "aesni" in cpu_flags:
        return "Detected  (likely active via OpenSSL)", ACCENT_GREEN
    # If we can't detect, mention OpenSSL auto-uses it
    return "Not confirmed  (OpenSSL enables if available)", ACCENT_ORANGE


class SysInfoTab:
    """Display system hardware, software environment, and benchmark config."""

    def __init__(self, parent: tk.Frame, config: Config,
                 status_var: tk.StringVar, root: tk.Tk, app=None) -> None:
        self.config = config
        self.status_var = status_var
        self.root = root
        self.app = app

        self.frame = tk.Frame(parent, bg=BG_BASE)
        self._build_ui()
        self._load_info()

    # ================================================================ BUILD
    def _build_ui(self) -> None:
        outer = tk.Frame(self.frame, bg=BG_BASE)
        outer.pack(fill="both", expand=True)

        self._build_header(outer)

        scroll_wrap = tk.Frame(outer, bg=BG_BASE)
        scroll_wrap.pack(fill="both", expand=True, padx=PAD_LG, pady=(0, PAD_MD))

        self._canvas = tk.Canvas(scroll_wrap, bg=BG_BASE, highlightthickness=0)
        self._vscroll = tk.Scrollbar(
            scroll_wrap, orient="vertical", command=self._canvas.yview,
            bg=BG_ELEVATED, troughcolor=BG_BASE, highlightthickness=0, bd=0,
        )
        self._canvas.configure(yscrollcommand=self._vscroll.set)
        self._vscroll.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self._content = tk.Frame(self._canvas, bg=BG_BASE)
        self._cid = self._canvas.create_window((0, 0), window=self._content, anchor="nw")

        self._content.bind("<Configure>", self._on_content_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self._canvas.bind("<MouseWheel>", self._on_mousewheel)

        # KPI cards host
        self._hw_host = tk.Frame(self._content, bg=BG_BASE)
        self._hw_host.pack(fill="x", pady=(0, PAD_SM))

        # Detail text
        make_section_label(self._content, "Full Detail")
        self._detail_text = tk.Text(
            self._content,
            height=12,
            bg=BG_SURFACE,
            fg=TEXT_PRIMARY,
            font=("Consolas", 9),
            relief="flat", bd=0,
            wrap="none",
            highlightthickness=0,
            state="disabled",
            padx=PAD_SM, pady=PAD_SM,
        )
        self._detail_text.pack(fill="x", pady=(0, PAD_MD))

        make_section_label(self._content, "Benchmark Configuration")
        self._cfg_text = tk.Text(
            self._content,
            height=8,
            bg=BG_SURFACE,
            fg=TEXT_PRIMARY,
            font=("Consolas", 9),
            relief="flat", bd=0,
            wrap="none",
            highlightthickness=0,
            state="disabled",
            padx=PAD_SM, pady=PAD_SM,
        )
        self._cfg_text.pack(fill="x")

    def _on_content_configure(self, _e) -> None:
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event) -> None:
        self._canvas.itemconfig(self._cid, width=event.width)

    def _on_mousewheel(self, event) -> None:
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _build_header(self, parent: tk.Frame) -> None:
        bar = tk.Frame(parent, bg=BG_BASE)
        bar.pack(fill="x", padx=PAD_LG, pady=PAD_MD)

        left = tk.Frame(bar, bg=BG_BASE)
        left.pack(side="left")
        tk.Label(left, text="System Info", bg=BG_BASE, fg=TEXT_PRIMARY,
                 font=FONT_HEADING).pack(anchor="w")
        tk.Label(left, text="Hardware, software, and OpenSSL environment",
                 bg=BG_BASE, fg=TEXT_MUTED, font=FONT_LABEL).pack(anchor="w")

        right = tk.Frame(bar, bg=BG_BASE)
        right.pack(side="right")
        make_button(right, text="Refresh", command=self._load_info,
                    style="ghost").pack(side="left")

    # ================================================================ LOAD
    def _load_info(self) -> None:
        cpu        = _get_cpu()
        cpu_cores  = _get_cpu_cores()
        ram        = _get_ram_str()
        py_ver     = platform.python_version()
        py_impl    = platform.python_implementation()
        os_name    = f"{platform.system()} {platform.release()} ({platform.machine()})"
        openssl    = _get_openssl_version()
        aes_ni, aes_ni_color = _check_aes_ni()

        # ── KPI cards row 1 ──
        for w in self._hw_host.winfo_children():
            w.destroy()

        row1 = tk.Frame(self._hw_host, bg=BG_BASE)
        row1.pack(fill="x")

        make_metric_card(row1, label="Operating System",
                         value=platform.system(), unit=platform.release(),
                         color=ACCENT_BLUE)
        make_metric_card(row1, label="Python",
                         value=py_ver, unit=py_impl,
                         color=ACCENT_BLUE)
        make_metric_card(row1, label="CPU Cores",
                         value=cpu_cores.split("/")[0].strip(),
                         unit=cpu_cores.split("/")[-1].strip() if "/" in cpu_cores else "logical",
                         color=ACCENT_GREEN)
        make_metric_card(row1, label="RAM",
                         value=ram.split(" ")[0],
                         unit=ram.split(" ")[-1] if " " in ram else ram,
                         color=ACCENT_GREEN)

        row2 = tk.Frame(self._hw_host, bg=BG_BASE)
        row2.pack(fill="x")
        make_metric_card(row2, label="AES-NI",
                         value="Detected" if "Detected" in aes_ni else "Unconfirmed",
                         unit="hardware acceleration",
                         color=aes_ni_color)
        make_metric_card(row2, label="OpenSSL",
                         value=openssl.split(" ")[1] if len(openssl.split(" ")) > 1 else openssl[:12],
                         unit=openssl.split(" ")[0] if openssl != "unknown" else "unavailable",
                         color=ACCENT_BLUE)
        make_metric_card(row2, label="Benchmark Runs",
                         value=str(self.config.runs),
                         unit=f"warmup = {self.config.warmup_runs}",
                         color=ACCENT_ORANGE)
        make_metric_card(row2, label="Kept Runs",
                         value=str(self.config.runs - self.config.warmup_runs),
                         unit="per experiment",
                         color=ACCENT_ORANGE)

        # ── Full detail block ──
        detail_lines = [
            f"  CPU Model    : {cpu}",
            f"  CPU Cores    : {cpu_cores}",
            f"  RAM          : {ram}",
            f"  OS           : {os_name}",
            f"  Python       : {py_ver}  ({py_impl}  {sys.version.split()[0]})",
            f"  OpenSSL      : {openssl}",
            f"  AES-NI       : {aes_ni}",
            f"  Script path  : {Path(sys.argv[0]).resolve() if sys.argv else 'unknown'}",
        ]
        self._set_text(self._detail_text, "\n".join(detail_lines))

        # ── Config block ──
        groups_str = "  " + "\n  ".join(self.config.file_groups)
        cfg_lines = [
            f"  Config file  : config.ini",
            f"  Input dir    : {self.config.input_dir}",
            f"  Results dir  : {self.config.results_dir}",
            f"  CSV file     : {self.config.csv_file}",
            f"  Graphs dir   : {self.config.graphs_dir}",
            f"  Runs         : {self.config.runs}",
            f"  Warmup runs  : {self.config.warmup_runs}",
            f"  Key size     : {self.config.key_size_bytes * 8}-bit  ({self.config.key_size_bytes} bytes)",
            f"  CTR nonce    : {self.config.ctr_nonce_size} bytes",
            f"  GCM nonce    : {self.config.gcm_nonce_size} bytes  (NIST-recommended 96-bit)",
            f"  GCM tag      : {self.config.gcm_tag_length} bytes  (128-bit tag)",
            f"  File groups  :\n{groups_str}",
        ]
        self._set_text(self._cfg_text, "\n".join(cfg_lines))
        self.status_var.set("System info loaded")

    @staticmethod
    def _set_text(widget: tk.Text, text: str) -> None:
        widget.config(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.config(state="disabled")
