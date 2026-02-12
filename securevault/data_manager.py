"""Vault veri yönetimi: şifreleme + steganografi + CRUD işlemleri.

Veri akışı (kaydetme):
    dict -> JSON -> AES-256-GCM encrypt -> base64 -> LSB steganografi -> vault.png

Veri akışı (yükleme):
    vault.png -> LSB decode -> base64 decode -> AES-256-GCM decrypt -> JSON -> dict
"""

import base64
import json
import os
import shutil
import subprocess
import uuid
from datetime import datetime
from typing import Optional

from securevault.constants import DEFAULT_CATEGORIES, VERSION
from securevault.crypto import CryptoManager
from securevault.steganography import SteganographyManager

# Güvenlik limitleri
MAX_FIELD_LENGTH = 512          # site adı, kullanıcı adı, kategori
MAX_PASSWORD_LENGTH = 256       # şifre alanı
MAX_NOTE_LENGTH = 65_536        # not içeriği (64 KB)
MAX_MASTER_PASSWORD_LENGTH = 128


class DataManager:
    """Vault verilerini yönetir: kimlik doğrulama, CRUD, ayarlar."""

    def __init__(self, base_dir: str):
        self._base_dir = base_dir
        self._key_file = os.path.join(base_dir, "vault.key")
        self._vault_image = os.path.join(base_dir, "vault.png")
        self._key: Optional[bytes] = None
        self._data: Optional[dict] = None

    # --- Durum sorguları -------------------------------------------------

    @property
    def is_authenticated(self) -> bool:
        return self._key is not None

    def is_first_run(self) -> bool:
        return not os.path.exists(self._key_file)

    # --- Kimlik doğrulama ------------------------------------------------

    def create_master_password(self, password: str) -> None:
        """İlk çalıştırmada master parola oluşturur ve boş vault başlatır."""
        stored = CryptoManager.hash_master_password(password)
        with open(self._key_file, "w", encoding="utf-8") as fh:
            json.dump(stored, fh)
        self._restrict_file_permissions(self._key_file)

        self._key = CryptoManager.verify_master_password(password, stored)
        self._data = self._empty_vault()

        SteganographyManager.create_carrier_image(self._vault_image)
        self.save()

    def authenticate(self, password: str) -> bool:
        """Master parolayı doğrular ve vault verisini yükler."""
        if not os.path.exists(self._key_file):
            return False

        with open(self._key_file, "r", encoding="utf-8") as fh:
            stored = json.load(fh)

        key = CryptoManager.verify_master_password(password, stored)
        if key is None:
            return False

        self._key = key
        self._load_data()
        return True

    def change_master_password(self, old_password: str, new_password: str) -> bool:
        """Master parolayı değiştirir; mevcut verileri yeni anahtarla yeniden şifreler.

        Süreç:
            1. Eski parolayı doğrula
            2. Yeni parola hash/salt üret
            3. Yeni anahtarla veriyi yeniden şifrele
            4. vault.key ve vault.png güncelle
        """
        # Eski parolayı doğrula
        if not os.path.exists(self._key_file):
            return False

        with open(self._key_file, "r", encoding="utf-8") as fh:
            stored = json.load(fh)

        old_key = CryptoManager.verify_master_password(old_password, stored)
        if old_key is None:
            return False

        # Yeni parola hash/salt üret
        new_stored = CryptoManager.hash_master_password(new_password)
        new_key = CryptoManager.verify_master_password(new_password, new_stored)
        if new_key is None:
            return False

        # vault.key güncelle
        with open(self._key_file, "w", encoding="utf-8") as fh:
            json.dump(new_stored, fh)

        # Aktif anahtarı değiştir ve veriyi yeniden şifrele
        self._key = new_key
        self.save()

        return True

    @staticmethod
    def _restrict_file_permissions(path: str) -> None:
        """Dosya izinlerini sadece sahibine okuma/yazma olarak kısıtlar."""
        try:
            if os.name == "nt":
                subprocess.run(
                    ["icacls", path, "/inheritance:r", "/grant:r",
                     f"{os.environ.get('USERNAME', '')}:(R,W)"],
                    capture_output=True, timeout=5,
                )
            else:
                os.chmod(path, 0o600)
        except (OSError, subprocess.TimeoutExpired):
            pass

    def lock(self) -> None:
        """Vault'u kaydeder ve anahtarı bellekten temizler."""
        if self._key and self._data:
            self.save()
        self._key = None
        self._data = None

    # --- Veri yükleme / kaydetme -----------------------------------------

    def _empty_vault(self) -> dict:
        return {
            "version": VERSION,
            "theme": "dark",
            "custom_categories": [],
            "passwords": [],
            "notes": [],
        }

    def _load_data(self) -> None:
        """vault.png'den veri yükler; hata olursa yedek alıp boş vault oluşturur."""
        if not os.path.exists(self._vault_image):
            self._data = self._empty_vault()
            SteganographyManager.create_carrier_image(self._vault_image)
            self.save()
            return

        try:
            encoded_data = SteganographyManager.decode(self._vault_image)
            encrypted = base64.b64decode(encoded_data)
            decrypted = CryptoManager.decrypt(encrypted, self._key)
            self._data = json.loads(decrypted.decode("utf-8"))
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            # Bozuk veri — yedek al, sonra sıfırla
            self._backup_corrupt_vault()
            self._data = self._empty_vault()
            SteganographyManager.create_carrier_image(self._vault_image)
            self.save()
        except Exception as exc:
            # Beklenmeyen hata — veriyi silmeden boş vault ile devam et
            self._backup_corrupt_vault()
            self._data = self._empty_vault()
            SteganographyManager.create_carrier_image(self._vault_image)
            self.save()

    def _backup_corrupt_vault(self) -> None:
        """Bozuk vault dosyalarının yedeğini alır."""
        from datetime import datetime as _dt
        ts = _dt.now().strftime("%Y%m%d_%H%M%S")
        for src in (self._vault_image, self._key_file):
            if os.path.exists(src):
                backup = f"{src}.backup_{ts}"
                try:
                    shutil.copy2(src, backup)
                except OSError:
                    pass

    def save(self) -> None:
        """Vault verisini şifreler ve görüntüye gömer."""
        if self._key is None or self._data is None:
            return

        json_bytes = json.dumps(self._data, ensure_ascii=False).encode("utf-8")
        encrypted = CryptoManager.encrypt(json_bytes, self._key)
        encoded = base64.b64encode(encrypted)

        # Kapasite kontrolü — gerekirse daha büyük taşıyıcı oluştur
        capacity = SteganographyManager.get_capacity(self._vault_image)
        if len(encoded) + 36 > capacity:
            side = 1024
            while True:
                side += 512
                potential = ((side * side * 3) // 8) - 36
                if potential >= len(encoded):
                    break
            SteganographyManager.create_carrier_image(self._vault_image, side, side)

        SteganographyManager.encode(self._vault_image, encoded)

    # --- Şifre CRUD ------------------------------------------------------

    def get_passwords(self) -> list[dict]:
        return list(self._data.get("passwords", []))

    def get_password(self, pwd_id: str) -> Optional[dict]:
        for p in self._data.get("passwords", []):
            if p["id"] == pwd_id:
                return p
        return None

    @staticmethod
    def _validate_entry(entry: dict) -> None:
        """Kayıt alanlarının uzunluklarını doğrular."""
        for key in ("site_name", "username", "category"):
            val = entry.get(key, "")
            if len(val) > MAX_FIELD_LENGTH:
                raise ValueError(
                    f"{key} çok uzun (maks {MAX_FIELD_LENGTH} karakter).")
        if len(entry.get("password", "")) > MAX_PASSWORD_LENGTH:
            raise ValueError(
                f"Şifre çok uzun (maks {MAX_PASSWORD_LENGTH} karakter).")
        if len(entry.get("notes", "")) > MAX_NOTE_LENGTH:
            raise ValueError(
                f"Not çok uzun (maks {MAX_NOTE_LENGTH} karakter).")

    def add_password(self, entry: dict) -> str:
        self._validate_entry(entry)
        now = datetime.now().isoformat()
        record = {**entry}
        record["id"] = uuid.uuid4().hex
        record["created_at"] = now
        record["updated_at"] = now
        self._data.setdefault("passwords", []).append(record)
        self.save()
        return record["id"]

    def update_password(self, pwd_id: str, updates: dict) -> bool:
        protected = {"id", "created_at"}
        safe = {k: v for k, v in updates.items() if k not in protected}
        for p in self._data.get("passwords", []):
            if p["id"] == pwd_id:
                p.update(safe)
                p["updated_at"] = datetime.now().isoformat()
                self.save()
                return True
        return False

    def delete_password(self, pwd_id: str) -> bool:
        passwords = self._data.get("passwords", [])
        before = len(passwords)
        self._data["passwords"] = [p for p in passwords if p["id"] != pwd_id]
        if len(self._data["passwords"]) < before:
            self.save()
            return True
        return False

    def search_passwords(self, query: str = "", category: str = "") -> list[dict]:
        results = self._data.get("passwords", [])
        if category and category != "Tümü":
            results = [p for p in results if p.get("category") == category]
        if query:
            q = query.lower()
            results = [
                p for p in results
                if q in p.get("site_name", "").lower()
                or q in p.get("username", "").lower()
            ]
        return results

    # --- Not CRUD --------------------------------------------------------

    def get_notes(self) -> list[dict]:
        return list(self._data.get("notes", []))

    def get_note(self, note_id: str) -> Optional[dict]:
        for n in self._data.get("notes", []):
            if n["id"] == note_id:
                return n
        return None

    def add_note(self, note: dict) -> str:
        now = datetime.now().isoformat()
        record = {**note}
        record["id"] = uuid.uuid4().hex
        record["created_at"] = now
        record["updated_at"] = now
        self._data.setdefault("notes", []).append(record)
        self.save()
        return record["id"]

    def update_note(self, note_id: str, updates: dict) -> bool:
        protected = {"id", "created_at"}
        safe = {k: v for k, v in updates.items() if k not in protected}
        for n in self._data.get("notes", []):
            if n["id"] == note_id:
                n.update(safe)
                n["updated_at"] = datetime.now().isoformat()
                self.save()
                return True
        return False

    def delete_note(self, note_id: str) -> bool:
        notes = self._data.get("notes", [])
        before = len(notes)
        self._data["notes"] = [n for n in notes if n["id"] != note_id]
        if len(self._data["notes"]) < before:
            self.save()
            return True
        return False

    # --- Ayarlar ---------------------------------------------------------

    def get_theme(self) -> str:
        return self._data.get("theme", "dark") if self._data else "dark"

    def set_theme(self, theme: str) -> None:
        if self._data is not None:
            self._data["theme"] = theme
            self.save()

    def get_all_categories(self) -> list[str]:
        custom = self._data.get("custom_categories", []) if self._data else []
        return DEFAULT_CATEGORIES + [c for c in custom if c not in DEFAULT_CATEGORIES]

    def add_custom_category(self, name: str) -> None:
        if self._data is None:
            return
        cats = self._data.setdefault("custom_categories", [])
        if name not in cats and name not in DEFAULT_CATEGORIES:
            cats.append(name)
            self.save()
