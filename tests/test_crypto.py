"""Tests for the AES-CTR and AES-GCM crypto layer."""

import os
import pytest

from src.crypto import AuthenticationError
from src.crypto.aes_ctr import encrypt as ctr_encrypt, decrypt as ctr_decrypt
from src.crypto.aes_gcm import encrypt as gcm_encrypt, decrypt as gcm_decrypt


PLAINTEXT = b"The quick brown fox jumps over the lazy dog"
KEY = os.urandom(32)


def test_ctr_roundtrip():
    """CTR encrypt then decrypt returns original plaintext."""
    nonce = os.urandom(16)
    ct = ctr_encrypt(PLAINTEXT, KEY, nonce)
    pt = ctr_decrypt(ct, KEY, nonce)
    assert pt == PLAINTEXT


def test_gcm_roundtrip():
    """GCM encrypt then decrypt returns original plaintext."""
    nonce = os.urandom(12)
    ct, tag = gcm_encrypt(PLAINTEXT, KEY, nonce)
    pt = gcm_decrypt(ct, KEY, nonce, tag)
    assert pt == PLAINTEXT


def test_gcm_tamper_raises_authentication_error():
    """Flipping a bit in GCM ciphertext must raise AuthenticationError."""
    nonce = os.urandom(12)
    ct, tag = gcm_encrypt(PLAINTEXT, KEY, nonce)

    # Tamper: flip the first byte of ciphertext
    tampered = bytes([ct[0] ^ 0xFF]) + ct[1:]
    with pytest.raises(AuthenticationError):
        gcm_decrypt(tampered, KEY, nonce, tag)


def test_ctr_tamper_silent_corruption():
    """CTR decrypts tampered ciphertext without error — output is corrupted."""
    nonce = os.urandom(16)
    ct = ctr_encrypt(PLAINTEXT, KEY, nonce)

    # Tamper: flip the first byte of ciphertext
    tampered = bytes([ct[0] ^ 0xFF]) + ct[1:]
    pt = ctr_decrypt(tampered, KEY, nonce)

    # Decryption succeeds but plaintext is silently corrupted
    assert pt != PLAINTEXT
