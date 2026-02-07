# SecureVault

Tamamen yerel calisan, AES-256-GCM sifreleme ve LSB steganografi korumalı sifre yoneticisi.

## Ozellikler

- **AES-256-GCM Sifreleme** — Endustri standardi authenticated encryption
- **LSB Steganografi** — Tum veriler bir PNG goruntusunun piksellerine gizlenir
- **PBKDF2 Anahtar Turetme** — 600.000 iterasyon ile brute-force koruması
- **Rastgele Sifre Ureteci** — `secrets` modulu ile kriptografik guvenli uretim
- **Sifre Kasasi** — Ekleme, duzenleme, silme, kategoriler, arama ve filtreleme
- **Guvenli Not Defteri** — AES-256 ile sifrelenmis notlar
- **Sifre Saglik Raporu** — Guc analizi, tekrar eden sifre tespiti, 0-100 skor
- **Master Parola Degistirme** — Mevcut verileri koruyarak parola yenileme
- **Koyu/Acik Tema** — Catppuccin temali modern arayuz
- **Sistem Tepsisi** — Arka planda calisma destegi
- **Pano Guvenligi** — Kopyalanan sifreler 30 saniye sonra otomatik temizlenir

## Kurulum

### Gereksinimler

- Python 3.10+
- Windows 10/11

### Bagimliliklari yukleyin

```bash
pip install -r requirements.txt
```

### Uygulamayi baslatin

```bash
python main.py
```

### EXE olusturma (opsiyonel)

```bash
pip install pyinstaller
python -m PyInstaller --onefile --windowed --name SecureVault main.py
```

Cikti: `dist/SecureVault.exe`

## Kullanim

### Ilk Calistirma

1. Uygulama acildiginda bir **master parola** belirleyin (en az 8 karakter).
2. Paralolayi tekrar girerek onaylayin.
3. Vault otomatik olusturulur (`vault.key` + `vault.png`).

### Giris

Master parolanizi girerek vault'a erisin.

### Sifre Ureteci

- Uzunluk (8-128 karakter) ve karakter turlerini secin.
- **Sifre Uret** ile uretin, **Panoya Kopyala** veya **Kasaya Kaydet** ile kullanin.

### Sifre Kasasi

- **Ekle:** Site adi, kullanici, sifre, kategori ve not girin.
- **Duzenleme:** Listeden kayit secin, degistirin, **Guncelle**.
- **Silme:** Kayit secin, **Sil**, onayla.
- **Arama/Filtreleme:** Ust cubuktan arama veya kategori filtresi.

### Not Defteri

- Sol panelde not listesi, sagda duzenleyici.
- **Yeni** ile olusturun, **Kaydet** ile kaydedin.

### Saglik Raporu

- Tum sifrelerin guc analizi ve 0-100 genel guvenlik skoru.
- Zayif ve tekrar eden sifreleri tespit eder.

### Parola Degistirme

- Ust cubuktaki **Parola Degistir** butonu ile master paralanizi degistirebilirsiniz.
- Mevcut tum veriler yeni anahtarla yeniden sifrelenir.

## Guvenlik Mimarisi

```
Kaydetme:
  JSON → AES-256-GCM Sifreleme → Base64 → LSB Steganografi → vault.png

Yukleme:
  vault.png → LSB Cikarma → Base64 Cozme → AES-256-GCM Cozme → JSON
```

| Katman | Detay |
|--------|-------|
| Anahtar Turetme | PBKDF2-HMAC-SHA256, 600.000 iterasyon, 32-byte salt |
| Sifreleme | AES-256-GCM, 12-byte nonce, authenticated encryption |
| Veri Gizleme | LSB steganografi, SHA-256 checksum |
| Pano | 30 saniye sonra otomatik temizleme |

## Dosya Yapisi

```
sifre_guvenlık/
├── main.py
├── requirements.txt
├── test_all.py
├── README.md
├── .gitignore
└── securevault/
    ├── __init__.py
    ├── constants.py        # Sabitler, temalar, kategoriler
    ├── crypto.py           # AES-256-GCM + PBKDF2
    ├── steganography.py    # LSB steganografi
    ├── generator.py        # Guvenli sifre uretimi
    ├── health.py           # Sifre guc analizi
    ├── data_manager.py     # CRUD + sifreleme
    └── app.py              # Tkinter GUI
```

Calisma zamaninda olusturulan dosyalar:

| Dosya | Aciklama |
|-------|----------|
| `vault.key` | Master parola hash'i ve salt |
| `vault.png` | Sifrelenmis verilerin gizlendigi goruntu |

> **Uyari:** `vault.key` ve `vault.png` dosyalarini asla paylasmayın. Bu dosyalar `.gitignore` ile korunmaktadir.

## Klavye Kisayollari

| Kisayol | Islev |
|---------|-------|
| `Ctrl+L` | Uygulamayi kilitle |
| `Enter` | Giris ekraninda parola gonder |

## Testler

```bash
pip install pytest
python -m pytest test_all.py -v
```

## Lisans

Bu proje kisisel kullanim icin gelistirilmistir.
