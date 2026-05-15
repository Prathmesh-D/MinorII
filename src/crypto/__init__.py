class CryptoError(Exception):
    """Base exception for cryptographic operations."""
    pass


class AuthenticationError(CryptoError):
    """Raised when GCM authentication tag verification fails."""
    pass
