"""SecureVault Web — İndirme portalı ve tanıtım sayfası.

Sadece EXE dosyası indirilir, kaynak kod asla açığa çıkmaz.
"""

import os
import hashlib
import json
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, send_from_directory, abort,
    request, jsonify, redirect, url_for,
)
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# ---------------------------------------------------------------------------
# Uygulama yapılandırması
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(32).hex())

# Güvenli dosya indirme dizini (sadece EXE ve izin verilen dosyalar)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")

# İndirme sayacı dosyası
STATS_FILE = os.path.join(BASE_DIR, "stats.json")

# İzin verilen indirme dosyaları — SADECE bunlar indirilebilir
ALLOWED_FILES = {
    "SecureVault.exe",
}

# ---------------------------------------------------------------------------
# Ortam: yerel (localhost) vs production (sunucu)
# ---------------------------------------------------------------------------
def _is_production() -> bool:
    """Production ortamında mı çalışıyoruz? HTTPS ve sıkı güvenlik kullanılır."""
    return os.environ.get("FLASK_ENV") == "production" or os.environ.get("PRODUCTION", "").lower() in ("1", "true", "yes")


# ---------------------------------------------------------------------------
# Güvenlik middleware'leri (production'da sıkı, yerelde tamamen devre dışı)
# ---------------------------------------------------------------------------
if _is_production():
    csp = {
        "default-src": "'self'",
        "script-src": ["'self'", "https://cdn.tailwindcss.com", "'unsafe-inline'"],
        "style-src": ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com", "https://cdn.tailwindcss.com"],
        "font-src": ["'self'", "https://fonts.gstatic.com"],
        "img-src": ["'self'", "data:"],
        "connect-src": "'self'",
    }
    talisman = Talisman(
        app,
        content_security_policy=csp,
        force_https=True,
        session_cookie_secure=True,
        session_cookie_http_only=True,
        session_cookie_samesite="Lax",
    )

# Rate limiting — brute force ve DDoS koruması
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)


# ---------------------------------------------------------------------------
# İndirme istatistikleri
# ---------------------------------------------------------------------------
def _load_stats() -> dict:
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"total_downloads": 0, "daily": {}}


def _save_stats(stats: dict) -> None:
    try:
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False)
    except OSError:
        pass


def _increment_download() -> int:
    stats = _load_stats()
    stats["total_downloads"] = stats.get("total_downloads", 0) + 1
    today = datetime.now().strftime("%Y-%m-%d")
    daily = stats.setdefault("daily", {})
    daily[today] = daily.get(today, 0) + 1
    _save_stats(stats)
    return stats["total_downloads"]


