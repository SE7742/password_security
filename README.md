# SecureVault

[![Website](https://img.shields.io/badge/Website-Ziyaret_Et-blue?style=for-the-badge&logo=github)](https://SE7742.github.io/password_security/)
[![Download](https://img.shields.io/badge/Download-SecureVault.exe-green?style=for-the-badge&logo=windows)](https://github.com/SE7742/password_security/releases/latest/download/SecureVault.exe)

**Güvenli, Çevrimdışı ve Şifreli Parola Yöneticisi.**

SecureVault, verilerinizi AES-256-GCM ile şifreleyen ve steganografi kullanarak bir görüntü dosyası içine gizleyen, tamamen yerel çalışan bir şifre yöneticisidir. Hiçbir sunucuya veri göndermez.

## 🚀 İndir ve Kullan

En son sürümü **Releases** sayfasından indirebilirsiniz:
👉 **[SecureVault.exe İndir](https://github.com/SE7742/password_security/releases/latest)**

1. İndirin ve çalıştırın (Kurulum gerektirmez)
2. Master parolanızı belirleyin
3. Şifrelerinizi güvenle saklayın

> **Not:** Windows SmartScreen uyarısı alırsanız "Yine de çalıştır" diyerek devam edebilirsiniz. Bu uyarı imzalanmamış açık kaynak yazılımlar için normaldir.

## 🛠️ Kendin Derle (Build from Source)

Güvenlik konusunda hassassanız, kendi EXE dosyanızı kaynak koddan üretebilirsiniz:

1. **Python 3.10+** yükleyin
2. Bağımlılıkları kurun:
   ```bash
   pip install -r requirements.txt
   pip install pyinstaller
   ```
3. Derleyin:
   ```bash
   pyinstaller --onefile --noconsole --name SecureVault main.py
   ```
4. `dist/SecureVault.exe` dosyasını kullanın.

## ✨ Özellikler

- 🔒 **AES-256-GCM Sifreleme** — Endüstri standardı koruma
- 🖼️ **Steganografi** — Veriler `vault.png` görselinin içine gizlenir
- 🔑 **PBKDF2 Anahtar Türetme** — 600.000 iterasyon
- 🎲 **Güvenli Şifre Üretici** — Kriptografik rastgele şifreler
- 📝 **Not Defteri** — Şifreli not saklama
- 📊 **Sağlık Raporu** — Şifre gücü analizi
- 🌑 **Modern Arayüz** — Karanlık mod ve kullanıcı dostu tasarım

## 📂 Dosya Yapısı

Verileriniz sadece iki dosyada saklanır:
- `vault.png`: Şifrelenmiş verileriniz (bu dosyayı yedekleyin)
- `vault.key`: Kendi oluşturduğunuz anahtar dosyanız

Bu iki dosya application dizininde oluşur. Başka bir bilgisayara geçmek için EXE ile birlikte bu iki dosyayı taşımanız yeterlidir.

## ⚠️ Güvenlik Uyarısı

- Master parolanızı **asla unutmayın**. Kurtarma seçeneği yoktur.
- `vault.key` ve `vault.png` dosyalarını başkalarıyla paylaşmayın.

## 📜 Lisans

M. Taha Doğan tarafından geliştirilmiştir.
MIT License.

