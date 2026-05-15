"""Experiment configuration loader.

Reads config.ini and exposes a typed Config dataclass.
Auto-creates output directories; raises if input_dir is missing.
"""

from __future__ import annotations

import configparser
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass(frozen=True)
class Config:
    """Typed representation of all config.ini sections."""

    # [paths]
    input_dir: Path
    results_dir: Path
    csv_file: Path
    graphs_dir: Path

    # [experiment]
    runs: int
    warmup_runs: int
    file_groups: List[str]

    # [crypto]
    key_size_bytes: int
    ctr_nonce_size: int
    gcm_nonce_size: int
    gcm_tag_length: int

    # [ui]
    window_title: str
    window_width: int
    window_height: int
    theme: str


def load_config(config_path: str | Path | None = None) -> Config:
    """Load *config.ini* and return a validated :class:`Config`.

    Parameters
    ----------
    config_path:
        Explicit path to the INI file.  When *None* the file is resolved
        relative to the project root (two levels up from this module).

    Raises
    ------
    FileNotFoundError
        If *config.ini* itself or the ``input_dir`` declared inside it
        does not exist on disk.
    """
    if config_path is None:
        # project root: entropy-aes-benchmark/
        project_root = Path(__file__).resolve().parents[2]
        config_path = project_root / "config.ini"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    parser = configparser.ConfigParser()
    parser.read(config_path, encoding="utf-8")

    project_root = config_path.parent

    # --- [paths] ---
    input_dir = project_root / parser.get("paths", "input_dir")
    results_dir = project_root / parser.get("paths", "results_dir")
    csv_file = project_root / parser.get("paths", "csv_file")
    graphs_dir = project_root / parser.get("paths", "graphs_dir")

    # Auto-create output directories
    results_dir.mkdir(parents=True, exist_ok=True)
    graphs_dir.mkdir(parents=True, exist_ok=True)

    # Validate input directory exists
    if not input_dir.exists():
        raise FileNotFoundError(
            f"Input directory not found: {input_dir}. "
            "Please create it and populate with test files before running."
        )

    # --- [experiment] ---
    runs = parser.getint("experiment", "runs")
    warmup_runs = parser.getint("experiment", "warmup_runs")
    file_groups = [
        g.strip()
        for g in parser.get("experiment", "file_groups").split(",")
        if g.strip()
    ]

    # --- [crypto] ---
    key_size_bytes = parser.getint("crypto", "key_size_bytes")
    ctr_nonce_size = parser.getint("crypto", "ctr_nonce_size")
    gcm_nonce_size = parser.getint("crypto", "gcm_nonce_size")
    gcm_tag_length = parser.getint("crypto", "gcm_tag_length")

    # --- [ui] ---
    window_title = parser.get("ui", "window_title")
    window_width = parser.getint("ui", "window_width")
    window_height = parser.getint("ui", "window_height")
    theme = parser.get("ui", "theme")

    return Config(
        input_dir=input_dir,
        results_dir=results_dir,
        csv_file=csv_file,
        graphs_dir=graphs_dir,
        runs=runs,
        warmup_runs=warmup_runs,
        file_groups=file_groups,
        key_size_bytes=key_size_bytes,
        ctr_nonce_size=ctr_nonce_size,
        gcm_nonce_size=gcm_nonce_size,
        gcm_tag_length=gcm_tag_length,
        window_title=window_title,
        window_width=window_width,
        window_height=window_height,
        theme=theme,
    )
