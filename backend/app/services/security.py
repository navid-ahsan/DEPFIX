"""Security utilities for the application."""

import hashlib
import os
from typing import Tuple


def hash_key(key: str, salt: str = None) -> str:
    """
    Hash an API key securely.
    
    Args:
        key: The key to hash
        salt: Optional salt (generated if not provided)
        
    Returns:
        Hashed key with salt
    """
    if not salt:
        salt = os.urandom(32).hex()
    
    # Hash the key with salt
    hashed = hashlib.pbkdf2_hmac(
        'sha256',
        key.encode('utf-8'),
        salt.encode('utf-8'),
        100000,  # iterations
    )
    
    return f"{salt}${hashed.hex()}"


def verify_key(key: str, hashed_key: str) -> bool:
    """
    Verify a key against its hash.
    
    Args:
        key: The key to verify
        hashed_key: The hashed key to compare
        
    Returns:
        True if key matches hash
    """
    try:
        salt, key_hash = hashed_key.split('$')
        new_hash = hashlib.pbkdf2_hmac(
            'sha256',
            key.encode('utf-8'),
            salt.encode('utf-8'),
            100000,
        )
        return new_hash.hex() == key_hash
    except Exception:
        return False


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token."""
    return os.urandom(length // 2).hex()
