"""Entropy AES Benchmark — CLI entry point.

Usage:
    python main.py --run-experiments
    python main.py --generate-graphs
    python main.py --demo
    python main.py --check-config
    python main.py --all
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------

def _discover_files(config) -> list[tuple[str, str]]:
    """Return ``[(file_path, file_group), ...]`` for every test file found."""
    found: list[tuple[str, str]] = []
    for group in config.file_groups:
        group_dir = config.input_dir / group
        if not group_dir.is_dir():
            continue
        for fp in sorted(group_dir.iterdir()):
            if fp.is_file() and fp.name != ".gitkeep":
                found.append((str(fp), group))
    return found


# ---------------------------------------------------------------------------
# --run-experiments
# ---------------------------------------------------------------------------

def _cmd_run_experiments(config) -> None:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
    from rich.table import Table

    from src.benchmark.benchmark_runner import BenchmarkRunner
    from src.logging.csv_logger import CSVLogger
    from src.metrics.overhead_calculator import calculate_overhead_percent
    from src.metrics.throughput_calculator import calculate_throughput
    from src.visualization.graph_generator import GraphGenerator

    console = Console()
    runner = BenchmarkRunner()
    logger = CSVLogger(config)

    files = _discover_files(config)
    if not files:
        console.print(
            Panel("[bold red]No input files found.[/]\n"
                  f"Populate folders inside {config.input_dir}",
                  title="Error")
        )
        return

    console.print(
        Panel(f"[bold cyan]Entropy AES Benchmark[/]\n"
              f"Files discovered: {len(files)}  |  "
              f"Runs per mode: {config.runs}  |  "
              f"Warm-up: {config.warmup_runs}",
              title="Benchmark Suite")
    )

    # Collect summary rows for the final table
    summary_rows: list[dict] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task("Running experiments…", total=len(files))

        for file_path, group in files:
            fname = Path(file_path).name
            progress.update(task, description=f"[cyan]{group}[/] / {fname}")
            try:
                results = runner.run_experiment(file_path, group, config)
                ctr_res, gcm_res = results[0], results[1]
                logger.log(ctr_res, gcm_res)

                overhead_pct = calculate_overhead_percent(
                    gcm_res.avg_enc_time_ns, ctr_res.avg_enc_time_ns
                )
                enc_tp = calculate_throughput(
                    gcm_res.file_size_bytes, int(gcm_res.avg_enc_time_ns)
                )

                summary_rows.append({
                    "group": group,
                    "file": fname,
                    "ctr_ms": f"{ctr_res.avg_enc_time_ns / 1e6:.4f}",
                    "gcm_ms": f"{gcm_res.avg_enc_time_ns / 1e6:.4f}",
                    "overhead": f"{overhead_pct:.2f}%",
                    "mbps": f"{enc_tp:.2f}",
                })

            except Exception as exc:
                console.print(
                    Panel(f"[bold red]Error:[/] {exc}\nFile: {file_path}",
                          title="Skipped", border_style="red")
                )

            progress.advance(task)

    # -- Summary table --
    table = Table(title="Benchmark Summary", show_lines=True)
    table.add_column("Group", style="cyan")
    table.add_column("File", style="white")
    table.add_column("CTR enc (ms)", justify="right")
    table.add_column("GCM enc (ms)", justify="right")
    table.add_column("Overhead %", justify="right", style="yellow")
    table.add_column("GCM MB/s", justify="right", style="green")
    for r in summary_rows:
        table.add_row(r["group"], r["file"], r["ctr_ms"], r["gcm_ms"],
                       r["overhead"], r["mbps"])
    console.print(table)

    # -- Auto-generate graphs --
    console.print("\n[bold]Generating graphs…[/]")
    gen = GraphGenerator(config)
    paths = gen.generate_all()
    if paths:
        for p in paths:
            console.print(f"  [green]✓[/] {p}")
    else:
        console.print("  [dim]Graph generator returned no files (stub).[/]")

    console.print("\n[bold green]Done.[/] Results saved to:", str(config.csv_file))


# ---------------------------------------------------------------------------
# --generate-graphs
# ---------------------------------------------------------------------------

def _cmd_generate_graphs(config) -> None:
    from rich.console import Console
    from src.visualization.graph_generator import GraphGenerator

    console = Console()
    console.print("[bold]Generating graphs from CSV…[/]")

    gen = GraphGenerator(config)
    paths = gen.generate_all()

    if paths:
        for p in paths:
            console.print(f"  [green]✓[/] {p}")
    else:
        console.print("  [dim]No graphs generated (CSV may be missing or generator is stub).[/]")

    console.print("[bold green]Done.[/]")


# ---------------------------------------------------------------------------
# --demo
# ---------------------------------------------------------------------------

def _cmd_demo(_config) -> None:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    from src.demo.tamper_detection_demo import run_ctr_tamper_demo, run_gcm_tamper_demo

    console = Console()
    console.print(Panel("[bold cyan]Tamper Detection Demo[/]", expand=False))

    # --- GCM ---
    g = run_gcm_tamper_demo()
    console.print(Panel(
        f"[bold]Plaintext:[/]  {g['plaintext']}\n"
        f"[bold]Clean decrypt:[/]  {g['clean_decryption']}\n\n"
        f"Tampered byte index: [yellow]{g['tampered_byte_index']}[/]  "
        f"(0x{g['original_byte']:02X} → 0x{g['tampered_byte']:02X})\n\n"
        f"[bold green]GCM blocked tampered decryption: {g['gcm_blocked']}[/]\n"
        f"[red]Error:[/] {g['error_message']}",
        title="AES-GCM (Authenticated)", border_style="green",
    ))

    # --- CTR ---
    c = run_ctr_tamper_demo()
    console.print(Panel(
        f"[bold]Plaintext:[/]        {c['plaintext']}\n"
        f"[bold]Corrupted output:[/] {c['corrupted_output']}\n\n"
        f"Tampered byte index: [yellow]{c['tampered_byte_index']}[/]\n\n"
        f"[bold red]CTR allowed tampered decryption: {c['ctr_allowed']}[/]",
        title="AES-CTR (Unauthenticated)", border_style="red",
    ))

    # --- Comparison ---
    table = Table(title="Comparison", show_lines=True)
    table.add_column("Property", style="bold")
    table.add_column("AES-GCM", style="green")
    table.add_column("AES-CTR", style="red")
    table.add_row("Authenticated?", "Yes", "No")
    table.add_row("Tamper detected?", "Yes — blocked", "No — silent corruption")
    table.add_row("Decryption result",
                   "AuthenticationError raised",
                   f"Garbled: {c['corrupted_output'][:30]}…")
    console.print(table)


# ---------------------------------------------------------------------------
# --check-config
# ---------------------------------------------------------------------------

def _cmd_check_config(config) -> None:
    from rich.console import Console
    from rich.table import Table

    console = Console()

    # Config values
    table = Table(title="Configuration", show_lines=True)
    table.add_column("Section", style="cyan")
    table.add_column("Key", style="bold")
    table.add_column("Value")

    for section, pairs in [
        ("paths", [
            ("input_dir", config.input_dir),
            ("results_dir", config.results_dir),
            ("csv_file", config.csv_file),
            ("graphs_dir", config.graphs_dir),
        ]),
        ("experiment", [
            ("runs", config.runs),
            ("warmup_runs", config.warmup_runs),
            ("file_groups", ", ".join(config.file_groups)),
        ]),
        ("crypto", [
            ("key_size_bytes", config.key_size_bytes),
            ("ctr_nonce_size", config.ctr_nonce_size),
            ("gcm_nonce_size", config.gcm_nonce_size),
            ("gcm_tag_length", config.gcm_tag_length),
        ]),
        ("ui", [
            ("window_title", config.window_title),
            ("window_width", config.window_width),
            ("window_height", config.window_height),
            ("theme", config.theme),
        ]),
    ]:
        for key, value in pairs:
            table.add_row(section, key, str(value))

    console.print(table)

    # Discovered files per group
    files_table = Table(title="Discovered Input Files", show_lines=True)
    files_table.add_column("Group", style="cyan")
    files_table.add_column("Files")

    for group in config.file_groups:
        group_dir = config.input_dir / group
        if group_dir.is_dir():
            names = sorted(
                f.name for f in group_dir.iterdir()
                if f.is_file() and f.name != ".gitkeep"
            )
            files_table.add_row(group, ", ".join(names) if names else "[dim]empty[/]")
        else:
            files_table.add_row(group, "[red]directory missing[/]")

    console.print(files_table)
    console.print("[bold green]Config OK.[/]")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="entropy-aes-benchmark",
        description="AES-GCM vs AES-CTR performance benchmark suite",
    )
    parser.add_argument("--run-experiments", action="store_true",
                        help="Run full benchmark suite")
    parser.add_argument("--generate-graphs", action="store_true",
                        help="Generate graphs from existing CSV")
    parser.add_argument("--demo", action="store_true",
                        help="Run tamper detection demo in terminal")
    parser.add_argument("--check-config", action="store_true",
                        help="Validate config and list discovered files")
    parser.add_argument("--all", action="store_true",
                        help="Run everything in sequence")
    args = parser.parse_args()

    # If no flag supplied, print help
    if not any([args.run_experiments, args.generate_graphs,
                args.demo, args.check_config, args.all]):
        parser.print_help()
        sys.exit(0)

    from src.benchmark.experiment_config import load_config
    config = load_config()

    if args.all or args.check_config:
        _cmd_check_config(config)
    if args.all or args.demo:
        _cmd_demo(config)
    if args.all or args.run_experiments:
        _cmd_run_experiments(config)
    if args.all or args.generate_graphs:
        _cmd_generate_graphs(config)


if __name__ == "__main__":
    main()
