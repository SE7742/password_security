"""AES-256-GCM authenticated encryption ve PBKDF2 anahtar türetme."""

import base64
import hashlib
import secrets
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes


class CryptoManager:
    """AES-256-GCM authenticated encryption ve PBKDF2 anahtar türetme."""

    ITERATIONS = 600_000
    SALT_SIZE = 32
    KEY_SIZE = 32   # 256 bit
    NONCE_SIZE = 12  # GCM standart nonce

    # --- Anahtar türetme ------------------------------------------------

    @staticmethod
    def derive_key(password: str, salt: bytes) -> bytes:
        """Master paroladan AES-256 anahtarı türetir (PBKDF2-HMAC-SHA256)."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=CryptoManager.KEY_SIZE,
            salt=salt,
            iterations=CryptoManager.ITERATIONS,
        )
        return kdf.derive(password.encode("utf-8"))

    # --- Master parola hash / doğrulama ----------------------------------

    @staticmethod
    def hash_master_password(password: str) -> dict:
        """Master parolayı hash'ler; salt ve doğrulama hash'i döndürür."""
        salt = secrets.token_bytes(CryptoManager.SALT_SIZE)
        key = CryptoManager.derive_key(password, salt)
        verification_hash = hashlib.sha256(key).hexdigest()
        return {
            "salt": base64.b64encode(salt).decode("ascii"),
            "hash": verification_hash,
        }

    @staticmethod
    def verify_master_password(password: str, stored: dict) -> Optional[bytes]:
        """
        Doğrulama başarılıysa AES anahtarını döndürür, aksi hâlde None.
        Zamanlama saldırılarına karşı ``secrets.compare_digest`` kullanır.
        """
        salt = base64.b64decode(stored["salt"])
        key = CryptoManager.derive_key(password, salt)
        verification_hash = hashlib.sha256(key).hexdigest()
        if secrets.compare_digest(verification_hash, stored["hash"]):
            return key
        return None

    # --- AES-256-GCM şifreleme / çözme -----------------------------------

    @staticmethod
    def encrypt(plaintext: bytes, key: bytes) -> bytes:
        """AES-256-GCM şifrele.  Çıktı: nonce(12) || ciphertext || tag."""
        nonce = secrets.token_bytes(CryptoManager.NONCE_SIZE)
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        return nonce + ciphertext

    @staticmethod
    def decrypt(encrypted: bytes, key: bytes) -> bytes:
        """AES-256-GCM çöz.  Girdi: nonce(12) || ciphertext || tag."""
        if len(encrypted) < CryptoManager.NONCE_SIZE + 16:
            raise ValueError("Şifreli veri çok kısa, bozulmuş olabilir.")
        nonce = encrypted[: CryptoManager.NONCE_SIZE]
        ciphertext = encrypted[CryptoManager.NONCE_SIZE:]
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext, None)
