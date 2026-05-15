"""Tab 2 — Full Benchmark Suite."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from pathlib import Path

from src.benchmark.benchmark_runner import BenchmarkRunner
from src.benchmark.generated_files import (
    BYTES_PER_MB,
    GENERATED_PROFILES,
    build_generated_dataset,
    parse_group_size_mb,
)
from src.benchmark.experiment_config import Config
from src.logging.csv_logger import CSVLogger
from src.metrics.overhead_calculator import calculate_overhead_percent
from src.metrics.throughput_calculator import calculate_throughput
from src.ui.theme import (
    BG_BASE, BG_SURFACE, BG_ELEVATED, BORDER, BORDER_GLOW,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    ACCENT_BLUE, ACCENT_RED, ACCENT_GREEN, ACCENT_ORANGE,
    GLOW_BLUE, GLOW_GREEN,
    FONT_HEADING, FONT_SUBHEAD, FONT_BODY, FONT_MONO,
    FONT_METRIC, FONT_LABEL,
    PAD_LG, PAD_MD, PAD_SM, PAD_XS,
)
from src.ui.components import (
    make_button, make_section_label, make_log_window,
)


class BenchmarkTab:
    """Configure, run, and monitor the full benchmark suite."""

    def __init__(self, parent: tk.Frame, config: Config,
                 status_var: tk.StringVar, root: tk.Tk, app) -> None:
        self.config = config
        self.status_var = status_var
        self.root = root
        self.app = app
        self.runner = BenchmarkRunner()
        self._running = False
        self._stop_flag = False
        self._progress_mode = "AES-CTR"
        self._progress_last_run = 0
        self._input_mode = tk.StringVar(value="manual")
        self._generated_files_per_group = len(GENERATED_PROFILES)

        self.frame = tk.Frame(parent, bg=BG_BASE)
        self._build_ui()
        self._discover_files()

    # ================================================================ BUILD
    def _build_ui(self) -> None:
        outer = tk.Frame(self.frame, bg=BG_BASE)
        outer.pack(fill="both", expand=True)

        # ── Left sidebar (280px) ──
        self._sidebar = tk.Frame(outer, bg=BG_SURFACE, width=280)
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)

        # 1px right border
        tk.Frame(outer, bg=BORDER, width=1).pack(side="left", fill="y")

        # ── Main area ──
        self._main = tk.Frame(outer, bg=BG_BASE)
        self._main.pack(side="left", fill="both", expand=True)

        self._build_sidebar()
        self._build_main()

    # ========================================================= LEFT SIDEBAR
    def _build_sidebar(self) -> None:
        sb = self._sidebar
        pad = tk.Frame(sb, bg=BG_SURFACE)
        pad.pack(fill="both", expand=True, padx=PAD_LG, pady=PAD_LG)

        tk.Label(
            pad,
            text="Benchmark Source",
            bg=BG_SURFACE,
            fg=TEXT_MUTED,
            font=FONT_LABEL,
            anchor="w",
        ).pack(anchor="w", pady=(0, PAD_XS))

        mode_wrap = tk.Frame(pad, bg=BG_ELEVATED, height=34)
        mode_wrap.pack(fill="x", pady=(0, PAD_MD))
        mode_wrap.pack_propagate(False)
        mode_wrap.grid_columnconfigure(0, weight=1)
        mode_wrap.grid_columnconfigure(1, weight=1)

        self._source_manual_btn = tk.Button(
            mode_wrap,
            text="Manual Files",
            command=lambda: self._set_input_mode("manual"),
            relief="flat",
            bd=0,
            highlightthickness=0,
            cursor="hand2",
            font=FONT_LABEL,
        )
        self._source_manual_btn.grid(row=0, column=0, sticky="nsew")

        self._source_generated_btn = tk.Button(
            mode_wrap,
            text="Generated",
            command=lambda: self._set_input_mode("generated"),
            relief="flat",
            bd=0,
            highlightthickness=0,
            cursor="hand2",
            font=FONT_LABEL,
        )
        self._source_generated_btn.grid(row=0, column=1, sticky="nsew")

        tk.Label(
            pad,
            text="File Groups",
            bg=BG_SURFACE,
            fg=TEXT_MUTED,
            font=FONT_LABEL,
            anchor="w",
        ).pack(anchor="w", pady=(0, PAD_SM))

        self.check_frame = tk.Frame(pad, bg=BG_SURFACE)
        self.check_frame.pack(fill="x")
        self.group_vars: dict[str, tk.BooleanVar] = {}

        self._summary_line = tk.Label(
            pad,
            text="-- files · -- runs total",
            bg=BG_SURFACE,
            fg=TEXT_MUTED,
            font=FONT_LABEL,
            anchor="w",
        )
        self._summary_line.pack(fill="x", pady=(PAD_SM, 0))

        tk.Frame(pad, bg=BG_SURFACE).pack(fill="both", expand=True)

        self.start_btn = make_button(pad, text="Start Benchmark",
                                     command=self._start_benchmark)
        self.start_btn.pack(fill="x", side="bottom")
        self.start_btn.config(pady=10)

        self.stop_btn = make_button(pad, text="\u23F9  Stop",
                                    command=self._stop_benchmark, style="danger")
        self.stop_btn.pack(fill="x", side="bottom", pady=(0, PAD_XS))
        self.stop_btn.config(pady=10)
        self.stop_btn.pack_forget()  # hidden until running

        self._sync_input_mode_buttons()

    def _set_input_mode(self, mode: str) -> None:
        if mode not in {"manual", "generated"}:
            return
        self._input_mode.set(mode)
        self._sync_input_mode_buttons()
        self._update_summary()

    def _sync_input_mode_buttons(self) -> None:
        active_bg = TEXT_PRIMARY
        active_fg = BG_BASE
        inactive_bg = BG_ELEVATED
        inactive_fg = TEXT_MUTED

        if self._input_mode.get() == "manual":
            self._source_manual_btn.config(bg=active_bg, fg=active_fg)
            self._source_generated_btn.config(bg=inactive_bg, fg=inactive_fg)
            self.start_btn.config(text="Start Benchmark")
        else:
            self._source_manual_btn.config(bg=inactive_bg, fg=inactive_fg)
            self._source_generated_btn.config(bg=active_bg, fg=active_fg)
            self.start_btn.config(text="Generate + Run")

    # ============================================================ MAIN AREA
    def _build_main(self) -> None:
        m = self._main
        self._container = tk.Frame(m, bg=BG_BASE)
        self._container.pack(fill="both", expand=True, padx=PAD_MD, pady=PAD_SM)
        container = self._container

        # ── Section: Progress (hidden until start) ──
        self._progress_section = tk.Frame(container, bg=BG_BASE)
        # Will be packed at top of container when benchmark starts

        op_row = tk.Frame(self._progress_section, bg=BG_BASE)
        op_row.pack(fill="x", pady=(0, PAD_SM))

        self.current_label = tk.Label(op_row, text="",
                                      bg=BG_BASE, fg=TEXT_PRIMARY,
                                      font=FONT_SUBHEAD, anchor="w")
        self.current_label.pack(side="left", fill="x", expand=True)

        self._run_progress_label = tk.Label(op_row, text="",
                                            bg=BG_BASE, fg=TEXT_MUTED,
                                            font=FONT_LABEL, anchor="w")
        self._run_progress_label.pack(side="left")

        self._pct_label = tk.Label(op_row, text="0%", bg=BG_BASE,
                                   fg=TEXT_MUTED, font=FONT_LABEL)
        self._pct_label.pack(side="right")

        style = ttk.Style(self._progress_section)
        style.configure("BenchmarkThin.Horizontal.TProgressbar",
                        troughcolor=BG_ELEVATED, background=TEXT_PRIMARY,
                        borderwidth=0, thickness=2)
        self.overall_progress = ttk.Progressbar(self._progress_section,
                                                mode="determinate",
                                                style="BenchmarkThin.Horizontal.TProgressbar")
        self.overall_progress.pack(fill="x", pady=(PAD_XS, PAD_SM))

        # ── Section: Live Log ──
        self._log_header = make_section_label(container, "Live Log")
        self.log_text = make_log_window(container, height=8)
        self.log_text.config(font=FONT_BODY)
        # configure color tags
        self.log_text.tag_configure("ctr", foreground=ACCENT_BLUE)
        self.log_text.tag_configure("gcm", foreground=ACCENT_RED)
        self.log_text.tag_configure("gen", foreground=ACCENT_ORANGE)
        self.log_text.tag_configure("info", foreground=TEXT_SECONDARY)
        self.log_text.tag_configure("error", foreground=ACCENT_RED,
                        font=(FONT_BODY[0], FONT_BODY[1], "bold"))

        # ── Section: Live Results Table ──
        make_section_label(container, "Live Results")
        tree_frame = tk.Frame(container, bg=BG_BASE)
        tree_frame.pack(fill="both", expand=True, pady=PAD_XS)

        cols = ("group", "file", "mode", "enc", "dec", "throughput", "overhead")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=8)
        for cid, heading, w in [
            ("group",      "Group",       90),
            ("file",       "File",       130),
            ("mode",       "Mode",        70),
            ("enc",        "Enc (ms)",    90),
            ("dec",        "Dec (ms)",    90),
            ("throughput", "Throughput",   90),
            ("overhead",   "Overhead %",  90),
        ]:
            self.tree.heading(cid, text=heading)
            self.tree.column(cid, width=w, anchor="center")

        tsb = tk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview,
                           bg=BG_ELEVATED, troughcolor=BG_BASE,
                           highlightthickness=0, bd=0)
        self.tree.config(yscrollcommand=tsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        tsb.pack(side="right", fill="y")

        # Flat table styling (no alternating tint)
        self.tree.tag_configure("row", background=BG_BASE)

        # ── Completion banner (hidden initially) ──
        self._done_banner = tk.Frame(container, bg=GLOW_GREEN)
        # populated after completion

        self._done_buttons = tk.Frame(container, bg=BG_BASE)
        # populated after completion

    # ========================================================= DISCOVERY
    def _discover_files(self) -> None:
        for w in self.check_frame.winfo_children():
            w.destroy()
        self.group_vars.clear()

        total_files = 0
        for group in self.config.file_groups:
            group_dir = self.config.input_dir / group
            count = 0
            if group_dir.is_dir():
                count = len([f for f in group_dir.iterdir()
                             if f.is_file() and f.name != ".gitkeep"])

            var = tk.BooleanVar(value=True)
            self.group_vars[group] = var

            row = tk.Frame(self.check_frame, bg=BG_SURFACE)
            row.pack(fill="x", pady=(0, PAD_XS))

            group_id = group
            group_size = ""
            if "_" in group:
                parts = group.split("_", 1)
                group_id = parts[0]
                group_size = parts[1].replace("MB", " MB")

            cb = tk.Checkbutton(row, variable=var, text=group_id,
                                bg=BG_SURFACE, fg=TEXT_PRIMARY,
                                selectcolor=BG_ELEVATED, font=FONT_BODY,
                                activebackground=BG_SURFACE,
                                activeforeground=TEXT_PRIMARY,
                                highlightthickness=0, bd=0,
                                command=self._update_summary)
            cb.pack(side="left")

            if group_size:
                tk.Label(row, text=group_size, bg=BG_SURFACE,
                         fg=TEXT_MUTED, font=FONT_LABEL).pack(side="right")
            total_files += count

        self._file_counts = {
            g: len([f for f in (self.config.input_dir / g).iterdir()
                    if f.is_file() and f.name != ".gitkeep"])
            if (self.config.input_dir / g).is_dir() else 0
            for g in self.config.file_groups
        }
        self._update_summary()

    def _update_summary(self) -> None:
        selected = [g for g, v in self.group_vars.items() if v.get()]
        if self._input_mode.get() == "generated":
            total_files = len(selected) * self._generated_files_per_group
            total_runs = total_files * self.config.runs * 2
            try:
                total_mb = sum(parse_group_size_mb(g) for g in selected) * self._generated_files_per_group
                self._summary_line.config(
                    text=(
                        f"{total_files} generated files ({total_mb} MB) "
                        f"· {total_runs} runs total"
                    )
                )
            except ValueError:
                self._summary_line.config(
                    text=f"{total_files} generated files · {total_runs} runs total"
                )
        else:
            total_files = sum(self._file_counts.get(g, 0) for g in selected)
            total_runs = total_files * self.config.runs * 2
            self._summary_line.config(text=f"{total_files} files · {total_runs} runs total")

    # ========================================================= LOG HELPER
    def _log(self, msg: str, tag: str = "info") -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.append_line(f"  {ts}  {msg}", tag)

    # ======================================================== CONTROLS
    def _start_benchmark(self) -> None:
        selected = [g for g, v in self.group_vars.items() if v.get()]
        if not selected:
            messagebox.showwarning("No Groups", "Select at least one file group.")
            return

        input_mode = self._input_mode.get()
        if input_mode == "generated":
            try:
                for group in selected:
                    parse_group_size_mb(group)
            except ValueError as exc:
                messagebox.showerror("Invalid Group Name", str(exc))
                return

        self._running = True
        self._stop_flag = False
        self.start_btn.config(state="disabled")
        self._source_manual_btn.config(state="disabled", cursor="")
        self._source_generated_btn.config(state="disabled", cursor="")
        self.stop_btn.pack(fill="x")  # show stop
        self._progress_mode = "AES-CTR"
        self._progress_last_run = 0

        # Show progress section at top of container
        self._progress_section.pack(fill="x", pady=(0, PAD_SM),
                                    before=self._log_header)

        # Clear state
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._row_count = 0
        self.overall_progress.config(value=0)
        self._pct_label.config(text="0%")
        self._run_progress_label.config(text="")

        # Hide old completion banner/buttons
        for w in self._done_banner.winfo_children():
            w.destroy()
        self._done_banner.pack_forget()
        for w in self._done_buttons.winfo_children():
            w.destroy()
        self._done_buttons.pack_forget()

        self.status_var.set(
            "Running benchmark (manual files)..."
            if input_mode == "manual"
            else "Generating files and running benchmark..."
        )
        threading.Thread(target=self._run_benchmark, args=(selected, input_mode),
                         daemon=True).start()

    def _stop_benchmark(self) -> None:
        self._stop_flag = True
        self.status_var.set("Stopping after current file\u2026")

    # ======================================================== WORKER
    def _run_benchmark(self, groups: list[str], input_mode: str) -> None:
        config = self.config
        logger = CSVLogger(config)

        files: list[tuple[str, str]] = []
        if input_mode == "generated":
            self.root.after(0, lambda: self._log("[GEN] Creating fresh random benchmark files...", "gen"))

            def _generation_callback(record) -> None:
                size_mb = record.size_bytes / BYTES_PER_MB
                elapsed_ms = record.elapsed_seconds * 1000.0
                self.root.after(
                    0,
                    lambda r=record, s=size_mb, e=elapsed_ms: self._log(
                        f"[GEN] {r.group} / {r.path.name}  {s:.0f} MB  "
                        f"in {e:.1f} ms ({r.rate_mbps:.1f} MB/s)",
                        "gen",
                    ),
                )

            try:
                files, gen_summary = build_generated_dataset(
                    config.input_dir,
                    groups,
                    on_file_generated=_generation_callback,
                    should_stop=lambda: self._stop_flag,
                )
                total_mb = gen_summary.total_bytes / BYTES_PER_MB
                self.root.after(
                    0,
                    lambda m=total_mb, t=gen_summary.elapsed_seconds: self._log(
                        f"[GEN] Completed {gen_summary.file_count} files, "
                        f"{m:.0f} MB total in {t:.2f}s.",
                        "gen",
                    ),
                )
            except Exception as exc:
                self._stop_flag = True
                self.root.after(0, lambda e=str(exc): self._log(f"[GEN] ERROR: {e}", "error"))
                self.root.after(0, self._benchmark_done)
                return
        else:
            for group in groups:
                group_dir = config.input_dir / group
                if not group_dir.is_dir():
                    continue
                for fp in sorted(group_dir.iterdir()):
                    if fp.is_file() and fp.name != ".gitkeep":
                        files.append((str(fp), group))

        total = len(files)
        if total == 0:
            self.root.after(0, lambda: self._log("No files found."))
            self.root.after(0, self._benchmark_done)
            return

        self.root.after(0, lambda: self.overall_progress.config(maximum=total, value=0))
        for idx, (file_path, group) in enumerate(files):
            if self._stop_flag:
                self.root.after(0, lambda: self._log("\u23F9 Benchmark stopped by user."))
                break

            fname = Path(file_path).name

            def _progress_cb(run_num: int, total_r: int,
                             _g: str = group, _f: str = fname) -> None:
                pct = int(((idx + run_num / total_r) / total) * 100)
                self.root.after(0, lambda p=pct: self._pct_label.config(text=f"{p}%"))
                if run_num < self._progress_last_run:
                    self._progress_mode = "AES-GCM"
                self._progress_last_run = run_num
                self.root.after(0, lambda r=run_num, t=total_r, m=self._progress_mode:
                                self._apply_progress_header(_g, _f, m, r, t))

            self.root.after(0, lambda g=group, f=fname:
                            self._log(f"Testing {g} / {f}\u2026", "info"))

            try:
                results = self.runner.run_experiment(
                    file_path, group, config, progress_callback=_progress_cb)
                ctr_res, gcm_res = results[0], results[1]
                logger.log(ctr_res, gcm_res)

                ctr_ms = ctr_res.avg_enc_time_ns / 1e6
                ctr_dec = ctr_res.avg_dec_time_ns / 1e6
                gcm_ms = gcm_res.avg_enc_time_ns / 1e6
                gcm_dec = gcm_res.avg_dec_time_ns / 1e6
                ctr_tp = calculate_throughput(ctr_res.file_size_bytes,
                                             int(ctr_res.avg_enc_time_ns))
                gcm_tp = calculate_throughput(gcm_res.file_size_bytes,
                                             int(gcm_res.avg_enc_time_ns))
                overhead = calculate_overhead_percent(
                    gcm_res.avg_enc_time_ns, ctr_res.avg_enc_time_ns)

                self.root.after(0, lambda c=ctr_ms, t=ctr_tp, g=group, f=fname:
                                self._log(f"[CTR]  {g} / {f}     "
                                          f"enc={c:.3f}ms  {t:.0f} MB/s  \u2713", "ctr"))
                self.root.after(0, lambda gm=gcm_ms, o=overhead, g=group, f=fname:
                                self._log(f"[GCM]  {g} / {f}     "
                                          f"enc={gm:.3f}ms  overhead=+{o:.1f}%  \u2713", "gcm"))

                # Insert rows into tree
                self.root.after(0, lambda g=group, f=fname,
                                c=ctr_ms, cd=ctr_dec, ct=ctr_tp:
                                self._insert_tree_row(g, f, "CTR",
                                                      c, cd, ct, "—"))
                self.root.after(0, lambda g=group, f=fname,
                                gm=gcm_ms, gd=gcm_dec, gt=gcm_tp, o=overhead:
                                self._insert_tree_row(g, f, "GCM",
                                                      gm, gd, gt, f"+{o:.1f}%"))

            except Exception as exc:
                self.root.after(0, lambda e=str(exc), g=group, f=fname:
                                self._log(f"\u26A0 {g} / {f}  ERROR: {e}", "error"))

            done_pct = int(((idx + 1) / total) * 100)
            self.root.after(0, lambda v=idx + 1: self.overall_progress.config(value=v))
            self.root.after(0, lambda p=done_pct: self._pct_label.config(text=f"{p}%"))

        self.root.after(0, lambda t=total, g=len(groups): self._benchmark_done(t, g))

    def _apply_progress_header(self, group: str, fname: str,
                               mode: str, run_num: int, total_runs: int) -> None:
        self.current_label.config(text=f"{group}  /  {fname}  /  {mode}")
        self._run_progress_label.config(text=f"Run {run_num} of {total_runs}")

    # ─────────────────────────────────────────────── tree row insert
    def _insert_tree_row(self, group: str, fname: str, mode: str,
                         enc: float, dec: float, tp: float,
                         overhead: str) -> None:
        self.tree.insert("", "end", values=(
            group, fname, mode,
            f"{enc:.3f}", f"{dec:.3f}",
            f"{tp:.1f} MB/s", overhead,
        ), tags=("row",))
        self._row_count += 1
        # Auto-scroll to latest
        children = self.tree.get_children()
        if children:
            self.tree.see(children[-1])

    # ======================================================== POST-BENCHMARK
    def _benchmark_done(self, file_count: int = 0,
                        group_count: int = 0) -> None:
        self._running = False
        self.start_btn.config(state="normal")
        self._source_manual_btn.config(state="normal", cursor="hand2")
        self._source_generated_btn.config(state="normal", cursor="hand2")
        self.stop_btn.pack_forget()  # hide stop

        stopped = self._stop_flag
        if stopped:
            self._pct_label.config(text="Stopped")
            self.current_label.config(text="Stopped")
            self.status_var.set("Benchmark stopped")
        else:
            self._pct_label.config(text="100%")
            self.current_label.config(text="Complete")
            self.status_var.set("Benchmark complete \u2713")
        self._run_progress_label.config(text="")

        # ── Completion banner ──
        for w in self._done_banner.winfo_children():
            w.destroy()
        self._done_banner.pack(fill="x", pady=(PAD_SM, PAD_XS))

        outer = tk.Frame(self._done_banner, bg=ACCENT_ORANGE if stopped else ACCENT_GREEN)
        outer.pack(fill="x")
        inner = tk.Frame(outer, bg=GLOW_GREEN, padx=PAD_MD, pady=PAD_SM)
        inner.pack(fill="both", padx=1, pady=1)
        banner_text = (
            f"Benchmark Stopped - {file_count} files tested across {group_count} groups"
            if stopped
            else f"\u2713 Benchmark Complete \u2014 {file_count} files tested across {group_count} groups"
        )
        tk.Label(inner,
                 text=banner_text,
                 bg=GLOW_GREEN, fg=ACCENT_ORANGE if stopped else ACCENT_GREEN,
                 font=FONT_HEADING).pack(anchor="w")

        # ── Button row ──
        for w in self._done_buttons.winfo_children():
            w.destroy()
        self._done_buttons.pack(fill="x", pady=(PAD_XS, 0))

        make_button(self._done_buttons, text="View Graphs",
                    command=self._goto_graphs).pack(side="left", padx=(0, PAD_XS))
        make_button(self._done_buttons, text="View Results",
                    command=self._goto_results, style="ghost").pack(side="left", padx=(0, PAD_XS))
        make_button(self._done_buttons, text="View Summary",
                command=self._goto_summary, style="ghost").pack(side="left", padx=(0, PAD_XS))
        make_button(self._done_buttons, text="Export CSV",
                    command=self._export_csv, style="ghost").pack(side="left")

    def _goto_graphs(self) -> None:
        self.app.select_tab(2)
        self.app.tab_graphs.refresh_graphs()

    def _goto_results(self) -> None:
        self.app.select_tab(3)
        self.app.tab_results.load_csv()

    def _goto_summary(self) -> None:
        self.app.select_tab(4)
        self.app.tab_summary.load_summary()

    def _export_csv(self) -> None:
        self.status_var.set(f"Results saved to {Path(self.config.csv_file).name} \u2713")
