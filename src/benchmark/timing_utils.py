"""Nanosecond-precision timing wrappers for AES-CTR and AES-GCM.

Each function calls ``gc.collect()`` immediately before the timing window
opens.  Only the cipher call is timed — no file I/O happens here.
"""

from __future__ import annotations

import gc
import time

from src.crypto import aes_ctr, aes_gcm


def time_ctr_encrypt(plaintext: bytes, key: bytes, nonce: bytes) -> int:
    """Return elapsed nanoseconds for AES-CTR encryption."""
    gc.collect()
    start = time.perf_counter_ns()
    aes_ctr.encrypt(plaintext, key, nonce)
    return time.perf_counter_ns() - start


def time_ctr_decrypt(ciphertext: bytes, key: bytes, nonce: bytes) -> int:
    """Return elapsed nanoseconds for AES-CTR decryption."""
    gc.collect()
    start = time.perf_counter_ns()
    aes_ctr.decrypt(ciphertext, key, nonce)
    return time.perf_counter_ns() - start


def time_gcm_encrypt(
    plaintext: bytes, key: bytes, nonce: bytes
) -> tuple[int, bytes, bytes]:
    """Return ``(elapsed_ns, ciphertext, tag)`` for AES-GCM encryption."""
    gc.collect()
    start = time.perf_counter_ns()
    ciphertext, tag = aes_gcm.encrypt(plaintext, key, nonce)
    elapsed = time.perf_counter_ns() - start
    return elapsed, ciphertext, tag


def time_gcm_decrypt(
    ciphertext: bytes, key: bytes, nonce: bytes, tag: bytes
) -> int:
    """Return elapsed nanoseconds for AES-GCM decryption."""
    gc.collect()
    start = time.perf_counter_ns()
    aes_gcm.decrypt(ciphertext, key, nonce, tag)
    return time.perf_counter_ns() - start
