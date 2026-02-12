"""SecureVault — Kapsamlı birim test paketi.

Tüm modülleri edge case'ler ve performans testleriyle doğrular.
Çalıştırma:
    python test_all.py
"""

import base64
import json
import math
import os
import secrets
import shutil
import string
import sys
import tempfile
import time

# Proje kök dizinini path'e ekle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from securevault.crypto import CryptoManager
from securevault.steganography import SteganographyManager
from securevault.generator import PasswordGenerator
from securevault.health import PasswordHealthAnalyzer
from securevault.data_manager import DataManager

# ─── Yardımcılar ────────────────────────────────────────────────────────
passed = 0
failed = 0
errors: list[str] = []


def ok(test_name: str) -> None:
    global passed
    passed += 1
    print(f"  ✓ {test_name}")


def fail(test_name: str, detail: str = "") -> None:
    global failed
    failed += 1
    msg = f"  ✗ {test_name}" + (f" → {detail}" if detail else "")
    print(msg)
    errors.append(msg)


def section(title: str) -> None:
    print(f"\n{'═'*60}")
    print(f"  {title}")
    print(f"{'═'*60}")


# ═══════════════════════════════════════════════════════════════
#  1. CryptoManager testleri
# ═══════════════════════════════════════════════════════════════
def test_crypto():
    section("CryptoManager")

    # --- 1.1 Anahtar türetme deterministik mi? ---
    salt = secrets.token_bytes(32)
    k1 = CryptoManager.derive_key("test_pass", salt)
    k2 = CryptoManager.derive_key("test_pass", salt)
    if k1 == k2:
        ok("Aynı parola + salt → aynı anahtar")
    else:
        fail("Aynı parola + salt → aynı anahtar", "Anahtarlar farklı")

    # --- 1.2 Farklı salt → farklı anahtar ---
    salt2 = secrets.token_bytes(32)
    k3 = CryptoManager.derive_key("test_pass", salt2)
    if k1 != k3:
        ok("Farklı salt → farklı anahtar")
    else:
        fail("Farklı salt → farklı anahtar")

    # --- 1.3 Master parola hash & verify ---
    stored = CryptoManager.hash_master_password("MySuperSecret123!")
    key = CryptoManager.verify_master_password("MySuperSecret123!", stored)
    if key is not None and len(key) == 32:
        ok("Master parola hash & verify başarılı (32 byte key)")
    else:
        fail("Master parola hash & verify", f"key={key}")

    # --- 1.4 Yanlış parola → None ---
    bad_key = CryptoManager.verify_master_password("WrongPassword", stored)
    if bad_key is None:
        ok("Yanlış parola → None döndü")
    else:
        fail("Yanlış parola → None beklendi", f"key={bad_key}")

    # --- 1.5 Boş parola (edge case) ---
    stored_empty = CryptoManager.hash_master_password("")
    key_empty = CryptoManager.verify_master_password("", stored_empty)
    if key_empty is not None:
        ok("Boş parola hash/verify çalışıyor")
    else:
        fail("Boş parola hash/verify")

    # --- 1.6 Encrypt/Decrypt round-trip ---
    plaintext = b"Hello, World! \xc3\x87ok gizli veri 12345"
    encrypted = CryptoManager.encrypt(plaintext, key)
    decrypted = CryptoManager.decrypt(encrypted, key)
    if decrypted == plaintext:
        ok("Encrypt → Decrypt round-trip başarılı")
    else:
        fail("Encrypt → Decrypt", f"Beklenen: {plaintext}, Alınan: {decrypted}")

    # --- 1.7 Boş veri encrypt/decrypt ---
    enc_empty = CryptoManager.encrypt(b"", key)
    dec_empty = CryptoManager.decrypt(enc_empty, key)
    if dec_empty == b"":
        ok("Boş veri encrypt/decrypt başarılı")
    else:
        fail("Boş veri encrypt/decrypt")

    # --- 1.8 Yanlış anahtar ile decrypt → hata ---
    wrong_key = secrets.token_bytes(32)
    try:
        CryptoManager.decrypt(encrypted, wrong_key)
        fail("Yanlış anahtar ile decrypt → hata beklendi")
    except Exception:
        ok("Yanlış anahtar ile decrypt → hata fırlatıldı")

    # --- 1.9 Bozuk veri ile decrypt → hata ---
    try:
        CryptoManager.decrypt(b"short", key)
        fail("Çok kısa veri → ValueError beklendi")
    except ValueError:
        ok("Çok kısa veri → ValueError fırlatıldı")
    except Exception as e:
        fail("Çok kısa veri → ValueError beklendi", str(type(e)))

    # --- 1.10 Büyük veri encrypt/decrypt ---
    big_data = secrets.token_bytes(1_000_000)  # 1 MB
    enc_big = CryptoManager.encrypt(big_data, key)
    dec_big = CryptoManager.decrypt(enc_big, key)
    if dec_big == big_data:
        ok("1 MB veri encrypt/decrypt başarılı")
    else:
        fail("1 MB veri encrypt/decrypt")

    # --- 1.11 Nonce benzersizliği ---
    enc1 = CryptoManager.encrypt(plaintext, key)
    enc2 = CryptoManager.encrypt(plaintext, key)
    if enc1 != enc2:
        ok("Aynı veri, farklı nonce → farklı ciphertext")
    else:
        fail("Nonce benzersizliği — ciphertext'ler aynı")


