import base64
import hashlib
import bcrypt
from cryptography.fernet import Fernet

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def get_fernet(secret_key: str) -> Fernet:
    """Generate a Fernet key from a secret string."""
    key_bytes = hashlib.sha256(secret_key.encode("utf-8")).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)

def encrypt_config(config_str: str, secret_key: str) -> str:
    """Encrypt config JSON string using Fernet."""
    f = get_fernet(secret_key)
    return f.encrypt(config_str.encode("utf-8")).decode("utf-8")

def decrypt_config(encrypted_str: str, secret_key: str) -> str:
    """Decrypt encrypted config JSON string using Fernet."""
    f = get_fernet(secret_key)
    return f.decrypt(encrypted_str.encode("utf-8")).decode("utf-8")