# ---------------------------------------------------------------------------
# Dosya güvenlik kontrolü
# ---------------------------------------------------------------------------
def _get_file_hash(filepath: str) -> str:
    """Dosyanın SHA-256 hash'ini döndürür."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _get_file_size(filepath: str) -> str:
    """Okunabilir dosya boyutu döndürür."""
    size = os.path.getsize(filepath)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


# ---------------------------------------------------------------------------
# Rotalar
# ---------------------------------------------------------------------------
def _request_is_local() -> bool:
    """İstek yerel (localhost) mi geliyor?"""
    from flask import request
    h = request.environ.get("HTTP_HOST", "") or request.host or ""
    return h.startswith("127.0.0.1") or h.startswith("localhost") or "::1" in h


@app.route("/")
def index():
    """Ana sayfa — tanıtım ve indirme."""
    stats = _load_stats()
    exe_path = os.path.join(DOWNLOADS_DIR, "SecureVault.exe")
    file_info = {}
    if os.path.exists(exe_path):
        full_hash = _get_file_hash(exe_path)
        file_info = {
            "exists": True,
            "size": _get_file_size(exe_path),
            "sha256_short": full_hash[:16] + "...",
            "full_sha256": full_hash,
        }
    else:
        file_info = {"exists": False}

    return render_template(
        "index.html",
        total_downloads=stats.get("total_downloads", 0),
        file_info=file_info,
        version="1.0.0",
        is_local=not _is_production() and _request_is_local(),
        is_production=_is_production(),
    )


@app.route("/dogrulama")
def verification():
    """SHA-256 doğrulama sayfası — tam hash ve Windows doğrulama komutu."""
    exe_path = os.path.join(DOWNLOADS_DIR, "SecureVault.exe")
    if not os.path.exists(exe_path):
        return render_template(
            "dogrulama.html",
            exists=False,
            version="1.0.0",
            is_local=not _is_production() and _request_is_local(),
        )
    full_sha256 = _get_file_hash(exe_path)
    return render_template(
        "dogrulama.html",
        exists=True,
        version="1.0.0",
        filename="SecureVault.exe",
        full_sha256=full_sha256,
        size=_get_file_size(exe_path),
        is_local=not _is_production() and _request_is_local(),
    )


@app.route("/download/<filename>")
@limiter.limit("10 per hour")
def download_file(filename: str):
    """Güvenli dosya indirme — sadece izin verilen dosyalar."""
    # Güvenlik: Path traversal koruması
    safe_name = os.path.basename(filename)

    if safe_name not in ALLOWED_FILES:
        abort(403, description="Bu dosyayı indirme yetkiniz yok.")

    filepath = os.path.join(DOWNLOADS_DIR, safe_name)
    if not os.path.exists(filepath):
        abort(404, description="Dosya bulunamadı.")

    # Dosyanın gerçekten DOWNLOADS_DIR içinde olduğunu doğrula
    real_path = os.path.realpath(filepath)
    real_downloads = os.path.realpath(DOWNLOADS_DIR)
    if not real_path.startswith(real_downloads):
        abort(403, description="Geçersiz dosya yolu.")

    _increment_download()

    return send_from_directory(
        DOWNLOADS_DIR,
        safe_name,
        as_attachment=True,
        download_name=safe_name,
    )


@app.route("/api/stats")
def api_stats():
    """İndirme istatistikleri API'si."""
    stats = _load_stats()
    return jsonify({
        "total_downloads": stats.get("total_downloads", 0),
    })


@app.route("/api/verify/<filename>")
def api_verify(filename: str):
    """Dosya bütünlük doğrulama API'si."""
    safe_name = os.path.basename(filename)
    if safe_name not in ALLOWED_FILES:
        abort(403)

    filepath = os.path.join(DOWNLOADS_DIR, safe_name)
    if not os.path.exists(filepath):
        abort(404)

    return jsonify({
        "filename": safe_name,
        "sha256": _get_file_hash(filepath),
        "size": _get_file_size(filepath),
    })


@app.route("/favicon.ico")
def favicon():
    """Favicon 404 hatasını önlemek için boş yanıt."""
    from flask import Response
    return Response(status=204)


# Kaynak kodu rotalarını tamamen engelle
@app.route("/securevault/<path:path>")
@app.route("/securevault")
@app.route("/.git/<path:path>")
@app.route("/.git")
@app.route("/.env")
@app.route("/main.py")
@app.route("/test_all.py")
@app.route("/<path:path>.py")
def block_source(path=""):
    """Kaynak kod dosyalarına erişimi engelle."""
    abort(403, description="Erişim engellendi.")


# ---------------------------------------------------------------------------
# Hata sayfaları
# ---------------------------------------------------------------------------
@app.errorhandler(403)
def forbidden(e):
    return render_template("error.html", code=403,
                           message="Erişim Engellendi",
                           detail=str(e.description)), 403


@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", code=404,
                           message="Sayfa Bulunamadı",
                           detail="Aradığınız sayfa mevcut değil."), 404


@app.errorhandler(429)
def rate_limited(e):
    return render_template("error.html", code=429,
                           message="Çok Fazla İstek",
                           detail="Lütfen bir süre bekleyip tekrar deneyin."), 429


# ---------------------------------------------------------------------------
# Çalıştırma
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Downloads dizinini oluştur
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  SecureVault İndirme Portalı")
    print(f"  İndirme dizini: {DOWNLOADS_DIR}")
    print(f"  SecureVault.exe dosyasını 'downloads/' klasörüne koyun")
    print(f"{'='*60}\n")

    app.run(host="0.0.0.0", port=5000, debug=True)
