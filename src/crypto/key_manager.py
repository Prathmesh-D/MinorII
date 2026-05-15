"""Key and nonce generation for AES-CTR and AES-GCM."""

from __future__ import annotations

import os


def generate_key(size: int = 32) -> bytes:
    """Return a random AES-256 key (32 bytes by default)."""
    return os.urandom(size)


def generate_ctr_nonce(size: int = 16) -> bytes:
    """Return a random nonce for AES-CTR (16 bytes by default)."""
    return os.urandom(size)


def generate_gcm_nonce(size: int = 12) -> bytes:
    """Return a random nonce for AES-GCM (12 bytes by default)."""
    return os.urandom(size)
