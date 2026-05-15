"""Utilities to generate fresh benchmark datasets per run."""

from __future__ import annotations

import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

BYTES_PER_MB = 1_048_576
CHUNK_SIZE = 1_048_576

# Each selected file group gets one file for every profile below.
GENERATED_PROFILES: tuple[tuple[str, str], ...] = (
    ("text", "txt"),
    ("image", "jpg"),
    ("binary", "bin"),
)


@dataclass(frozen=True)
class GeneratedFileRecord:
    """Metadata for a single generated file."""

    path: Path
    group: str
    file_type: str
    size_bytes: int
    elapsed_seconds: float
    rate_mbps: float


@dataclass(frozen=True)
class GeneratedDatasetSummary:
    """Summary of one generated dataset run."""

    root_dir: Path
    file_count: int
    total_bytes: int
    elapsed_seconds: float


def parse_group_size_mb(group: str) -> int:
    """Extract integer MB size from labels like F1_1MB or Benchmark_50MB."""
    token = group.strip()
    if "_" in token:
        token = token.rsplit("_", 1)[-1]
    token = token.upper().strip()
    if token.endswith("MB"):
        token = token[:-2]

    try:
        size_mb = int(float(token))
    except ValueError as exc:
        raise ValueError(f"Unable to parse size from group '{group}'.") from exc

    if size_mb <= 0:
        raise ValueError(f"Parsed non-positive size for group '{group}'.")
    return size_mb


def _write_in_chunks(
    path: Path,
    total_bytes: int,
    chunk_supplier: Callable[[int], bytes],
    should_stop: Callable[[], bool] | None,
) -> None:
    with open(path, "wb") as handle:
        remaining = total_bytes
        while remaining > 0:
            if should_stop is not None and should_stop():
                raise RuntimeError("File generation stopped by user.")
            chunk_len = min(CHUNK_SIZE, remaining)
            handle.write(chunk_supplier(chunk_len))
            remaining -= chunk_len


def _write_binary(path: Path, size_bytes: int, should_stop: Callable[[], bool] | None) -> None:
    _write_in_chunks(path, size_bytes, os.urandom, should_stop)


def _write_text(path: Path, size_bytes: int, should_stop: Callable[[], bool] | None) -> None:
    seed = os.urandom(8).hex().encode("ascii")
    base = b"entropy-benchmark-" + seed + b"-abcdefghijklmnopqrstuvwxyz0123456789\n"

    def supplier(chunk_len: int) -> bytes:
        repeats = (chunk_len // len(base)) + 1
        return (base * repeats)[:chunk_len]

    _write_in_chunks(path, size_bytes, supplier, should_stop)


def _write_jpg_like(path: Path, size_bytes: int, should_stop: Callable[[], bool] | None) -> None:
    header = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    footer = b"\xff\xd9"
    if size_bytes <= len(header) + len(footer):
        raise ValueError("Requested image size is too small for JPEG framing bytes.")

    payload_size = size_bytes - len(header) - len(footer)
    with open(path, "wb") as handle:
        handle.write(header)
        remaining = payload_size
        while remaining > 0:
            if should_stop is not None and should_stop():
                raise RuntimeError("File generation stopped by user.")
            chunk_len = min(CHUNK_SIZE, remaining)
            handle.write(os.urandom(chunk_len))
            remaining -= chunk_len
        handle.write(footer)


def _write_profile_file(
    path: Path,
    profile: str,
    size_bytes: int,
    should_stop: Callable[[], bool] | None,
) -> None:
    if profile == "binary":
        _write_binary(path, size_bytes, should_stop)
    elif profile == "text":
        _write_text(path, size_bytes, should_stop)
    elif profile == "image":
        _write_jpg_like(path, size_bytes, should_stop)
    else:
        raise ValueError(f"Unsupported generated profile '{profile}'.")


def _get_incremental_dir(base: Path, prefix: str) -> Path:
    base.mkdir(parents=True, exist_ok=True)
    idx = 1
    while True:
        candidate = base / f"{prefix}{idx}"
        if not candidate.exists():
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
        idx += 1


def build_generated_dataset(
    input_dir: Path,
    groups: list[str],
    on_file_generated: Callable[[GeneratedFileRecord], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> tuple[list[tuple[str, str]], GeneratedDatasetSummary]:
    """Create fresh generated files and return benchmark file tuples + summary."""
    generated_root = input_dir / "_generated"
    run_dir = _get_incremental_dir(generated_root, "batch_")

    benchmark_files: list[tuple[str, str]] = []
    total_bytes = 0
    started = time.perf_counter()

    for group in groups:
        if should_stop is not None and should_stop():
            raise RuntimeError("File generation stopped by user.")

        size_mb = parse_group_size_mb(group)
        size_bytes = size_mb * BYTES_PER_MB

        group_dir = run_dir / group
        group_dir.mkdir(parents=True, exist_ok=True)

        for profile, extension in GENERATED_PROFILES:
            if should_stop is not None and should_stop():
                raise RuntimeError("File generation stopped by user.")

            file_path = group_dir / f"{profile}_{size_mb}MB.{extension}"
            t0 = time.perf_counter()
            _write_profile_file(file_path, profile, size_bytes, should_stop)
            elapsed = max(time.perf_counter() - t0, 1e-9)
            rate_mbps = (size_bytes / BYTES_PER_MB) / elapsed

            benchmark_files.append((str(file_path), group))
            total_bytes += size_bytes

            if on_file_generated is not None:
                on_file_generated(
                    GeneratedFileRecord(
                        path=file_path,
                        group=group,
                        file_type=profile,
                        size_bytes=size_bytes,
                        elapsed_seconds=elapsed,
                        rate_mbps=rate_mbps,
                    )
                )

    total_elapsed = time.perf_counter() - started
    summary = GeneratedDatasetSummary(
        root_dir=run_dir,
        file_count=len(benchmark_files),
        total_bytes=total_bytes,
        elapsed_seconds=total_elapsed,
    )
    return benchmark_files, summary


def generate_single_file(input_dir: Path, size_mb: int, profile: str) -> str:
    """Generate a single file into an incremental directory and return its path."""
    generated_root = input_dir / "_generated"
    run_dir = _get_incremental_dir(generated_root, "single_")
    
    # Map friendly profile names to our internal names and extensions
    profile_lower = profile.lower()
    if profile_lower == "zeros":
        profile_lower = "binary"
        ext = "bin"
    elif profile_lower == "pattern":
        profile_lower = "text"
        ext = "txt"
    else: # random
        profile_lower = "image" # image is just random bytes with jpeg header
        ext = "jpg"
        
    size_bytes = size_mb * BYTES_PER_MB
    file_path = run_dir / f"{profile_lower}_{size_mb}MB.{ext}"
    _write_profile_file(file_path, profile_lower, size_bytes, None)
    
    return str(file_path)
