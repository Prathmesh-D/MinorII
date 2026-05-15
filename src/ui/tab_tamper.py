"""Tab 5 - Tamper Detection Demonstration (GCM vs CTR)."""

from __future__ import annotations

import tkinter as tk

from src.benchmark.experiment_config import Config
from src.demo.tamper_detection_demo import run_ctr_tamper_demo, run_gcm_tamper_demo
from src.ui.theme import (
    BG_BASE,
    BG_SURFACE,
    BG_ELEVATED,
    BORDER,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
    ACCENT_BLUE,
    ACCENT_RED,
    ACCENT_GREEN,
    ACCENT_ORANGE,
    FONT_HEADING,
    FONT_SUBHEAD,
    FONT_BODY,
    FONT_MONO,
    FONT_LABEL,
    PAD_LG,
    PAD_MD,
    PAD_SM,
    PAD_XS,
)
from src.ui.components import (
    make_button,
    make_section_label,
    make_status_indicator,
    make_tag,
    add_tooltip,
)

STEP_DELAY_MS = 800


class TamperTab:
    """Animated side-by-side GCM vs CTR tamper demo."""

    def __init__(self, parent: tk.Frame, config: Config,
                 status_var: tk.StringVar, root: tk.Tk,
                 app=None) -> None:
        self.config = config
        self.status_var = status_var
        self.root = root
        self.app = app
        self._step_widgets: list[tk.Widget] = []

        self.frame = tk.Frame(parent, bg=BG_BASE)
        self._build_ui()

    def _build_ui(self) -> None:
        outer = tk.Frame(self.frame, bg=BG_BASE)
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, bg=BG_BASE, highlightthickness=0)
        vsb = tk.Scrollbar(outer, orient="vertical", command=canvas.yview,
                           bg=BG_ELEVATED, troughcolor=BG_BASE,
                           highlightthickness=0, bd=0)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self._inner = tk.Frame(canvas, bg=BG_BASE)
        self._inner_id = canvas.create_window((0, 0), window=self._inner,
                                              anchor="nw")

        def _on_configure(_e):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(e):
            canvas.itemconfig(self._inner_id, width=e.width)

        self._inner.bind("<Configure>", _on_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        self._canvas = canvas
        self._container = self._inner

        top = tk.Frame(self._container, bg=BG_BASE)
        top.pack(fill="x", padx=PAD_MD, pady=(PAD_MD, 0))

        make_section_label(top, "Tamper Detection Demonstration")

        btn_row = tk.Frame(self._container, bg=BG_BASE)
        btn_row.pack(fill="x", padx=PAD_MD, pady=(PAD_SM, PAD_XS))
        self.run_btn = make_button(btn_row, "Run Demo",
                                   self._run_demo, "primary", width=20)
        self.run_btn.pack(anchor="center")

        self.status_lbl = tk.Label(
            self._container,
            text="Click Run Demo to begin the demonstration",
            bg=BG_BASE,
            fg=TEXT_SECONDARY,
            font=FONT_LABEL,
        )
        self.status_lbl.pack(pady=(0, PAD_SM))

        self.columns_frame = tk.Frame(self._container, bg=BG_BASE)
        self.columns_frame.pack(fill="both", expand=True,
                                padx=PAD_MD, pady=PAD_XS)
        self.columns_frame.columnconfigure(0, weight=1, uniform="col")
        self.columns_frame.columnconfigure(1, weight=1, uniform="col")

        self.gcm_col = tk.Frame(self.columns_frame, bg=BG_BASE)
        self.gcm_col.grid(row=0, column=0, sticky="nsew", padx=(0, PAD_MD // 2))

        gcm_hdr = tk.Frame(self.gcm_col, bg=BG_BASE)
        gcm_hdr.pack(fill="x", pady=(0, PAD_SM))
        tk.Label(gcm_hdr, text="AES-GCM", bg=BG_BASE, fg=ACCENT_RED,
                 font=FONT_HEADING).pack(side="left", padx=(PAD_MD, PAD_SM),
                                         pady=PAD_SM)
        t1 = make_tag(gcm_hdr, "Authenticated Encryption", ACCENT_RED)
        t1.pack(side="left", padx=(0, PAD_XS), pady=PAD_SM)
        add_tooltip(t1, "AES-GCM provides confidentiality and authentication.")
        t2 = make_tag(gcm_hdr, "128-bit Auth Tag", ACCENT_GREEN)
        t2.pack(side="left", pady=PAD_SM)
        add_tooltip(t2, "Tag verification fails if any ciphertext bit is altered.")

        self.gcm_steps = tk.Frame(self.gcm_col, bg=BG_BASE)
        self.gcm_steps.pack(fill="both", expand=True)

        self.ctr_col = tk.Frame(self.columns_frame, bg=BG_BASE)
        self.ctr_col.grid(row=0, column=1, sticky="nsew", padx=(PAD_MD // 2, 0))

        ctr_hdr = tk.Frame(self.ctr_col, bg=BG_BASE)
        ctr_hdr.pack(fill="x", pady=(0, PAD_SM))
        tk.Label(ctr_hdr, text="AES-CTR", bg=BG_BASE, fg=ACCENT_BLUE,
                 font=FONT_HEADING).pack(side="left", padx=(PAD_MD, PAD_SM),
                                         pady=PAD_SM)
        t3 = make_tag(ctr_hdr, "Confidentiality Only", ACCENT_BLUE)
        t3.pack(side="left", padx=(0, PAD_XS), pady=PAD_SM)
        add_tooltip(t3, "AES-CTR encrypts but does not authenticate data.")
        t4 = make_tag(ctr_hdr, "No Authentication", ACCENT_ORANGE)
        t4.pack(side="left", pady=PAD_SM)
        add_tooltip(t4, "Tampered ciphertext decrypts without integrity failure.")

        self.ctr_steps = tk.Frame(self.ctr_col, bg=BG_BASE)
        self.ctr_steps.pack(fill="both", expand=True)

        self.table_frame = tk.Frame(self._container, bg=BG_BASE)
        self.table_frame.pack(fill="x", padx=PAD_MD, pady=(PAD_LG, PAD_LG))

        self._build_pre_demo_placeholders()

    def _build_pre_demo_placeholders(self) -> None:
        step_names = [
            "Original Message",
            "Encryption",
            "Ciphertext Tampered",
            "Decryption Attempt",
            "Verification",
        ]
        for parent in (self.gcm_steps, self.ctr_steps):
            rail = tk.Frame(parent, bg=TEXT_MUTED, width=1)
            rail.place(relx=0.03, rely=0, relheight=1)
            for name in step_names:
                row = tk.Frame(parent, bg=BG_BASE)
                row.pack(fill="x", pady=(0, PAD_SM))
                tk.Label(row, text="o", bg=BG_BASE, fg=TEXT_MUTED,
                         font=FONT_LABEL).pack(side="left", padx=(PAD_SM, PAD_MD))
                inner = tk.Frame(row, bg=BG_SURFACE, padx=PAD_LG, pady=PAD_LG)
                inner.pack(side="left", fill="x", expand=True)
                tk.Label(inner, text=name, bg=BG_SURFACE, fg=TEXT_MUTED,
                         font=FONT_LABEL).pack(anchor="w")
                tk.Label(inner, text="Waiting for demo...", bg=BG_SURFACE,
                         fg=TEXT_MUTED, font=FONT_BODY).pack(anchor="w", pady=(PAD_XS, 0))

    def _run_demo(self) -> None:
        self.run_btn.config(state="disabled")
        self.status_lbl.config(text="Running tamper detection demo...", fg=ACCENT_BLUE)
        self.status_var.set("Running tamper detection demo...")

        self._step_widgets.clear()
        for w in self.gcm_steps.winfo_children():
            w.destroy()
        for w in self.ctr_steps.winfo_children():
            w.destroy()
        for w in self.table_frame.winfo_children():
            w.destroy()

        gcm = run_gcm_tamper_demo()
        ctr = run_ctr_tamper_demo()

        steps = self._prepare_steps(gcm, ctr)
        self._animate(steps, 0)

    def _prepare_steps(self, gcm: dict, ctr: dict) -> list[tuple]:
        steps: list[tuple] = []

        ct_hex = gcm["ciphertext_hex"]
        ct_hex_short = ct_hex[:40] + "..."
        tag_hex = ct_hex[-32:]
        ctr_ct_hex = ctr["ciphertext_hex"][:40] + "..."

        orig_b = gcm["original_byte"]
        tamp_b = gcm["tampered_byte"]
        idx = gcm["tampered_byte_index"]
        tampered_hex_full = gcm["tampered_ciphertext_hex"]

        steps.append((self.gcm_steps, lambda p, pt=gcm["plaintext"]: self._step1(p, pt)))
        steps.append((self.ctr_steps, lambda p, pt=ctr["plaintext"]: self._step1(p, pt)))

        steps.append((self.gcm_steps, lambda p: self._step2_gcm(p, ct_hex_short, tag_hex)))
        steps.append((self.ctr_steps, lambda p: self._step2_ctr(p, ctr_ct_hex)))

        steps.append((self.gcm_steps,
                      lambda p: self._step3(p, idx, orig_b, tamp_b, tampered_hex_full)))
        steps.append((self.ctr_steps,
                      lambda p: self._step3(
                          p, ctr["tampered_byte_index"], 0, 0, ctr["tampered_ciphertext_hex"])))

        steps.append((self.gcm_steps, lambda p: self._step4_gcm(p, gcm["error_message"])))
        steps.append((self.ctr_steps, lambda p: self._step4_ctr(p, ctr["corrupted_output"])))

        steps.append((self.gcm_steps, lambda p: self._step5_gcm(p, gcm["clean_decryption"])))
        steps.append((self.ctr_steps, lambda p: self._step5_ctr(p)))

        steps.append((self.table_frame, lambda p: self._comparison_table(p)))

        return steps

    def _animate(self, steps: list[tuple], idx: int) -> None:
        if idx >= len(steps):
            self.run_btn.config(state="normal")
            self.status_lbl.config(text="Demonstration complete", fg=ACCENT_GREEN)
            self.status_var.set("Tamper demo complete")
            return

        parent, builder = steps[idx]
        widget = builder(parent)
        if widget:
            self._step_widgets.append(widget)
            self._flash_border(widget)

        self.root.after(STEP_DELAY_MS, lambda: self._animate(steps, idx + 1))

    def _flash_border(self, widget: tk.Widget) -> None:
        try:
            orig_bg = widget.cget("bg")
        except Exception:
            return
        widget.config(bg=ACCENT_BLUE)
        self.root.after(120, lambda: widget.config(bg=orig_bg))

    def _make_step_shell(self, parent: tk.Frame, title: str) -> tuple[tk.Frame, tk.Frame]:
        row = tk.Frame(parent, bg=BG_BASE)
        row.pack(fill="x", pady=(0, PAD_SM))
        tk.Label(row, text="o", bg=BG_BASE, fg=TEXT_MUTED,
                 font=FONT_LABEL).pack(side="left", padx=(PAD_SM, PAD_MD))
        card = tk.Frame(row, bg=BG_SURFACE, padx=PAD_LG, pady=PAD_LG)
        card.pack(side="left", fill="x", expand=True)
        tk.Label(card, text=title, bg=BG_SURFACE, fg=TEXT_SECONDARY,
                 font=FONT_SUBHEAD).pack(anchor="w", pady=(0, PAD_SM))
        return row, card

    def _step1(self, parent: tk.Frame, plaintext: str) -> tk.Frame:
        row, card = self._make_step_shell(parent, "Original Message")
        box = tk.Text(card, height=2, width=50, bg=BG_BASE, fg=TEXT_PRIMARY,
                      font=FONT_MONO, relief="flat", bd=0,
                      highlightthickness=1, highlightbackground=BORDER,
                      wrap="word", padx=PAD_SM, pady=PAD_SM)
        box.insert("1.0", plaintext)
        box.config(state="disabled")
        box.pack(fill="x", pady=(0, PAD_SM))

        ind = make_status_indicator(card, "Plaintext ready", "neutral")
        ind.pack(anchor="w")
        return row

    def _step2_gcm(self, parent: tk.Frame, ct_short: str, tag_hex: str) -> tk.Frame:
        row, card = self._make_step_shell(parent, "Encrypted with AES-GCM")

        ct_row = tk.Frame(card, bg=BG_SURFACE)
        ct_row.pack(fill="x", pady=PAD_XS)
        tk.Label(ct_row, text="Ciphertext:", bg=BG_SURFACE,
                 fg=TEXT_SECONDARY, font=FONT_LABEL).pack(side="left")
        tk.Label(ct_row, text=ct_short, bg=BG_SURFACE, fg=ACCENT_BLUE,
                 font=FONT_MONO).pack(side="left", padx=(PAD_SM, 0))

        tag_row = tk.Frame(card, bg=BG_SURFACE)
        tag_row.pack(fill="x", pady=PAD_XS)
        tk.Label(tag_row, text="Auth Tag:", bg=BG_SURFACE,
                 fg=TEXT_SECONDARY, font=FONT_LABEL).pack(side="left")
        tk.Label(tag_row, text=tag_hex, bg=BG_SURFACE, fg=ACCENT_GREEN,
                 font=FONT_MONO).pack(side="left", padx=(PAD_SM, 0))

        ind = make_status_indicator(card, "Encrypted + tag generated", "success")
        ind.pack(anchor="w", pady=(PAD_SM, 0))
        return row

    def _step2_ctr(self, parent: tk.Frame, ct_short: str) -> tk.Frame:
        row, card = self._make_step_shell(parent, "Encrypted with AES-CTR")

        ct_row = tk.Frame(card, bg=BG_SURFACE)
        ct_row.pack(fill="x", pady=PAD_XS)
        tk.Label(ct_row, text="Ciphertext:", bg=BG_SURFACE,
                 fg=TEXT_SECONDARY, font=FONT_LABEL).pack(side="left")
        tk.Label(ct_row, text=ct_short, bg=BG_SURFACE, fg=ACCENT_BLUE,
                 font=FONT_MONO).pack(side="left", padx=(PAD_SM, 0))

        ind = make_status_indicator(card, "Encrypted (no tag)", "success")
        ind.pack(anchor="w", pady=(PAD_SM, 0))
        return row

    def _step3(self, parent: tk.Frame, idx: int, orig_b: int,
               tamp_b: int, tampered_hex: str) -> tk.Frame:
        row, inner = self._make_step_shell(parent, "Ciphertext Tampered")

        tk.Label(inner, text=f"Byte at index {idx} modified:",
                 bg=BG_SURFACE, fg=TEXT_SECONDARY,
                 font=FONT_LABEL).pack(anchor="w", pady=(0, PAD_XS))

        change_row = tk.Frame(inner, bg=BG_SURFACE)
        change_row.pack(anchor="w", pady=PAD_XS)
        tk.Label(change_row, text=f"Original: 0x{orig_b:02X}",
                 bg=BG_SURFACE, fg=ACCENT_BLUE,
                 font=FONT_MONO).pack(side="left")
        tk.Label(change_row, text="  ->  ", bg=BG_SURFACE, fg=TEXT_MUTED,
                 font=FONT_BODY).pack(side="left")
        tk.Label(change_row, text=f"Modified: 0x{tamp_b:02X}",
                 bg=BG_SURFACE, fg=ACCENT_RED,
                 font=FONT_MONO).pack(side="left")

        hex_frame = tk.Frame(inner, bg=BG_BASE, padx=PAD_SM, pady=PAD_SM,
                             highlightthickness=1, highlightbackground=BORDER)
        hex_frame.pack(fill="x", pady=(PAD_SM, PAD_SM))

        hex_text = tk.Text(hex_frame, height=2, bg=BG_BASE,
                           font=FONT_MONO, relief="flat", bd=0,
                           wrap="char", highlightthickness=0)
        hex_text.tag_configure("normal", foreground=TEXT_MUTED)
        hex_text.tag_configure("tampered", foreground="white", background=ACCENT_RED)

        byte_idx_start = idx * 2
        byte_idx_end = byte_idx_start + 2
        if byte_idx_end <= len(tampered_hex):
            hex_text.insert("end", tampered_hex[:byte_idx_start], "normal")
            hex_text.insert("end", tampered_hex[byte_idx_start:byte_idx_end], "tampered")
            hex_text.insert("end", tampered_hex[byte_idx_end:], "normal")
        else:
            hex_text.insert("end", tampered_hex, "normal")

        hex_text.config(state="disabled")
        hex_text.pack(fill="x")

        ind = make_status_indicator(inner, "Ciphertext modified", "warning")
        for child in ind.winfo_children():
            child.config(bg=BG_SURFACE)
        ind.config(bg=BG_SURFACE)
        ind.pack(anchor="w")

        return row

    def _step4_gcm(self, parent: tk.Frame, error_msg: str) -> tk.Frame:
        row = tk.Frame(parent, bg=BG_BASE)
        row.pack(fill="x", pady=(0, PAD_SM))

        tk.Label(row, text="o", bg=BG_BASE, fg=TEXT_MUTED,
                 font=FONT_LABEL).pack(side="left", padx=(PAD_SM, PAD_MD))

        shell = tk.Frame(row, bg=BG_BASE)
        shell.pack(side="left", fill="x", expand=True)
        tk.Frame(shell, bg=TEXT_PRIMARY, width=2).pack(side="left", fill="y")

        inner = tk.Frame(shell, bg=BG_SURFACE, padx=PAD_LG, pady=PAD_LG)
        inner.pack(side="left", fill="both", expand=True)

        tk.Label(inner, text="Decryption Attempt", bg=BG_SURFACE,
                 fg=TEXT_SECONDARY, font=FONT_SUBHEAD).pack(anchor="w", pady=(0, PAD_SM))
        tk.Label(inner, text="AUTHENTICATION FAILED", bg=BG_SURFACE,
                 fg=TEXT_PRIMARY, font=FONT_HEADING).pack(anchor="w")
        tk.Label(inner, text="InvalidTag exception raised", bg=BG_SURFACE,
                 fg=TEXT_SECONDARY, font=FONT_BODY).pack(anchor="w", pady=(PAD_XS, 0))

        exc_box = tk.Frame(inner, bg=BG_BASE, padx=PAD_MD, pady=PAD_SM,
                           highlightthickness=1, highlightbackground=BORDER)
        exc_box.pack(fill="x", pady=(PAD_SM, 0))
        tk.Label(exc_box, text="cryptography.exceptions.InvalidTag",
                 bg=BG_BASE, fg=ACCENT_RED, font=FONT_MONO).pack(anchor="w")
        tk.Label(exc_box, text="GCM tag verification failed",
                 bg=BG_BASE, fg=ACCENT_RED, font=FONT_MONO).pack(anchor="w", pady=(PAD_XS, 0))
        if error_msg:
            tk.Label(exc_box, text=error_msg, bg=BG_BASE,
                     fg=TEXT_MUTED, font=FONT_MONO).pack(anchor="w", pady=(PAD_XS, 0))

        return row

    def _step4_ctr(self, parent: tk.Frame, corrupted: str) -> tk.Frame:
        row = tk.Frame(parent, bg=BG_BASE)
        row.pack(fill="x", pady=(0, PAD_SM))

        tk.Label(row, text="o", bg=BG_BASE, fg=TEXT_MUTED,
                 font=FONT_LABEL).pack(side="left", padx=(PAD_SM, PAD_MD))

        shell = tk.Frame(row, bg=BG_BASE)
        shell.pack(side="left", fill="x", expand=True)
        tk.Frame(shell, bg=TEXT_MUTED, width=1).pack(side="left", fill="y")

        inner = tk.Frame(shell, bg=BG_SURFACE, padx=PAD_LG, pady=PAD_LG)
        inner.pack(side="left", fill="both", expand=True)

        tk.Label(inner, text="Decryption Attempt", bg=BG_SURFACE,
                 fg=TEXT_SECONDARY, font=FONT_SUBHEAD).pack(anchor="w", pady=(0, PAD_SM))
        tk.Label(inner, text="DECRYPTION ALLOWED", bg=BG_SURFACE,
                 fg=TEXT_PRIMARY, font=FONT_HEADING).pack(anchor="w")
        tk.Label(inner, text="No authentication - tampering undetected", bg=BG_SURFACE,
                 fg=TEXT_SECONDARY, font=FONT_BODY).pack(anchor="w", pady=(PAD_XS, 0))

        tk.Label(inner, text="Corrupted output:", bg=BG_SURFACE,
                 fg=TEXT_MUTED, font=FONT_LABEL).pack(anchor="w", pady=(PAD_MD, PAD_XS))
        cor_box = tk.Frame(inner, bg=BG_BASE, padx=PAD_MD, pady=PAD_SM,
                           highlightthickness=1, highlightbackground=BORDER)
        cor_box.pack(fill="x")
        tk.Label(cor_box, text=corrupted, bg=BG_BASE, fg=ACCENT_ORANGE,
                 font=FONT_MONO, wraplength=420, justify="left").pack(anchor="w")

        return row

    def _step5_gcm(self, parent: tk.Frame, clean_text: str) -> tk.Frame:
        row, inner = self._make_step_shell(parent, "Unmodified - Decryption Success")

        tk.Label(inner, text=clean_text, bg=BG_SURFACE, fg=ACCENT_GREEN,
                 font=FONT_MONO, wraplength=420,
                 justify="left").pack(anchor="w", pady=(0, PAD_SM))

        ind = make_status_indicator(inner, "Original data recovered intact", "success")
        for child in ind.winfo_children():
            child.config(bg=BG_SURFACE)
        ind.config(bg=BG_SURFACE)
        ind.pack(anchor="w")

        return row

    def _step5_ctr(self, parent: tk.Frame) -> tk.Frame:
        row, inner = self._make_step_shell(parent, "No Integrity Check Available")

        ind = make_status_indicator(inner, "Data silently corrupted - no error raised", "warning")
        for child in ind.winfo_children():
            child.config(bg=BG_SURFACE)
        ind.config(bg=BG_SURFACE)
        ind.pack(anchor="w")

        return row

    @staticmethod
    def _comparison_table(parent: tk.Frame) -> tk.Frame:
        wrapper = tk.Frame(parent, bg=BG_BASE)
        wrapper.pack(fill="x")

        tk.Label(wrapper, text="Security Comparison Summary",
                 bg=BG_BASE, fg=TEXT_PRIMARY,
                 font=FONT_HEADING).pack(anchor="w", padx=PAD_MD,
                                         pady=(PAD_MD, PAD_SM))

        grid = tk.Frame(wrapper, bg=BG_BASE)
        grid.pack(fill="x", padx=PAD_MD, pady=(0, PAD_SM))

        headers = ["Mode", "Tamper Detected", "Output Safe", "Integrity"]
        for ci, h in enumerate(headers):
            tk.Label(grid, text=h, bg=BG_BASE, fg=TEXT_MUTED,
                     font=FONT_LABEL, anchor="w").grid(
                row=0, column=ci, sticky="w", padx=(0, PAD_LG), pady=(0, PAD_SM)
            )

        gcm_vals = ["AES-GCM", "Yes", "Yes", "Guaranteed"]
        ctr_vals = ["AES-CTR", "No", "No", "None"]

        for ci, val in enumerate(gcm_vals):
            tk.Label(grid, text=val, bg=BG_BASE, fg=TEXT_PRIMARY,
                     font=FONT_BODY, anchor="w").grid(
                row=1, column=ci, sticky="w", padx=(0, PAD_LG), pady=(0, PAD_SM)
            )
        for ci, val in enumerate(ctr_vals):
            tk.Label(grid, text=val, bg=BG_BASE, fg=TEXT_MUTED,
                     font=FONT_BODY, anchor="w").grid(
                row=2, column=ci, sticky="w", padx=(0, PAD_LG)
            )

        caption = (
            "AES-GCM authentication proves ciphertext integrity. "
            "AES-CTR provides no built-in tamper detection."
        )
        tk.Label(wrapper, text=caption, bg=BG_BASE,
                 fg=TEXT_MUTED, font=("Consolas", 10, "italic"),
                 wraplength=700, justify="center").pack(pady=(PAD_XS, PAD_MD))

        return wrapper