# ═══════════════════════════════════════════════════════════════
#  2. SteganographyManager testleri
# ═══════════════════════════════════════════════════════════════
def test_steganography():
    section("SteganographyManager")

    tmpdir = tempfile.mkdtemp(prefix="steg_test_")
    try:
        img_path = os.path.join(tmpdir, "test.png")

        # --- 2.1 Taşıyıcı oluşturma ---
        SteganographyManager.create_carrier_image(img_path, 256, 256)
        if os.path.exists(img_path) and os.path.getsize(img_path) > 0:
            ok("Taşıyıcı görüntü oluşturuldu")
        else:
            fail("Taşıyıcı görüntü oluşturma")

        # --- 2.2 Kapasite hesaplama ---
        cap = SteganographyManager.get_capacity(img_path)
        expected_cap = ((256 * 256 * 3) // 8) - 36
        if cap == expected_cap:
            ok(f"Kapasite doğru: {cap} bayt")
        else:
            fail(f"Kapasite", f"Beklenen: {expected_cap}, Alınan: {cap}")

        # --- 2.3 Encode/Decode round-trip ---
        data = b"Merhaba Dunya! AES-256-GCM ile sifrelenmis veri."
        SteganographyManager.encode(img_path, data)
        decoded = SteganographyManager.decode(img_path)
        if decoded == data:
            ok("Encode → Decode round-trip başarılı")
        else:
            fail("Encode → Decode round-trip")

        # --- 2.4 Boş veri encode/decode ---
        img2 = os.path.join(tmpdir, "test2.png")
        SteganographyManager.create_carrier_image(img2, 64, 64)
        SteganographyManager.encode(img2, b"")
        decoded_empty = SteganographyManager.decode(img2)
        if decoded_empty == b"":
            ok("Boş veri encode/decode başarılı")
        else:
            fail("Boş veri encode/decode")

        # --- 2.5 Kapasite aşımı → hata ---
        img3 = os.path.join(tmpdir, "tiny.png")
        SteganographyManager.create_carrier_image(img3, 8, 8)
        cap_tiny = SteganographyManager.get_capacity(img3)
        try:
            SteganographyManager.encode(img3, secrets.token_bytes(cap_tiny + 100))
            fail("Kapasite aşımı → ValueError beklendi")
        except ValueError:
            ok("Kapasite aşımı → ValueError fırlatıldı")

        # --- 2.6 Bozuk görüntü → hata ---
        img4 = os.path.join(tmpdir, "corrupt.png")
        SteganographyManager.create_carrier_image(img4, 128, 128)
        # Orijinal veri yaz, sonra pikselleri boz
        SteganographyManager.encode(img4, b"gizli veri")
        # Bozma: dosyanın ortasına rastgele bayt yaz
        with open(img4, "r+b") as f:
            f.seek(500)
            f.write(secrets.token_bytes(200))
        try:
            SteganographyManager.decode(img4)
            # Bozulma her zaman yakalanmayabilir, ama çoğu durumda hata bekleriz
            fail("Bozuk görüntü → hata beklendi (veya checksum uyuşmazlığı)")
        except Exception:
            ok("Bozuk görüntü → hata yakalandı")

        # --- 2.7 Maksimum kapasite encode/decode ---
        img5 = os.path.join(tmpdir, "maxcap.png")
        SteganographyManager.create_carrier_image(img5, 128, 128)
        cap5 = SteganographyManager.get_capacity(img5)
        max_data = secrets.token_bytes(cap5)
        SteganographyManager.encode(img5, max_data)
        decoded_max = SteganographyManager.decode(img5)
        if decoded_max == max_data:
            ok(f"Maksimum kapasite ({cap5} bayt) encode/decode başarılı")
        else:
            fail("Maksimum kapasite encode/decode")

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════
#  3. PasswordGenerator testleri
# ═══════════════════════════════════════════════════════════════
def test_generator():
    section("PasswordGenerator")

    # --- 3.1 Varsayılan üretim ---
    pw = PasswordGenerator.generate()
    if len(pw) == 16:
        ok(f"Varsayılan uzunluk: 16 ('{pw[:4]}…')")
    else:
        fail(f"Varsayılan uzunluk", f"Beklenen: 16, Alınan: {len(pw)}")

    # --- 3.2 Her karakter kümesi mevcut ---
    has_upper = any(c in string.ascii_uppercase for c in pw)
    has_lower = any(c in string.ascii_lowercase for c in pw)
    has_digit = any(c in string.digits for c in pw)
    has_special = any(c in string.punctuation for c in pw)
    if all([has_upper, has_lower, has_digit, has_special]):
        ok("Tüm karakter kümeleri mevcut")
    else:
        fail("Karakter kümeleri",
             f"U={has_upper} L={has_lower} D={has_digit} S={has_special}")

    # --- 3.3 Minimum uzunluk (length=4, 4 küme) ---
    pw4 = PasswordGenerator.generate(length=4)
    if len(pw4) == 4:
        ok("Minimum uzunluk (4 karakter, 4 küme)")
    else:
        fail("Minimum uzunluk")

    # --- 3.4 length < küme sayısı → ValueError ---
    try:
        PasswordGenerator.generate(length=2)
        fail("length=2, 4 küme → ValueError beklendi")
    except ValueError:
        ok("length=2, 4 küme → ValueError fırlatıldı")

    # --- 3.5 length=0 → ValueError ---
    try:
        PasswordGenerator.generate(length=0)
        fail("length=0 → ValueError beklendi")
    except ValueError:
        ok("length=0 → ValueError fırlatıldı")

    # --- 3.6 Tüm kümeler kapalı → ValueError ---
    try:
        PasswordGenerator.generate(uppercase=False, lowercase=False,
                                   digits=False, special=False)
        fail("Tüm kümeler kapalı → ValueError beklendi")
    except ValueError:
        ok("Tüm kümeler kapalı → ValueError fırlatıldı")

    # --- 3.7 Sadece rakam ---
    pw_digits = PasswordGenerator.generate(
        length=20, uppercase=False, lowercase=False,
        digits=True, special=False)
    if pw_digits.isdigit() and len(pw_digits) == 20:
        ok("Sadece rakam: 20 haneli")
    else:
        fail("Sadece rakam", pw_digits)

    # --- 3.8 Uzun şifre (128 karakter) ---
    pw128 = PasswordGenerator.generate(length=128)
    if len(pw128) == 128:
        ok("128 karakter şifre üretildi")
    else:
        fail("128 karakter şifre", f"len={len(pw128)}")

    # --- 3.9 Entropi hesaplama ---
    entropy = PasswordGenerator.get_entropy("Abc1!")
    # pool: 26+26+10+32 = 94 → log2(94) * 5 ≈ 32.8
    expected = math.log2(94) * 5
    if abs(entropy - expected) < 0.01:
        ok(f"Entropi doğru: {entropy:.2f} bit")
    else:
        fail(f"Entropi", f"Beklenen: {expected:.2f}, Alınan: {entropy:.2f}")

    # --- 3.10 Boş şifre entropisi ---
    if PasswordGenerator.get_entropy("") == 0.0:
        ok("Boş şifre → entropi 0")
    else:
        fail("Boş şifre entropisi")

    # --- 3.11 calculate_strength dönüş formatı ---
    strength = PasswordGenerator.calculate_strength("Ab1!xYzW")
    required_keys = {"entropy", "score", "label", "color"}
    if required_keys.issubset(strength.keys()):
        ok(f"calculate_strength format doğru: {strength['label']} ({strength['score']})")
    else:
        fail("calculate_strength format", str(strength))

    # --- 3.12 Benzersizlik (1000 şifre üret, hepsi farklı mı?) ---
    passwords = set()
    for _ in range(1000):
        passwords.add(PasswordGenerator.generate(length=20))
    if len(passwords) == 1000:
        ok("1000 şifre üretildi, hepsi benzersiz")
    else:
        fail("Benzersizlik", f"{len(passwords)}/1000 benzersiz")


# ═══════════════════════════════════════════════════════════════
#  4. PasswordHealthAnalyzer testleri
# ═══════════════════════════════════════════════════════════════
def test_health():
    section("PasswordHealthAnalyzer")

    # --- 4.1 Boş liste → skor 100 ---
    report = PasswordHealthAnalyzer.get_report([])
    if report["score"] == 100 and report["total"] == 0:
        ok("Boş liste → skor 100")
    else:
        fail("Boş liste skoru", str(report["score"]))

    # --- 4.2 Güçlü şifreler → yüksek skor ---
    strong_entries = [
        {"id": f"s{i}", "site_name": f"site{i}", "username": f"u{i}",
         "password": PasswordGenerator.generate(length=24)}
        for i in range(10)
    ]
    report2 = PasswordHealthAnalyzer.get_report(strong_entries)
    if report2["score"] >= 70:
        ok(f"10 güçlü şifre → skor {report2['score']}")
    else:
        fail("Güçlü şifreler skoru", str(report2["score"]))

    # --- 4.3 Zayıf şifreler → düşük skor ---
    weak_entries = [
        {"id": f"w{i}", "site_name": f"site{i}", "username": f"u{i}",
         "password": "123"}
        for i in range(5)
    ]
    report3 = PasswordHealthAnalyzer.get_report(weak_entries)
    if report3["score"] < 30:
        ok(f"5 zayıf şifre → skor {report3['score']}")
    else:
        fail("Zayıf şifreler skoru", str(report3["score"]))

    # --- 4.4 Tekrar eden şifreler tespiti ---
    dup_entries = [
        {"id": "d1", "site_name": "A", "username": "u", "password": "SamePass123!"},
        {"id": "d2", "site_name": "B", "username": "u", "password": "SamePass123!"},
        {"id": "d3", "site_name": "C", "username": "u", "password": "DifferentPass!"},
    ]
    dups = PasswordHealthAnalyzer.find_duplicates(dup_entries)
    if len(dups) == 1 and len(dups[0]) == 2:
        ok("Tekrar eden şifre grubu doğru tespit edildi")
    else:
        fail("Tekrar tespiti", f"gruplar={len(dups)}")

    # --- 4.5 Tekrar eden → ceza uygulanıyor ---
    dup_report = PasswordHealthAnalyzer.get_report(dup_entries)
    no_dup_entries = [
        {"id": "d1", "site_name": "A", "username": "u", "password": "SamePass123!"},
        {"id": "d2", "site_name": "B", "username": "u", "password": "OtherPass456!"},
    ]
    no_dup_report = PasswordHealthAnalyzer.get_report(no_dup_entries)
    # Tekrarlı rapor, tekrarsız rapordan düşük skor vermeli
    if dup_report["score"] <= no_dup_report["score"]:
        ok(f"Tekrar cezası uygulanıyor ({dup_report['score']} ≤ {no_dup_report['score']})")
    else:
        fail("Tekrar cezası", f"{dup_report['score']} > {no_dup_report['score']}")

    # --- 4.6 Rapor anahtarları tam ---
    required_keys = {"score", "total", "analysis", "duplicates",
                     "weak_count", "medium_count", "strong_count"}
    if required_keys.issubset(report2.keys()):
        ok("Rapor anahtarları tam")
    else:
        fail("Rapor anahtarları", f"Eksik: {required_keys - report2.keys()}")


# ═══════════════════════════════════════════════════════════════
#  5. DataManager testleri
# ═══════════════════════════════════════════════════════════════
def test_data_manager():
    section("DataManager")

    tmpdir = tempfile.mkdtemp(prefix="dm_test_")
    try:
        dm = DataManager(tmpdir)

        # --- 5.1 İlk çalıştırma ---
        if dm.is_first_run():
            ok("İlk çalıştırma tespit edildi")
        else:
            fail("İlk çalıştırma tespiti")

        # --- 5.2 Master parola oluşturma ---
        dm.create_master_password("TestMaster1234!")
        if dm.is_authenticated:
            ok("Master parola oluşturuldu, authenticated")
        else:
            fail("Master parola oluşturma sonrası authenticated değil")

        # --- 5.3 vault.key ve vault.png oluşturuldu ---
        key_exists = os.path.exists(os.path.join(tmpdir, "vault.key"))
        img_exists = os.path.exists(os.path.join(tmpdir, "vault.png"))
        if key_exists and img_exists:
            ok("vault.key ve vault.png oluşturuldu")
        else:
            fail("Vault dosyaları", f"key={key_exists}, img={img_exists}")

        # --- 5.4 Şifre ekleme ---
        pwd_id = dm.add_password({
            "site_name": "Test Site",
            "username": "testuser",
            "password": "MySecret123!",
            "category": "Diğer",
        })
        if pwd_id and len(dm.get_passwords()) == 1:
            ok(f"Şifre eklendi (id={pwd_id[:8]}…)")
        else:
            fail("Şifre ekleme")

        # --- 5.5 add_password caller dict mutate etmiyor ---
        caller_dict = {"site_name": "X", "username": "Y",
                       "password": "Z", "category": "İş"}
        dm.add_password(caller_dict)
        if "id" not in caller_dict:
            ok("add_password caller dict'ini mutate etmiyor")
        else:
            fail("add_password mutation", f"caller_dict keys: {list(caller_dict.keys())}")

        # --- 5.6 Şifre güncelleme ---
        updated = dm.update_password(pwd_id, {
            "site_name": "Updated Site",
            "password": "NewSecret456!",
        })
        pwd = dm.get_password(pwd_id)
        if updated and pwd["site_name"] == "Updated Site":
            ok("Şifre güncellendi")
        else:
            fail("Şifre güncelleme")

        # --- 5.7 update korunaklı alanları değiştiremiyor ---
        orig_created = pwd["created_at"]
        dm.update_password(pwd_id, {"id": "HACKED", "created_at": "TAMPERED"})
        pwd2 = dm.get_password(pwd_id)
        if pwd2["id"] == pwd_id and pwd2["created_at"] == orig_created:
            ok("Korunaklı alanlar (id, created_at) değişmedi")
        else:
            fail("Korunaklı alan ihlali",
                 f"id={pwd2['id']}, created_at={pwd2['created_at']}")

        # --- 5.8 Arama ---
        results = dm.search_passwords("updated")
        if len(results) == 1:
            ok("Arama çalışıyor")
        else:
            fail("Arama", f"Sonuç: {len(results)}")

        # --- 5.9 Kategori filtresi ---
        results_cat = dm.search_passwords(category="İş")
        if len(results_cat) == 1:
            ok("Kategori filtresi çalışıyor")
        else:
            fail("Kategori filtresi", f"Sonuç: {len(results_cat)}")

        # --- 5.10 Şifre silme ---
        deleted = dm.delete_password(pwd_id)
        if deleted and dm.get_password(pwd_id) is None:
            ok("Şifre silindi")
        else:
            fail("Şifre silme")

        # --- 5.11 Var olmayan kayıt silme → False ---
        if not dm.delete_password("nonexistent_id"):
            ok("Var olmayan kayıt silme → False")
        else:
            fail("Var olmayan kayıt silme")

        # --- 5.12 Not ekleme ---
        note_id = dm.add_note({"title": "Test Not", "content": "İçerik…"})
        if note_id and len(dm.get_notes()) == 1:
            ok(f"Not eklendi (id={note_id[:8]}…)")
        else:
            fail("Not ekleme")

        # --- 5.13 add_note caller dict mutate etmiyor ---
        note_dict = {"title": "A", "content": "B"}
        dm.add_note(note_dict)
        if "id" not in note_dict:
            ok("add_note caller dict'ini mutate etmiyor")
        else:
            fail("add_note mutation")

        # --- 5.14 Not güncelleme ---
        dm.update_note(note_id, {"title": "Güncel Not"})
        note = dm.get_note(note_id)
        if note["title"] == "Güncel Not":
            ok("Not güncellendi")
        else:
            fail("Not güncelleme")

        # --- 5.15 Not silme ---
        dm.delete_note(note_id)
        if dm.get_note(note_id) is None:
            ok("Not silindi")
        else:
            fail("Not silme")

        # --- 5.16 Tema kaydetme/yükleme ---
        dm.set_theme("light")
        if dm.get_theme() == "light":
            ok("Tema kaydedildi (light)")
        else:
            fail("Tema kaydetme")

        # --- 5.17 Lock → key temizleniyor ---
        dm.lock()
        if not dm.is_authenticated:
            ok("Lock sonrası authenticated değil")
        else:
            fail("Lock sonrası durum")

        # --- 5.18 Tekrar kimlik doğrulama ---
        if dm.authenticate("TestMaster1234!"):
            ok("Tekrar authenticate başarılı")
        else:
            fail("Tekrar authenticate")

        # --- 5.19 Tema persist etti mi? ---
        if dm.get_theme() == "light":
            ok("Tema persist etti (light)")
        else:
            fail("Tema persistence", dm.get_theme())

        # --- 5.20 Yanlış parola ile authenticate → False ---
        dm2 = DataManager(tmpdir)
        if not dm2.authenticate("YanlisParola"):
            ok("Yanlış parola → False")
        else:
            fail("Yanlış parola testi")

        # --- 5.21 Özel kategori ekleme ---
        dm.add_custom_category("VPN")
        cats = dm.get_all_categories()
        if "VPN" in cats:
            ok("Özel kategori eklendi (VPN)")
        else:
            fail("Özel kategori", str(cats))

        # --- 5.22 Aynı kategori tekrar eklenemez ---
        before_len = len(dm.get_all_categories())
        dm.add_custom_category("VPN")
        after_len = len(dm.get_all_categories())
        if before_len == after_len:
            ok("Aynı kategori tekrar eklenemez")
        else:
            fail("Kategori tekrar engeli")

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════
#  6. Performans testleri
# ═══════════════════════════════════════════════════════════════
def test_performance():
    section("Performans")

    # --- 6.1 1000 şifre üretme süresi ---
    t0 = time.perf_counter()
    for _ in range(1000):
        PasswordGenerator.generate(length=20)
    dt = time.perf_counter() - t0
    if dt < 5.0:
        ok(f"1000 şifre üretimi: {dt:.3f}s")
    else:
        fail(f"1000 şifre üretimi çok yavaş: {dt:.3f}s")

    # --- 6.2 1000 kayıt sağlık raporu süresi ---
    entries = [
        {"id": f"p{i}", "site_name": f"site{i}", "username": f"u{i}",
         "password": PasswordGenerator.generate(length=16)}
        for i in range(1000)
    ]
    t0 = time.perf_counter()
    report = PasswordHealthAnalyzer.get_report(entries)
    dt = time.perf_counter() - t0
    if dt < 2.0:
        ok(f"1000 kayıt sağlık raporu: {dt:.3f}s (skor={report['score']})")
    else:
        fail(f"1000 kayıt sağlık raporu çok yavaş: {dt:.3f}s")

    # --- 6.3 Steganografi encode/decode süresi (100 KB veri) ---
    tmpdir = tempfile.mkdtemp(prefix="perf_test_")
    try:
        img = os.path.join(tmpdir, "perf.png")
        SteganographyManager.create_carrier_image(img, 1024, 1024)
        data = secrets.token_bytes(100_000)  # 100 KB

        t0 = time.perf_counter()
        SteganographyManager.encode(img, data)
        encode_dt = time.perf_counter() - t0

        t0 = time.perf_counter()
        decoded = SteganographyManager.decode(img)
        decode_dt = time.perf_counter() - t0

        if decoded == data and encode_dt < 30 and decode_dt < 30:
            ok(f"100 KB steganografi: encode={encode_dt:.2f}s, decode={decode_dt:.2f}s")
        else:
            fail(f"Steganografi performans",
                 f"encode={encode_dt:.2f}s, decode={decode_dt:.2f}s, eşleşme={decoded == data}")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    # --- 6.4 AES-256 encrypt/decrypt süresi (1 MB) ---
    key = secrets.token_bytes(32)
    big_data = secrets.token_bytes(1_000_000)

    t0 = time.perf_counter()
    enc = CryptoManager.encrypt(big_data, key)
    enc_dt = time.perf_counter() - t0

    t0 = time.perf_counter()
    dec = CryptoManager.decrypt(enc, key)
    dec_dt = time.perf_counter() - t0

    if dec == big_data and enc_dt < 1.0 and dec_dt < 1.0:
        ok(f"1 MB AES-256-GCM: encrypt={enc_dt*1000:.1f}ms, decrypt={dec_dt*1000:.1f}ms")
    else:
        fail(f"AES performans", f"encrypt={enc_dt:.3f}s, decrypt={dec_dt:.3f}s")


# ═══════════════════════════════════════════════════════════════
#  7. Entegrasyon testi (tam akış)
# ═══════════════════════════════════════════════════════════════
def test_integration():
    section("Entegrasyon (Tam Akış)")

    tmpdir = tempfile.mkdtemp(prefix="integ_test_")
    try:
        # 1) Vault oluştur
        dm = DataManager(tmpdir)
        dm.create_master_password("Integration$Test#2024")
        ok("Vault oluşturuldu")

        # 2) 50 şifre ekle
        ids = []
        for i in range(50):
            pw = PasswordGenerator.generate(length=20)
            pid = dm.add_password({
                "site_name": f"Site #{i+1}",
                "username": f"user{i}@example.com",
                "password": pw,
                "category": ["Sosyal Medya", "Banka", "E-posta", "İş"][i % 4],
                "notes": f"Not #{i+1}",
            })
            ids.append(pid)
        if len(dm.get_passwords()) == 50:
            ok("50 şifre eklendi")
        else:
            fail("50 şifre ekleme", f"{len(dm.get_passwords())} kayıt")

        # 3) 10 not ekle
        for i in range(10):
            dm.add_note({"title": f"Not {i+1}", "content": f"İçerik {i+1}" * 50})
        if len(dm.get_notes()) == 10:
            ok("10 not eklendi")
        else:
            fail("10 not ekleme")

        # 4) Kilitle ve tekrar aç
        dm.lock()
        if dm.authenticate("Integration$Test#2024"):
            ok("Kilitle → tekrar authenticate")
        else:
            fail("Kilitle → tekrar authenticate")

        # 5) Veriler persist etti mi?
        if len(dm.get_passwords()) == 50 and len(dm.get_notes()) == 10:
            ok("Veri persistence doğrulandı (50 şifre + 10 not)")
        else:
            fail("Veri persistence",
                 f"passwords={len(dm.get_passwords())}, notes={len(dm.get_notes())}")

        # 6) Sağlık raporu
        report = PasswordHealthAnalyzer.get_report(dm.get_passwords())
        if report["total"] == 50 and report["score"] >= 0:
            ok(f"Sağlık raporu: skor={report['score']}, "
               f"güçlü={report['strong_count']}, "
               f"orta={report['medium_count']}, "
               f"zayıf={report['weak_count']}")
        else:
            fail("Sağlık raporu")

        # 7) Arama + filtre
        banka = dm.search_passwords(category="Banka")
        if len(banka) > 0:
            ok(f"Banka kategorisi: {len(banka)} kayıt")
        else:
            fail("Kategori araması")

        text_search = dm.search_passwords(query="Site #1")
        if len(text_search) >= 1:
            ok(f"Metin araması 'Site #1': {len(text_search)} sonuç")
        else:
            fail("Metin araması")

        # 8) Silme sonrası sayı
        dm.delete_password(ids[0])
        if len(dm.get_passwords()) == 49:
            ok("Silme sonrası: 49 kayıt")
        else:
            fail("Silme sonrası sayı")

        # 9) Tamamen yeni DataManager ile doğrulama
        dm2 = DataManager(tmpdir)
        dm2.authenticate("Integration$Test#2024")
        if len(dm2.get_passwords()) == 49 and len(dm2.get_notes()) == 10:
            ok("Ayrı DataManager instance ile veri doğrulandı")
        else:
            fail("Ayrı instance doğrulama")

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════
#  ÇALIŞTIR
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print(f"\n{'='*60}")
    print(f"  SecureVault — Kapsamlı Test Paketi")
    print(f"{'='*60}")

    test_crypto()
    test_steganography()
    test_generator()
    test_health()
    test_data_manager()
    test_performance()
    test_integration()

    section("SONUÇ")
    total = passed + failed
    print(f"  Toplam: {total}  |  Başarılı: {passed}  |  Başarısız: {failed}")
    if errors:
        print(f"\n  Hatalar:")
        for e in errors:
            print(f"  {e}")
    print()

    sys.exit(0 if failed == 0 else 1)
