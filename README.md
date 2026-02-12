# SecureVault

**Güvenli, çevrimdışı ve şifreli parola yöneticisi.**

Bu proje **Sidar Doğan** tarafından geliştirilmiştir.

**Proje klasörü:** Mümkünse ASCII isim kullanın (örn. `sifre_guvenlik` veya `SecureVault`). Türkçe **ı/ş/ğ/ü** bazı ortamlarda sorun çıkarır. Eski `şifre_güvenlik` klasörünü yeniden adlandırmak için proje kökünde `python rename_folders.py` çalıştırabilirsiniz (klasör açık değilken).

SecureVault, verilerinizi AES-256-GCM ile şifreleyen ve steganografi kullanarak bir görüntü dosyası içine gizleyen, tamamen yerel çalışan bir şifre yöneticisidir. Hiçbir sunucuya veri göndermez.

---

## İndir

**Windows için hazır EXE:**

👉 **[SecureVault.exe indir](releases/SecureVault.exe)**

1. Yukarıdaki bağlantıdan veya bu depodaki `releases` klasöründen `SecureVault.exe` dosyasını indirin.
2. Çalıştırın (kurulum yok).
3. Master parolanızı belirleyin ve şifrelerinizi güvenle saklayın.

> **Not:** Windows SmartScreen uyarısı çıkarsa "Yine de çalıştır" ile devam edebilirsiniz. İmzalanmamış açık kaynak yazılımlar için normaldir.

---

## Özellikler

- **AES-256-GCM şifreleme** — Endüstri standardı koruma
- **Steganografi** — Veriler `vault.png` görselinin içine gizlenir
- **PBKDF2 anahtar türetme** — 600.000 iterasyon
- **Güvenli şifre üretici** — Kriptografik rastgele şifreler
- **Not defteri** — Şifreli not saklama
- **Sağlık raporu** — Şifre gücü ve tekrar analizi
- **Modern arayüz** — Karanlık mod, sistem tepsisi

---

## Dosya yapısı (verileriniz)

Verileriniz yalnızca iki dosyada tutulur:

| Dosya     | Açıklama |
|----------|----------|
| `vault.png` | Şifrelenmiş verileriniz (yedekleyin) |
| `vault.key` | Anahtar dosyası (EXE ile aynı klasörde oluşur) |

Başka bir bilgisayara geçmek için EXE ile birlikte bu iki dosyayı kopyalamanız yeterlidir.

---

## Kendin derle (isteğe bağlı)

Kendi EXE dosyanızı kaynak koddan üretmek isterseniz:

1. **Python 3.10+** yükleyin.
2. Bağımlılıkları kurun:
   ```bash
   pip install -r requirements.txt
   pip install pyinstaller
   ```
3. **releases/** için (EXE içinde geliştirme ortamı yolu olmasın):
   ```bash
   python build_release.py
   ```
   Bu script projeyi geçici bir dizine kopyalayıp orada derler; üretilen EXE `releases/SecureVault.exe` olur.
4. Veya doğrudan:
   ```bash
   pyinstaller --onefile --noconsole --name SecureVault main.py
   ```
   Sonra `dist/SecureVault.exe` dosyasını `releases/` içine kopyalayın.

---

## Güvenlik

- Master parolanızı **asla unutmayın**. Kurtarma seçeneği yoktur.
- `vault.key` ve `vault.png` dosyalarını kimseyle paylaşmayın.

---

## Lisans

**Sıdar Doğan** — MIT License.
