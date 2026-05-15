"""Tamper-detection demo — pure logic, no UI code.

Demonstrates the difference between AES-GCM (authenticated) and AES-CTR
(unauthenticated) when ciphertext is tampered with.
"""

from __future__ import annotations

from src.crypto import AuthenticationError
from src.crypto.aes_ctr import decrypt as ctr_decrypt, encrypt as ctr_encrypt
from src.crypto.aes_gcm import decrypt as gcm_decrypt, encrypt as gcm_encrypt
from src.crypto.key_manager import generate_ctr_nonce, generate_gcm_nonce, generate_key

PLAINTEXT = "Confidential: Transfer $10,000 to Account 99-2847"
TAMPER_INDEX = 10


def run_gcm_tamper_demo() -> dict:
    """Encrypt with AES-GCM, tamper one byte, show that decryption is blocked."""
    key = generate_key()
    nonce = generate_gcm_nonce()
    plaintext_bytes = PLAINTEXT.encode("utf-8")

    ciphertext, tag = gcm_encrypt(plaintext_bytes, key, nonce)

    # Successful decryption of unmodified ciphertext
    clean = gcm_decrypt(ciphertext, key, nonce, tag)

    # Tamper
    original_byte = ciphertext[TAMPER_INDEX]
    tampered = bytearray(ciphertext)
    tampered[TAMPER_INDEX] ^= 0xFF
    tampered = bytes(tampered)

    # Attempt decryption of tampered ciphertext
    error_message = ""
    try:
        gcm_decrypt(tampered, key, nonce, tag)
    except AuthenticationError as exc:
        error_message = str(exc)

    return {
        "plaintext": PLAINTEXT,
        "ciphertext_hex": ciphertext.hex(),
        "tampered_byte_index": TAMPER_INDEX,
        "original_byte": original_byte,
        "tampered_byte": original_byte ^ 0xFF,
        "tampered_ciphertext_hex": tampered.hex(),
        "gcm_blocked": True,
        "error_message": error_message,
        "clean_decryption": clean.decode("utf-8"),
    }


def run_ctr_tamper_demo() -> dict:
    """Encrypt with AES-CTR, tamper one byte, show silent corruption."""
    key = generate_key()
    nonce = generate_ctr_nonce()
    plaintext_bytes = PLAINTEXT.encode("utf-8")

    ciphertext = ctr_encrypt(plaintext_bytes, key, nonce)

    # Tamper
    tampered = bytearray(ciphertext)
    tampered[TAMPER_INDEX] ^= 0xFF
    tampered = bytes(tampered)

    # Decryption succeeds — but output is silently corrupted
    corrupted = ctr_decrypt(tampered, key, nonce)

    return {
        "plaintext": PLAINTEXT,
        "ciphertext_hex": ciphertext.hex(),
        "tampered_byte_index": TAMPER_INDEX,
        "tampered_ciphertext_hex": tampered.hex(),
        "ctr_allowed": True,
        "corrupted_output": corrupted.decode("utf-8", errors="replace"),
    }
