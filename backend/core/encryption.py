import os
import base64
from cryptography.fernet import Fernet
import logging

logger = logging.getLogger("QLM.Security")

KEY_FILE = os.path.join("data", "secret.key")

class EncryptionManager:
    def __init__(self):
        self.key = self._load_or_generate_key()
        self.fernet = Fernet(self.key)

    def _load_or_generate_key(self) -> bytes:
        if os.path.exists(KEY_FILE):
            with open(KEY_FILE, "rb") as f:
                return f.read()
        else:
            logger.warning("No encryption key found. Generating new key...")
            key = Fernet.generate_key()
            os.makedirs(os.path.dirname(KEY_FILE), exist_ok=True)
            with open(KEY_FILE, "wb") as f:
                f.write(key)
            return key

    def encrypt(self, data: str) -> str:
        if not data: return ""
        try:
            return self.fernet.encrypt(data.encode()).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return data # Fail open? Or raise? Better to fail safe, but for migration maybe check if already encrypted.

    def decrypt(self, token: str) -> str:
        if not token: return ""
        try:
            return self.fernet.decrypt(token.encode()).decode()
        except Exception:
            # Maybe it's not encrypted (legacy plain text)
            # Fernet tokens are url-safe base64 strings.
            # If decryption fails, return as is (assuming it was plain text)
            return token

encryption = EncryptionManager()
