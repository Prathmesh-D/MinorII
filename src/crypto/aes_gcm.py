"""AES-GCM encryption and decryption."""

from __future__ import annotations

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

from src.crypto import AuthenticationError, CryptoError


def encrypt(plaintext: bytes, key: bytes, nonce: bytes) -> tuple[bytes, bytes]:
    """Encrypt *plaintext* with AES-GCM.

    Returns ``(ciphertext, tag)`` where *tag* is 16 bytes.
    """
    if len(nonce) != 12:
        raise ValueError(f"GCM nonce must be 12 bytes, got {len(nonce)}")
    try:
        aesgcm = AESGCM(key)
        # AESGCM.encrypt returns ciphertext || tag (last 16 bytes)
        ct_with_tag = aesgcm.encrypt(nonce, plaintext, None)
        ciphertext, tag = ct_with_tag[:-16], ct_with_tag[-16:]
        return ciphertext, tag
    except Exception as exc:
        raise CryptoError(f"AES-GCM encryption failed: {exc}") from exc


def decrypt(ciphertext: bytes, key: bytes, nonce: bytes, tag: bytes) -> bytes:
    """Decrypt *ciphertext* with AES-GCM, verifying the authentication *tag*.

    Raises :class:`AuthenticationError` if the tag does not match.
    """
    if len(nonce) != 12:
        raise ValueError(f"GCM nonce must be 12 bytes, got {len(nonce)}")
    try:
        aesgcm = AESGCM(key)
        # AESGCM.decrypt expects ciphertext || tag
        return aesgcm.decrypt(nonce, ciphertext + tag, None)
    except InvalidTag as exc:
        raise AuthenticationError(
            "GCM authentication failed — ciphertext or tag was tampered with"
        ) from exc
    except Exception as exc:
        raise CryptoError(f"AES-GCM decryption failed: {exc}") from exc
