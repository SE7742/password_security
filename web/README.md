# SecureVault Web — İndirme Portalı

SecureVault uygulamasının indirme ve tanıtım web sitesi.
**Sadece EXE dosyası indirilir, kaynak kod asla açığa çıkmaz.**

## Kurulum

```bash
cd web
pip install -r requirements.txt
```

## Kullanım

### Geliştirme
```bash
python app.py
```
Tarayıcıda `http://localhost:5000` adresine gidin.

### Production (Gunicorn)
```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

## EXE Dosyası Yerleştirme

`SecureVault.exe` dosyasını `web/downloads/` klasörüne koyun:

```
web/
  downloads/
    SecureVault.exe   ← buraya koyun
```

## Güvenlik Özellikleri

- **CSP Headers** — Content Security Policy ile XSS koruması
- **Rate Limiting** — Saatte 10 indirme limiti (DDoS koruması)
- **Path Traversal Koruması** — Sadece izin verilen dosyalar indirilebilir
- **Kaynak Kod Engelleme** — `.py`, `.git`, `.env` dosyalarına erişim engelli
- **SHA-256 Doğrulama** — İndirilen dosyanın bütünlük kontrolü
- **Secure Cookies** — HttpOnly, SameSite cookie'ler

## Ortam Değişkenleri

| Değişken | Açıklama | Varsayılan |
|----------|----------|------------|
| `FLASK_SECRET_KEY` | Session şifreleme anahtarı | Rastgele üretilir |
