"""Entropy — AES Benchmark Tool (GUI entry point)."""

import sys
import tkinter as tk
from tkinter import messagebox


def main() -> None:
    # Validate config loads cleanly before opening the window
    try:
        from src.benchmark.experiment_config import load_config
        config = load_config()
    except FileNotFoundError as exc:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Configuration Error", str(exc))
        root.destroy()
        sys.exit(1)

    from src.ui.app_window import AppWindow
    app = AppWindow()

    app.run()


if __name__ == "__main__":
    main()
