"""Kriptografik olarak güvenli rastgele şifre üretimi ve güç analizi."""

import math
import secrets
import string


class PasswordGenerator:
    """``secrets`` modülü ile şifre üretimi ve entropi hesabı."""

    @staticmethod
    def generate(
        length: int = 16,
        uppercase: bool = True,
        lowercase: bool = True,
        digits: bool = True,
        special: bool = True,
    ) -> str:
        """
        ``secrets.choice`` ile şifre üretir.
        Seçili her karakter kümesinden en az 1 karakter içerir.
        """
        if length < 1:
            raise ValueError("Şifre uzunluğu en az 1 olmalıdır.")

        pools: list[str] = []
        if uppercase:
            pools.append(string.ascii_uppercase)
        if lowercase:
            pools.append(string.ascii_lowercase)
        if digits:
            pools.append(string.digits)
        if special:
            pools.append(string.punctuation)

        if not pools:
            raise ValueError("En az bir karakter kümesi seçilmelidir.")

        if length < len(pools):
            raise ValueError(
                f"Uzunluk ({length}), seçili küme sayısından ({len(pools)}) az olamaz."
            )

        combined = "".join(pools)
        while True:
            # Her kümeden 1 zorunlu karakter + geri kalanı rastgele
            password_chars = [secrets.choice(pool) for pool in pools]
            remaining = length - len(pools)
            password_chars.extend(secrets.choice(combined) for _ in range(remaining))

            # Fisher-Yates shuffle (secrets tabanlı)
            for i in range(len(password_chars) - 1, 0, -1):
                j = secrets.randbelow(i + 1)
                password_chars[i], password_chars[j] = password_chars[j], password_chars[i]

            password = "".join(password_chars)

            # Doğrulama: her kümeden gerçekten karakter var mı?
            if all(any(c in pool for c in password) for pool in pools):
                return password

    @staticmethod
    def get_entropy(password: str) -> float:
        """Karakter havuzu tabanlı entropi (bit) hesaplar."""
        if not password:
            return 0.0

        pool_size = 0
        if any(c in string.ascii_lowercase for c in password):
            pool_size += 26
        if any(c in string.ascii_uppercase for c in password):
            pool_size += 26
        if any(c in string.digits for c in password):
            pool_size += 10
        if any(c in string.punctuation for c in password):
            pool_size += 32
        if any(ord(c) > 127 for c in password):
            pool_size += 128

        if pool_size == 0:
            pool_size = 256

        return math.log2(pool_size) * len(password)

    @staticmethod
    def calculate_strength(password: str) -> dict:
        """Şifre gücünü analiz eder; skor, etiket ve renk anahtarı döndürür."""
        if not password:
            return {"entropy": 0, "score": 0, "label": "Boş", "color": "muted"}

        entropy = PasswordGenerator.get_entropy(password)

        if entropy < 28:
            return {"entropy": entropy, "score": 10, "label": "Çok Zayıf", "color": "error"}
        if entropy < 36:
            return {"entropy": entropy, "score": 25, "label": "Zayıf", "color": "error"}
        if entropy < 60:
            return {"entropy": entropy, "score": 50, "label": "Orta", "color": "warning"}
        if entropy < 128:
            return {"entropy": entropy, "score": 75, "label": "Güçlü", "color": "success"}
        return {"entropy": entropy, "score": 100, "label": "Çok Güçlü", "color": "accent"}
