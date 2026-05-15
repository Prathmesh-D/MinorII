"""Benchmark runner — orchestrates timed experiments per file."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from src.benchmark.experiment_config import Config
from src.benchmark.timing_utils import (
    time_ctr_decrypt,
    time_ctr_encrypt,
    time_gcm_decrypt,
    time_gcm_encrypt,
)
from src.crypto.key_manager import generate_ctr_nonce, generate_gcm_nonce, generate_key


@dataclass
class BenchmarkResult:
    """Raw result of a single file × mode experiment."""

    timestamp: str
    file_group: str
    file_type: str
    mode: str  # "AES-CTR" or "AES-GCM"
    file_size_bytes: int
    file_size_mb: float
    raw_enc_times_ns: list[int]
    raw_dec_times_ns: list[int]
    avg_enc_time_ns: float
    avg_dec_time_ns: float


class BenchmarkRunner:
    """Loads a file once, then runs timed encrypt/decrypt experiments."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def load_file(path: str) -> bytes:
        """Read an entire file into memory."""
        with open(path, "rb") as f:
            return f.read()

    @staticmethod
    def infer_file_type(filename: str) -> str:
        """Map file extension to a human-friendly type label."""
        ext = Path(filename).suffix.lower()
        mapping = {
            ".txt": "text",
            ".jpg": "image",
            ".jpeg": "image",
            ".png": "image",
            ".bin": "binary",
        }
        return mapping.get(ext, "unknown")

    # ------------------------------------------------------------------
    # Core experiment
    # ------------------------------------------------------------------

    def run_experiment(
        self,
        file_path: str,
        file_group: str,
        config: Config,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> list[BenchmarkResult]:
        """Run AES-CTR and AES-GCM benchmarks for *file_path*.

        Parameters
        ----------
        file_path:
            Absolute or relative path to the input file.
        file_group:
            Group label, e.g. ``"F1_1MB"``.
        config:
            Loaded :class:`Config` instance.
        progress_callback:
            Optional ``callback(run_number, total_runs)`` invoked after
            every individual run so the UI can update a progress bar.

        Returns
        -------
        list[BenchmarkResult]
            Two results — one for AES-CTR, one for AES-GCM.
        """
        plaintext = self.load_file(file_path)
        file_size_bytes = len(plaintext)
        file_size_mb = file_size_bytes / 1_048_576
        file_type = self.infer_file_type(file_path)
        timestamp = datetime.now(timezone.utc).isoformat()

        total_runs = config.runs
        warmup = config.warmup_runs

        results: list[BenchmarkResult] = []

        for mode in ("AES-CTR", "AES-GCM"):
            raw_enc: list[int] = []
            raw_dec: list[int] = []

            for i in range(total_runs):
                key = generate_key(config.key_size_bytes)

                if mode == "AES-CTR":
                    nonce = generate_ctr_nonce(config.ctr_nonce_size)
                    enc_ns = time_ctr_encrypt(plaintext, key, nonce)
                    # Need actual ciphertext for decryption timing
                    from src.crypto.aes_ctr import encrypt as ctr_enc

                    ct = ctr_enc(plaintext, key, nonce)
                    dec_ns = time_ctr_decrypt(ct, key, nonce)
                else:
                    nonce = generate_gcm_nonce(config.gcm_nonce_size)
                    enc_ns, ct, tag = time_gcm_encrypt(plaintext, key, nonce)
                    dec_ns = time_gcm_decrypt(ct, key, nonce, tag)

                raw_enc.append(enc_ns)
                raw_dec.append(dec_ns)

                if progress_callback is not None:
                    progress_callback(i + 1, total_runs)

            # Discard warm-up run(s), average the rest
            kept_enc = raw_enc[warmup:]
            kept_dec = raw_dec[warmup:]

            avg_enc = sum(kept_enc) / len(kept_enc) if kept_enc else 0.0
            avg_dec = sum(kept_dec) / len(kept_dec) if kept_dec else 0.0

            results.append(
                BenchmarkResult(
                    timestamp=timestamp,
                    file_group=file_group,
                    file_type=file_type,
                    mode=mode,
                    file_size_bytes=file_size_bytes,
                    file_size_mb=round(file_size_mb, 6),
                    raw_enc_times_ns=raw_enc,
                    raw_dec_times_ns=raw_dec,
                    avg_enc_time_ns=round(avg_enc, 2),
                    avg_dec_time_ns=round(avg_dec, 2),
                )
            )

        return results
