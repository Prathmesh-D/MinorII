"""AES-CTR encryption and decryption."""

from __future__ import annotations

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from src.crypto import CryptoError


def encrypt(plaintext: bytes, key: bytes, nonce: bytes) -> bytes:
    """Encrypt *plaintext* with AES-CTR.

    Returns the ciphertext (same length as plaintext).
    """
    if len(nonce) != 16:
        raise ValueError(f"CTR nonce must be 16 bytes, got {len(nonce)}")
    try:
        cipher = Cipher(algorithms.AES(key), modes.CTR(nonce))
        encryptor = cipher.encryptor()
        return encryptor.update(plaintext) + encryptor.finalize()
    except Exception as exc:
        raise CryptoError(f"AES-CTR encryption failed: {exc}") from exc


def decrypt(ciphertext: bytes, key: bytes, nonce: bytes) -> bytes:
    """Decrypt *ciphertext* with AES-CTR.

    Returns the plaintext.
    """
    if len(nonce) != 16:
        raise ValueError(f"CTR nonce must be 16 bytes, got {len(nonce)}")
    try:
        cipher = Cipher(algorithms.AES(key), modes.CTR(nonce))
        decryptor = cipher.decryptor()
        return decryptor.update(ciphertext) + decryptor.finalize()
    except Exception as exc:
        raise CryptoError(f"AES-CTR decryption failed: {exc}") from exc
