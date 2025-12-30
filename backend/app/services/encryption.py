"""Token encryption utilities for securely storing sensitive tokens.

Uses Fernet symmetric encryption (AES-128-CBC with HMAC) derived from
the JWT secret key. This ensures tokens are encrypted at rest but can
be decrypted when needed for API calls.
"""

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

logger = logging.getLogger(__name__)


def _get_fernet_key() -> bytes:
    """Derive a Fernet-compatible key from the JWT secret.

    Fernet requires a 32-byte base64-encoded key.
    We derive this from the JWT secret using SHA-256.
    """
    # Use SHA-256 to get a consistent 32-byte key from the secret
    key_bytes = hashlib.sha256(settings.jwt_secret_key.encode()).digest()
    # Fernet expects base64-encoded key
    return base64.urlsafe_b64encode(key_bytes)


def _get_fernet() -> Fernet:
    """Get a Fernet instance for encryption/decryption."""
    return Fernet(_get_fernet_key())


def encrypt_token(plaintext_token: str) -> str:
    """Encrypt a token for secure storage.

    Args:
        plaintext_token: The token to encrypt

    Returns:
        Base64-encoded encrypted token
    """
    fernet = _get_fernet()
    encrypted_bytes = fernet.encrypt(plaintext_token.encode())
    return encrypted_bytes.decode()


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a stored token for use.

    Args:
        encrypted_token: The encrypted token from the database

    Returns:
        The original plaintext token

    Raises:
        ValueError: If decryption fails (invalid or corrupted token)
    """
    try:
        fernet = _get_fernet()
        decrypted_bytes = fernet.decrypt(encrypted_token.encode())
        return decrypted_bytes.decode()
    except InvalidToken as e:
        logger.error("Failed to decrypt token - may be corrupted or key changed")
        raise ValueError("Failed to decrypt token") from e


def mask_token(plaintext_token: str) -> str:
    """Create a masked preview of a token for display.

    Shows only the last 4 characters, with the rest masked.
    Example: "sk-ant-xxx...abcd"

    Args:
        plaintext_token: The token to mask

    Returns:
        Masked token string safe for display
    """
    if len(plaintext_token) <= 8:
        return "****"

    # Show prefix (up to first 8 chars) and last 4 chars
    prefix = plaintext_token[:8] if len(plaintext_token) > 12 else plaintext_token[:4]
    suffix = plaintext_token[-4:]
    return f"{prefix}...{suffix}"
