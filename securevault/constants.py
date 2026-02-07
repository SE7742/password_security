"""Uygulama sabitleri: temalar, varsayılan kategoriler, genel ayarlar."""

APP_NAME = "SecureVault"
APP_TITLE = "SecureVault - Güvenli Şifre Yöneticisi"
VERSION = "1.0.0"

DEFAULT_CATEGORIES: list[str] = [
    "Sosyal Medya",
    "Banka",
    "E-posta",
    "Alışveriş",
    "Oyun",
    "İş",
    "Diğer",
]

THEMES: dict[str, dict[str, str]] = {
    "dark": {
        "bg": "#1e1e2e",
        "fg": "#cdd6f4",
        "accent": "#89b4fa",
        "accent_fg": "#1e1e2e",
        "entry_bg": "#313244",
        "entry_fg": "#cdd6f4",
        "button_bg": "#45475a",
        "button_fg": "#cdd6f4",
        "button_active": "#585b70",
        "success": "#a6e3a1",
        "warning": "#f9e2af",
        "error": "#f38ba8",
        "header_bg": "#181825",
        "select_bg": "#45475a",
        "select_fg": "#cdd6f4",
        "border": "#585b70",
        "muted": "#6c7086",
    },
    "light": {
        "bg": "#eff1f5",
        "fg": "#4c4f69",
        "accent": "#1e66f5",
        "accent_fg": "#ffffff",
        "entry_bg": "#ffffff",
        "entry_fg": "#4c4f69",
        "button_bg": "#ccd0da",
        "button_fg": "#4c4f69",
        "button_active": "#bcc0cc",
        "success": "#40a02b",
        "warning": "#df8e1d",
        "error": "#d20f39",
        "header_bg": "#dce0e8",
        "select_bg": "#ccd0da",
        "select_fg": "#4c4f69",
        "border": "#9ca0b0",
        "muted": "#8c8fa1",
    },
}

FONT_FAMILY = "Segoe UI"
