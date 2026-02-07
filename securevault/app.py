"""Tkinter GUI — login, sekmeli arayüz, koyu/açık tema, sistem tepsisi."""

import os
import sys
import threading
from typing import Optional

import tkinter as tk
from tkinter import ttk, messagebox

from PIL import Image, ImageDraw

try:
    import pystray
    from pystray import MenuItem

    HAS_PYSTRAY = True
except ImportError:
    HAS_PYSTRAY = False

from securevault.constants import (
    APP_NAME,
    APP_TITLE,
    DEFAULT_CATEGORIES,
    FONT_FAMILY,
    THEMES,
)
from securevault.data_manager import DataManager
from securevault.generator import PasswordGenerator
from securevault.health import PasswordHealthAnalyzer


class App:
    """Ana uygulama sınıfı — GUI, tema, sistem tepsisi."""

    def __init__(self) -> None:
        self.root = tk.Tk()
        self._base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        self._data_mgr: Optional[DataManager] = None
        self._pass_gen = PasswordGenerator()
        self._health = PasswordHealthAnalyzer()
        self._current_theme = "dark"
        self._clipboard_timer: Optional[threading.Timer] = None
        self._tray = None
        self._tray_running = False
        self._selected_pwd_id: Optional[str] = None
        self._selected_note_id: Optional[str] = None
        self._notebook: Optional[ttk.Notebook] = None

        self._setup_window()

    # ==================================================================
    #  Pencere kurulumu
    # ==================================================================
    def _setup_window(self) -> None:
        self.root.title(APP_TITLE)
        self.root.geometry("960x700")
        self.root.minsize(820, 620)
        self.root.configure(bg=THEMES[self._current_theme]["bg"])
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f"+{x}+{y}")

    def run(self) -> None:
        """Uygulamayı başlatır."""
        self._data_mgr = DataManager(self._base_dir)
        self._show_login()
        self.root.mainloop()

    # ==================================================================
    #  Tema
    # ==================================================================
    @property
    def theme(self) -> dict:
        return THEMES[self._current_theme]

    def _apply_ttk_styles(self) -> None:
        t = self.theme
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(".", background=t["bg"], foreground=t["fg"],
                         font=(FONT_FAMILY, 10))

        style.configure("TNotebook", background=t["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=t["button_bg"],
                         foreground=t["fg"], padding=[14, 6],
                         font=(FONT_FAMILY, 10, "bold"))
        style.map("TNotebook.Tab",
                   background=[("selected", t["bg"])],
                   foreground=[("selected", t["accent"])])

        style.configure("Treeview", background=t["entry_bg"],
                         foreground=t["fg"], fieldbackground=t["entry_bg"],
                         rowheight=30, font=(FONT_FAMILY, 10))
        style.configure("Treeview.Heading", background=t["header_bg"],
                         foreground=t["fg"], font=(FONT_FAMILY, 9, "bold"))
        style.map("Treeview",
                   background=[("selected", t["select_bg"])],
                   foreground=[("selected", t["select_fg"])])

        style.configure("TCombobox", fieldbackground=t["entry_bg"],
                         background=t["button_bg"], foreground=t["entry_fg"],
                         arrowcolor=t["fg"])
        style.map("TCombobox", fieldbackground=[("readonly", t["entry_bg"])])

        style.configure("TScale", background=t["bg"], troughcolor=t["entry_bg"])
        style.configure("TScrollbar", background=t["button_bg"],
                         troughcolor=t["entry_bg"], arrowcolor=t["fg"])
        style.configure("TCheckbutton", background=t["bg"], foreground=t["fg"],
                         font=(FONT_FAMILY, 10))
        style.map("TCheckbutton", background=[("active", t["bg"])])

    def _toggle_theme(self) -> None:
        tab_idx = 0
        if self._notebook:
            try:
                tab_idx = self._notebook.index(self._notebook.select())
            except Exception:
                tab_idx = 0

        self._current_theme = "light" if self._current_theme == "dark" else "dark"
        if self._data_mgr:
            self._data_mgr.set_theme(self._current_theme)
        self._show_main(restore_tab=tab_idx)

    # ==================================================================
    #  Yardımcı widget oluşturucular
    # ==================================================================
    def _make_frame(self, parent, **kw) -> tk.Frame:
        return tk.Frame(parent, bg=self.theme["bg"], **kw)

    def _make_label(self, parent, text="", font_size=10, bold=False,
                    fg_key="fg", **kw) -> tk.Label:
        t = self.theme
        weight = "bold" if bold else "normal"
        return tk.Label(parent, text=text, bg=t["bg"], fg=t[fg_key],
                        font=(FONT_FAMILY, font_size, weight), **kw)

    def _make_entry(self, parent, textvariable=None, show=None, **kw) -> tk.Entry:
        t = self.theme
        return tk.Entry(parent, textvariable=textvariable, show=show,
                        bg=t["entry_bg"], fg=t["entry_fg"],
                        insertbackground=t["fg"], font=(FONT_FAMILY, 11),
                        relief="flat", bd=4, **kw)

    def _make_text(self, parent, height=5, **kw) -> tk.Text:
        t = self.theme
        return tk.Text(parent, bg=t["entry_bg"], fg=t["entry_fg"],
                       insertbackground=t["fg"], font=(FONT_FAMILY, 10),
                       relief="flat", bd=4, height=height, wrap="word", **kw)

    def _make_button(self, parent, text, command, color_key="accent",
                     **kw) -> tk.Button:
        t = self.theme
        bg = t[color_key]
        fg = t["accent_fg"] if color_key == "accent" else t["button_fg"]
        return tk.Button(parent, text=text, command=command,
                         bg=bg, fg=fg, activebackground=t["button_active"],
                         font=(FONT_FAMILY, 10, "bold"), relief="flat",
                         bd=0, cursor="hand2", padx=14, pady=6, **kw)

    def _make_secondary_button(self, parent, text, command, **kw) -> tk.Button:
        return self._make_button(parent, text, command,
                                 color_key="button_bg", **kw)

    # ==================================================================
    #  Pano (clipboard)
    # ==================================================================
    def _copy_to_clipboard(self, text: str) -> None:
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
        except tk.TclError:
            return

        if self._clipboard_timer:
            self._clipboard_timer.cancel()

        def _clear():
            try:
                self.root.after(0, lambda: (
                    self.root.clipboard_clear(),
                    self.root.clipboard_append(""),
                ))
            except Exception:
                pass

        self._clipboard_timer = threading.Timer(30.0, _clear)
        self._clipboard_timer.daemon = True
        self._clipboard_timer.start()

    # ==================================================================
    #  LOGIN EKRANI
    # ==================================================================
    def _show_login(self) -> None:
        for w in self.root.winfo_children():
            w.destroy()

        self.root.configure(bg=self.theme["bg"])
        self._apply_ttk_styles()

        t = self.theme
        frame = self._make_frame(self.root)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        self._make_label(frame, "🔐", font_size=42).pack(pady=(0, 5))
        self._make_label(frame, APP_NAME, font_size=24, bold=True,
                         fg_key="accent").pack()
        self._make_label(frame, "Güvenli Şifre Yöneticisi", font_size=11,
                         fg_key="muted").pack(pady=(0, 30))

        is_first = self._data_mgr.is_first_run()

        prompt = ("Yeni master parola belirleyin:" if is_first
                  else "Master parolanızı girin:")
        self._make_label(frame, prompt, font_size=11).pack(anchor="w", padx=5)

        pw_var = tk.StringVar()
        pw_entry = self._make_entry(frame, textvariable=pw_var,
                                    show="●", width=35)
        pw_entry.pack(pady=(5, 8), ipady=4)
        pw_entry.focus_set()

        confirm_var = tk.StringVar()
        confirm_entry = None
        if is_first:
            self._make_label(frame, "Parolayı tekrar girin:",
                             font_size=11).pack(anchor="w", padx=5)
            confirm_entry = self._make_entry(frame, textvariable=confirm_var,
                                             show="●", width=35)
            confirm_entry.pack(pady=(5, 8), ipady=4)

        status_var = tk.StringVar()
        tk.Label(frame, textvariable=status_var, bg=t["bg"],
                 fg=t["error"], font=(FONT_FAMILY, 10)).pack(pady=(0, 10))

        def on_submit(_event=None):
            pw = pw_var.get()
            if not pw:
                status_var.set("Parola boş olamaz.")
                return

            if is_first:
                if len(pw) < 8:
                    status_var.set("Parola en az 8 karakter olmalıdır.")
                    return
                if pw != confirm_var.get():
                    status_var.set("Parolalar eşleşmiyor.")
                    return
                status_var.set("Vault oluşturuluyor…")
                self.root.update_idletasks()
                try:
                    self._data_mgr.create_master_password(pw)
                except Exception as exc:
                    status_var.set(f"Hata: {exc}")
                    return
            else:
                status_var.set("Doğrulanıyor…")
                self.root.update_idletasks()
                if not self._data_mgr.authenticate(pw):
                    status_var.set("Yanlış parola!")
                    return

            self._current_theme = self._data_mgr.get_theme()
            self._show_main()

        pw_entry.bind("<Return>", on_submit)
        if confirm_entry:
            confirm_entry.bind("<Return>", on_submit)

        btn_text = "Oluştur ve Giriş Yap" if is_first else "Giriş Yap"
        self._make_button(frame, btn_text, on_submit).pack(
            pady=(5, 0), ipadx=10)

    # ==================================================================
    #  ANA EKRAN
    # ==================================================================
    def _show_main(self, restore_tab: int = 0) -> None:
        for w in self.root.winfo_children():
            w.destroy()

        self.root.configure(bg=self.theme["bg"])
        self._apply_ttk_styles()

        # --- Üst çubuk ---
        top_bar = self._make_frame(self.root)
        top_bar.pack(fill="x", padx=15, pady=(10, 0))

        self._make_label(top_bar, f"🔐 {APP_NAME}", font_size=14,
                         bold=True, fg_key="accent").pack(side="left")

        right_frame = self._make_frame(top_bar)
        right_frame.pack(side="right")

        theme_icon = "☀️" if self._current_theme == "dark" else "🌙"
        self._make_secondary_button(right_frame, theme_icon,
                                    self._toggle_theme).pack(side="left", padx=3)
        self._make_secondary_button(right_frame, "🔑 Parola Değiştir",
                                    self._show_change_password).pack(side="left", padx=3)
        self._make_secondary_button(right_frame, "🔒 Kilitle",
                                    self._lock_app).pack(side="left", padx=3)

        # --- Sekmeler ---
        self._notebook = ttk.Notebook(self.root)
        self._notebook.pack(fill="both", expand=True, padx=15, pady=10)

        tab_gen = self._make_frame(self._notebook)
        tab_vault = self._make_frame(self._notebook)
        tab_notes = self._make_frame(self._notebook)
        tab_health = self._make_frame(self._notebook)

        self._notebook.add(tab_gen, text="  🎲 Şifre Üreteci  ")
        self._notebook.add(tab_vault, text="  🔑 Şifre Kasası  ")
        self._notebook.add(tab_notes, text="  📝 Not Defteri  ")
        self._notebook.add(tab_health, text="  📊 Sağlık Raporu  ")

        self._build_generator_tab(tab_gen)
        self._build_vault_tab(tab_vault)
        self._build_notes_tab(tab_notes)
        self._build_health_tab(tab_health)

        if restore_tab < self._notebook.index("end"):
            self._notebook.select(restore_tab)

        self.root.bind("<Control-l>", lambda _: self._lock_app())
        self.root.bind("<Control-L>", lambda _: self._lock_app())

        if not self._tray_running:
            self._setup_tray()

    # ==================================================================
    #  SEKME 1 — Şifre Üreteci
    # ==================================================================
    def _build_generator_tab(self, parent: tk.Frame) -> None:
        t = self.theme
        container = self._make_frame(parent)
        container.pack(fill="both", expand=True, padx=20, pady=15)

        self._make_label(container, "Rastgele Şifre Üreteci", font_size=14,
                         bold=True).pack(anchor="w")
        self._make_label(container, "Kriptografik olarak güvenli şifre üretin",
                         font_size=9, fg_key="muted").pack(anchor="w", pady=(0, 15))

        # Uzunluk
        len_frame = self._make_frame(container)
        len_frame.pack(fill="x", pady=5)

        self._make_label(len_frame, "Uzunluk:", font_size=10).pack(side="left")
        self._gen_length_var = tk.IntVar(value=16)
        len_val = self._make_label(len_frame, "16", font_size=11,
                                   bold=True, fg_key="accent")
        len_val.pack(side="right")

        ttk.Scale(
            len_frame, from_=8, to=128, variable=self._gen_length_var,
            orient="horizontal",
            command=lambda v: len_val.configure(text=str(int(float(v)))),
        ).pack(side="left", fill="x", expand=True, padx=10)

        # Karakter seçenekleri
        opts = self._make_frame(container)
        opts.pack(fill="x", pady=10)

        self._gen_upper = tk.BooleanVar(value=True)
        self._gen_lower = tk.BooleanVar(value=True)
        self._gen_digits = tk.BooleanVar(value=True)
        self._gen_special = tk.BooleanVar(value=True)

        for label, var in [("ABC Büyük Harf", self._gen_upper),
                           ("abc Küçük Harf", self._gen_lower),
                           ("123 Rakam", self._gen_digits),
                           ("!@# Özel Karakter", self._gen_special)]:
            ttk.Checkbutton(opts, text=label, variable=var).pack(
                side="left", padx=(0, 15))

        self._make_button(container, "🎲  Şifre Üret",
                          self._generate_password).pack(pady=15)

        # Sonuç
        result_frame = self._make_frame(container)
        result_frame.pack(fill="x", pady=5)
        result_frame.configure(bg=t["entry_bg"], bd=2, relief="flat",
                               highlightbackground=t["border"],
                               highlightthickness=1)

        self._gen_result_var = tk.StringVar()
        tk.Entry(result_frame, textvariable=self._gen_result_var,
                 font=("Consolas", 16), bg=t["entry_bg"], fg=t["accent"],
                 relief="flat", bd=8, readonlybackground=t["entry_bg"],
                 state="readonly", justify="center").pack(fill="x")

        # Güç göstergesi
        sf = self._make_frame(container)
        sf.pack(fill="x", pady=8)
        self._gen_strength_canvas = tk.Canvas(sf, height=8, bg=t["entry_bg"],
                                              highlightthickness=0)
        self._gen_strength_canvas.pack(fill="x")
        self._gen_strength_label = self._make_label(sf, "", font_size=10,
                                                    bold=True)
        self._gen_strength_label.pack(pady=(5, 0))

        # Alt butonlar
        bf = self._make_frame(container)
        bf.pack(fill="x", pady=10)
        self._make_button(bf, "📋 Panoya Kopyala",
                          self._copy_generated).pack(side="left", padx=(0, 10))
        self._make_button(bf, "💾 Kasaya Kaydet",
                          self._save_generated_to_vault).pack(side="left")
        self._gen_info_label = self._make_label(bf, "", font_size=9,
                                                fg_key="muted")
        self._gen_info_label.pack(side="right")

    def _generate_password(self) -> None:
        t = self.theme
        try:
            password = self._pass_gen.generate(
                length=self._gen_length_var.get(),
                uppercase=self._gen_upper.get(),
                lowercase=self._gen_lower.get(),
                digits=self._gen_digits.get(),
                special=self._gen_special.get(),
            )
        except ValueError as exc:
            messagebox.showwarning("Uyarı", str(exc), parent=self.root)
            return

        self._gen_result_var.set(password)

        strength = self._pass_gen.calculate_strength(password)
        canvas = self._gen_strength_canvas
        canvas.delete("all")
        cw = canvas.winfo_width() or 400
        fill_w = int(cw * strength["score"] / 100)
        color = t[strength["color"]]
        canvas.create_rectangle(0, 0, cw, 8, fill=t["entry_bg"], outline="")
        canvas.create_rectangle(0, 0, fill_w, 8, fill=color, outline="")

        self._gen_strength_label.configure(
            text=f"{strength['label']}  —  {strength['entropy']:.0f} bit entropi",
            fg=color,
        )

    def _copy_generated(self) -> None:
        pw = self._gen_result_var.get()
        if pw:
            self._copy_to_clipboard(pw)
            self._gen_info_label.configure(
                text="✓ Kopyalandı (30sn sonra temizlenecek)")
            self.root.after(
                3000, lambda: self._gen_info_label.configure(text=""))

    def _save_generated_to_vault(self) -> None:
        pw = self._gen_result_var.get()
        if not pw:
            messagebox.showinfo("Bilgi", "Önce bir şifre üretin.",
                                parent=self.root)
            return
        self._notebook.select(1)
        self._vault_pass_var.set(pw)

    # ==================================================================
    #  SEKME 2 — Şifre Kasası
    # ==================================================================
    def _build_vault_tab(self, parent: tk.Frame) -> None:
        t = self.theme
        container = self._make_frame(parent)
        container.pack(fill="both", expand=True, padx=20, pady=15)

        # Başlık + Arama
        top = self._make_frame(container)
        top.pack(fill="x", pady=(0, 10))
        self._make_label(top, "Şifre Kasası", font_size=14,
                         bold=True).pack(side="left")

        search_fr = self._make_frame(top)
        search_fr.pack(side="right")
        self._vault_search_var = tk.StringVar()
        self._vault_search_var.trace_add(
            "write", lambda *_: self._refresh_vault_tree())
        self._make_entry(search_fr, textvariable=self._vault_search_var,
                         width=20).pack(side="left", padx=(0, 8))
        self._make_label(search_fr, "Ara:", font_size=10).pack(side="left")

        # Kategori filtresi
        cat_fr = self._make_frame(container)
        cat_fr.pack(fill="x", pady=(0, 8))
        self._make_label(cat_fr, "Kategori:", font_size=10).pack(side="left")
        self._vault_cat_filter_var = tk.StringVar(value="Tümü")
        cats = ["Tümü"] + self._data_mgr.get_all_categories()
        self._vault_cat_filter = ttk.Combobox(
            cat_fr, values=cats, textvariable=self._vault_cat_filter_var,
            state="readonly", width=18)
        self._vault_cat_filter.pack(side="left", padx=8)
        self._vault_cat_filter.bind(
            "<<ComboboxSelected>>", lambda _: self._refresh_vault_tree())

        # Treeview
        tree_fr = self._make_frame(container)
        tree_fr.pack(fill="both", expand=True)
        cols = ("site", "user", "category", "date")
        self._vault_tree = ttk.Treeview(tree_fr, columns=cols,
                                        show="headings", selectmode="browse")
        self._vault_tree.heading("site", text="Site Adı")
        self._vault_tree.heading("user", text="Kullanıcı Adı")
        self._vault_tree.heading("category", text="Kategori")
        self._vault_tree.heading("date", text="Tarih")
        self._vault_tree.column("site", width=200)
        self._vault_tree.column("user", width=180)
        self._vault_tree.column("category", width=120)
        self._vault_tree.column("date", width=100)
        vsb = ttk.Scrollbar(tree_fr, orient="vertical",
                            command=self._vault_tree.yview)
        self._vault_tree.configure(yscrollcommand=vsb.set)
        self._vault_tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self._vault_tree.bind("<<TreeviewSelect>>", self._on_vault_select)

        # Form alanı
        form_fr = self._make_frame(container)
        form_fr.pack(fill="x", pady=(10, 0))

        left = self._make_frame(form_fr)
        left.pack(side="left", fill="both", expand=True)

        # site
        self._make_label(left, "Site Adı:", font_size=10).grid(
            row=0, column=0, sticky="w", pady=2)
        self._vault_site_var = tk.StringVar()
        self._make_entry(left, textvariable=self._vault_site_var,
                         width=30).grid(row=0, column=1, sticky="ew",
                                        pady=2, padx=(5, 0))
        # kullanıcı
        self._make_label(left, "Kullanıcı:", font_size=10).grid(
            row=1, column=0, sticky="w", pady=2)
        self._vault_user_var = tk.StringVar()
        self._make_entry(left, textvariable=self._vault_user_var,
                         width=30).grid(row=1, column=1, sticky="ew",
                                        pady=2, padx=(5, 0))
        # şifre
        self._make_label(left, "Şifre:", font_size=10).grid(
            row=2, column=0, sticky="w", pady=2)
        self._vault_pass_var = tk.StringVar()
        self._vault_pass_entry = self._make_entry(
            left, textvariable=self._vault_pass_var, show="●", width=30)
        self._vault_pass_entry.grid(row=2, column=1, sticky="ew",
                                    pady=2, padx=(5, 0))
        self._vault_pass_visible = False

        # kategori
        self._make_label(left, "Kategori:", font_size=10).grid(
            row=3, column=0, sticky="w", pady=2)
        self._vault_cat_var = tk.StringVar(value=DEFAULT_CATEGORIES[0])
        self._vault_cat_combo = ttk.Combobox(
            left, values=self._data_mgr.get_all_categories(),
            textvariable=self._vault_cat_var, state="readonly", width=28)
        self._vault_cat_combo.grid(row=3, column=1, sticky="ew",
                                   pady=2, padx=(5, 0))

        # notlar
        self._make_label(left, "Notlar:", font_size=10).grid(
            row=4, column=0, sticky="nw", pady=2)
        self._vault_notes_text = self._make_text(left, height=2)
        self._vault_notes_text.grid(row=4, column=1, sticky="ew",
                                    pady=2, padx=(5, 0))
        left.columnconfigure(1, weight=1)

        # Butonlar
        right = self._make_frame(form_fr)
        right.pack(side="right", padx=(15, 0))
        self._make_button(right, "➕ Ekle",
                          self._add_vault_entry).pack(fill="x", pady=2)
        self._make_button(right, "✏️ Güncelle",
                          self._update_vault_entry).pack(fill="x", pady=2)
        self._make_secondary_button(right, "🗑️ Sil",
                                    self._delete_vault_entry).pack(fill="x", pady=2)
        self._make_secondary_button(right, "👁️ Göster/Gizle",
                                    self._toggle_vault_pass).pack(fill="x", pady=2)
        self._make_secondary_button(right, "📋 Kopyala",
                                    self._copy_vault_pass).pack(fill="x", pady=2)
        self._make_secondary_button(right, "🧹 Temizle",
                                    self._clear_vault_form).pack(fill="x", pady=2)

        self._refresh_vault_tree()

    # --- Vault yardımcıları ---

    def _refresh_vault_tree(self) -> None:
        tree = self._vault_tree
        tree.delete(*tree.get_children())
        query = self._vault_search_var.get().strip()
        category = self._vault_cat_filter_var.get()
        for pwd in self._data_mgr.search_passwords(query, category):
            tree.insert("", tk.END, iid=pwd["id"],
                        values=(pwd.get("site_name", ""),
                                pwd.get("username", ""),
                                pwd.get("category", ""),
                                pwd.get("created_at", "")[:10]))

    def _on_vault_select(self, _event=None) -> None:
        sel = self._vault_tree.selection()
        if not sel:
            self._selected_pwd_id = None
            return
        self._selected_pwd_id = sel[0]
        pwd = self._data_mgr.get_password(self._selected_pwd_id)
        if not pwd:
            return
        self._vault_site_var.set(pwd.get("site_name", ""))
        self._vault_user_var.set(pwd.get("username", ""))
        self._vault_pass_var.set(pwd.get("password", ""))
        self._vault_cat_var.set(pwd.get("category", DEFAULT_CATEGORIES[0]))
        self._vault_notes_text.delete("1.0", tk.END)
        self._vault_notes_text.insert("1.0", pwd.get("notes", ""))

    def _add_vault_entry(self) -> None:
        site = self._vault_site_var.get().strip()
        password = self._vault_pass_var.get().strip()
        if not site:
            messagebox.showwarning("Uyarı", "Site adı boş olamaz.",
                                   parent=self.root)
            return
        if not password:
            messagebox.showwarning("Uyarı", "Şifre boş olamaz.",
                                   parent=self.root)
            return
        self._data_mgr.add_password({
            "site_name": site,
            "username": self._vault_user_var.get().strip(),
            "password": password,
            "category": self._vault_cat_var.get().strip() or DEFAULT_CATEGORIES[-1],
            "notes": self._vault_notes_text.get("1.0", tk.END).strip(),
        })
        self._clear_vault_form()
        self._refresh_vault_tree()

    def _update_vault_entry(self) -> None:
        if not self._selected_pwd_id:
            messagebox.showinfo("Bilgi", "Güncellenecek kaydı listeden seçin.",
                                parent=self.root)
            return
        site = self._vault_site_var.get().strip()
        password = self._vault_pass_var.get().strip()
        if not site:
            messagebox.showwarning("Uyarı", "Site adı boş olamaz.",
                                   parent=self.root)
            return
        if not password:
            messagebox.showwarning("Uyarı", "Şifre boş olamaz.",
                                   parent=self.root)
            return
        self._data_mgr.update_password(self._selected_pwd_id, {
            "site_name": site,
            "username": self._vault_user_var.get().strip(),
            "password": password,
            "category": self._vault_cat_var.get().strip(),
            "notes": self._vault_notes_text.get("1.0", tk.END).strip(),
        })
        self._refresh_vault_tree()

    def _delete_vault_entry(self) -> None:
        if not self._selected_pwd_id:
            messagebox.showinfo("Bilgi", "Silinecek kaydı listeden seçin.",
                                parent=self.root)
            return
        if not messagebox.askyesno("Onay",
                                   "Bu şifre kaydını silmek istediğinize "
                                   "emin misiniz?", parent=self.root):
            return
        self._data_mgr.delete_password(self._selected_pwd_id)
        self._clear_vault_form()
        self._refresh_vault_tree()

    def _toggle_vault_pass(self) -> None:
        self._vault_pass_visible = not self._vault_pass_visible
        self._vault_pass_entry.configure(
            show="" if self._vault_pass_visible else "●")

    def _copy_vault_pass(self) -> None:
        pw = self._vault_pass_var.get()
        if pw:
            self._copy_to_clipboard(pw)

    def _clear_vault_form(self) -> None:
        self._selected_pwd_id = None
        self._vault_site_var.set("")
        self._vault_user_var.set("")
        self._vault_pass_var.set("")
        self._vault_cat_var.set(DEFAULT_CATEGORIES[0])
        self._vault_notes_text.delete("1.0", tk.END)
        self._vault_pass_visible = False
        self._vault_pass_entry.configure(show="●")
        for item in self._vault_tree.selection():
            self._vault_tree.selection_remove(item)

    # ==================================================================
    #  SEKME 3 — Not Defteri
    # ==================================================================
    def _build_notes_tab(self, parent: tk.Frame) -> None:
        t = self.theme
        container = self._make_frame(parent)
        container.pack(fill="both", expand=True, padx=20, pady=15)

        self._make_label(container, "Güvenli Not Defteri", font_size=14,
                         bold=True).pack(anchor="w")
        self._make_label(container, "Notlarınız AES-256 ile şifrelenir",
                         font_size=9, fg_key="muted").pack(anchor="w", pady=(0, 10))

        paned = tk.PanedWindow(container, orient="horizontal",
                               bg=t["border"], sashwidth=4, bd=0)
        paned.pack(fill="both", expand=True)

        # Sol: Not listesi
        left = self._make_frame(paned)
        paned.add(left, width=250)

        self._notes_listbox = tk.Listbox(
            left, bg=t["entry_bg"], fg=t["fg"], font=(FONT_FAMILY, 10),
            selectbackground=t["select_bg"], selectforeground=t["select_fg"],
            relief="flat", bd=4, activestyle="none")
        self._notes_listbox.pack(fill="both", expand=True)
        self._notes_listbox.bind("<<ListboxSelect>>", self._on_note_select)

        btn_row = self._make_frame(left)
        btn_row.pack(fill="x", pady=(5, 0))
        self._make_button(btn_row, "➕ Yeni", self._new_note).pack(
            side="left", fill="x", expand=True, padx=(0, 2))
        self._make_secondary_button(btn_row, "🗑️ Sil",
                                    self._delete_note).pack(
            side="left", fill="x", expand=True, padx=(2, 0))

        # Sağ: Not düzenleyici
        right = self._make_frame(paned)
        paned.add(right)

        self._make_label(right, "Başlık:", font_size=10).pack(anchor="w")
        self._note_title_var = tk.StringVar()
        self._make_entry(right, textvariable=self._note_title_var).pack(
            fill="x", pady=(2, 8), ipady=2)

        self._make_label(right, "İçerik:", font_size=10).pack(anchor="w")
        self._note_content_text = self._make_text(right, height=12)
        self._note_content_text.pack(fill="both", expand=True, pady=(2, 8))

        self._note_date_label = self._make_label(right, "", font_size=9,
                                                 fg_key="muted")
        self._note_date_label.pack(anchor="w")

        self._make_button(right, "💾 Kaydet", self._save_note).pack(
            anchor="w", pady=(8, 0))

        self._refresh_notes_list()

    # --- Not yardımcıları ---

    def _refresh_notes_list(self) -> None:
        self._notes_listbox.delete(0, tk.END)
        self._notes_ids: list[str] = []
        for note in self._data_mgr.get_notes():
            self._notes_ids.append(note["id"])
            self._notes_listbox.insert(tk.END,
                                       note.get("title", "(Başlıksız)"))

    def _on_note_select(self, _event=None) -> None:
        sel = self._notes_listbox.curselection()
        if not sel:
            self._selected_note_id = None
            return
        idx = sel[0]
        if idx >= len(self._notes_ids):
            return
        self._selected_note_id = self._notes_ids[idx]
        note = self._data_mgr.get_note(self._selected_note_id)
        if not note:
            return
        self._note_title_var.set(note.get("title", ""))
        self._note_content_text.delete("1.0", tk.END)
        self._note_content_text.insert("1.0", note.get("content", ""))
        created = note.get("created_at", "")[:19].replace("T", " ")
        updated = note.get("updated_at", "")[:19].replace("T", " ")
        self._note_date_label.configure(
            text=f"Oluşturma: {created}  |  Güncelleme: {updated}")

    def _new_note(self) -> None:
        self._selected_note_id = None
        self._note_title_var.set("")
        self._note_content_text.delete("1.0", tk.END)
        self._note_date_label.configure(text="")
        self._notes_listbox.selection_clear(0, tk.END)

    def _save_note(self) -> None:
        title = self._note_title_var.get().strip()
        content = self._note_content_text.get("1.0", tk.END).strip()
        if not title:
            messagebox.showwarning("Uyarı", "Not başlığı boş olamaz.",
                                   parent=self.root)
            return

        if self._selected_note_id:
            self._data_mgr.update_note(self._selected_note_id,
                                       {"title": title, "content": content})
        else:
            new_id = self._data_mgr.add_note(
                {"title": title, "content": content})
            self._selected_note_id = new_id

        self._refresh_notes_list()
        if self._selected_note_id in self._notes_ids:
            idx = self._notes_ids.index(self._selected_note_id)
            self._notes_listbox.selection_set(idx)
            self._on_note_select()

    def _delete_note(self) -> None:
        if not self._selected_note_id:
            messagebox.showinfo("Bilgi", "Silinecek notu listeden seçin.",
                                parent=self.root)
            return
        if not messagebox.askyesno("Onay",
                                   "Bu notu silmek istediğinize "
                                   "emin misiniz?", parent=self.root):
            return
        self._data_mgr.delete_note(self._selected_note_id)
        self._new_note()
        self._refresh_notes_list()

    # ==================================================================
    #  SEKME 4 — Sağlık Raporu
    # ==================================================================
    def _build_health_tab(self, parent: tk.Frame) -> None:
        t = self.theme
        container = self._make_frame(parent)
        container.pack(fill="both", expand=True, padx=20, pady=15)

        header = self._make_frame(container)
        header.pack(fill="x", pady=(0, 10))
        self._make_label(header, "Şifre Sağlık Raporu", font_size=14,
                         bold=True).pack(side="left")
        self._make_button(header, "🔄 Yenile",
                          self._refresh_health).pack(side="right")

        # Skor
        score_fr = self._make_frame(container)
        score_fr.pack(fill="x", pady=10)
        score_fr.configure(bg=t["entry_bg"], bd=1, relief="flat",
                           highlightbackground=t["border"],
                           highlightthickness=1)

        self._health_score_label = tk.Label(
            score_fr, text="—", bg=t["entry_bg"], fg=t["accent"],
            font=(FONT_FAMILY, 48, "bold"))
        self._health_score_label.pack(side="left", padx=20, pady=10)

        info_fr = self._make_frame(score_fr)
        info_fr.pack(side="left", padx=10)
        info_fr.configure(bg=t["entry_bg"])
        self._health_info_label = tk.Label(
            info_fr,
            text='Rapor oluşturmak için\n"Yenile" butonuna tıklayın.',
            bg=t["entry_bg"], fg=t["fg"], font=(FONT_FAMILY, 10),
            justify="left")
        self._health_info_label.pack(anchor="w")

        # Detay tablosu
        detail_fr = self._make_frame(container)
        detail_fr.pack(fill="both", expand=True, pady=(10, 0))
        cols = ("site", "user", "strength", "entropy")
        self._health_tree = ttk.Treeview(detail_fr, columns=cols,
                                         show="headings", selectmode="browse")
        self._health_tree.heading("site", text="Site")
        self._health_tree.heading("user", text="Kullanıcı")
        self._health_tree.heading("strength", text="Güç")
        self._health_tree.heading("entropy", text="Entropi (bit)")
        self._health_tree.column("site", width=200)
        self._health_tree.column("user", width=160)
        self._health_tree.column("strength", width=100)
        self._health_tree.column("entropy", width=100)
        hsb = ttk.Scrollbar(detail_fr, orient="vertical",
                            command=self._health_tree.yview)
        self._health_tree.configure(yscrollcommand=hsb.set)
        self._health_tree.pack(side="left", fill="both", expand=True)
        hsb.pack(side="right", fill="y")

        self._health_dup_label = self._make_label(container, "",
                                                  font_size=10,
                                                  fg_key="warning")
        self._health_dup_label.pack(anchor="w", pady=(8, 0))

        self.root.after(100, self._refresh_health)

    def _refresh_health(self) -> None:
        t = self.theme
        passwords = self._data_mgr.get_passwords()
        report = self._health.get_report(passwords)

        score = report["score"]
        if score >= 75:
            color = t["success"]
        elif score >= 50:
            color = t["warning"]
        else:
            color = t["error"]

        self._health_score_label.configure(text=str(score), fg=color)
        self._health_info_label.configure(
            text=(f"Toplam: {report['total']} kayıt\n"
                  f"Güçlü: {report['strong_count']}  |  "
                  f"Orta: {report['medium_count']}  |  "
                  f"Zayıf: {report['weak_count']}"))

        tree = self._health_tree
        tree.delete(*tree.get_children())
        tree.tag_configure("strong", foreground=t["success"])
        tree.tag_configure("medium", foreground=t["warning"])
        tree.tag_configure("weak", foreground=t["error"])

        for a in report["analysis"]:
            tag = ("weak" if a["score"] <= 25
                   else "medium" if a["score"] <= 50
                   else "strong")
            tree.insert("", tk.END, values=(
                a["site_name"], a["username"],
                a["label"], f"{a['entropy']:.0f}",
            ), tags=(tag,))

        dups = report["duplicates"]
        if dups:
            parts = [" ↔ ".join(e.get("site_name", "?") for e in g)
                     for g in dups]
            dup_text = "⚠️ Tekrar eden şifreler: " + "  |  ".join(parts)
        else:
            dup_text = "✅ Tekrar eden şifre bulunmadı."
        self._health_dup_label.configure(text=dup_text)

    # ==================================================================
    #  Parola Değiştirme Dialogu
    # ==================================================================
    def _show_change_password(self) -> None:
        """Master parola değiştirme penceresi açar."""
        t = self.theme
        dialog = tk.Toplevel(self.root)
        dialog.title("Master Parola Değiştir")
        dialog.geometry("420x340")
        dialog.resizable(False, False)
        dialog.configure(bg=t["bg"])
        dialog.transient(self.root)
        dialog.grab_set()

        # Pencereyi ortala
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 210
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 170
        dialog.geometry(f"+{x}+{y}")

        frame = tk.Frame(dialog, bg=t["bg"])
        frame.pack(fill="both", expand=True, padx=30, pady=20)

        tk.Label(frame, text="🔑 Parola Değiştir", bg=t["bg"], fg=t["accent"],
                 font=(FONT_FAMILY, 16, "bold")).pack(pady=(0, 15))

        # Mevcut parola
        tk.Label(frame, text="Mevcut Parola:", bg=t["bg"], fg=t["fg"],
                 font=(FONT_FAMILY, 10), anchor="w").pack(fill="x")
        old_pw_var = tk.StringVar()
        old_entry = tk.Entry(frame, textvariable=old_pw_var, show="●",
                             bg=t["entry_bg"], fg=t["entry_fg"],
                             insertbackground=t["fg"], font=(FONT_FAMILY, 11),
                             relief="flat", bd=4)
        old_entry.pack(fill="x", pady=(2, 8), ipady=3)
        old_entry.focus_set()

        # Yeni parola
        tk.Label(frame, text="Yeni Parola:", bg=t["bg"], fg=t["fg"],
                 font=(FONT_FAMILY, 10), anchor="w").pack(fill="x")
        new_pw_var = tk.StringVar()
        tk.Entry(frame, textvariable=new_pw_var, show="●",
                 bg=t["entry_bg"], fg=t["entry_fg"],
                 insertbackground=t["fg"], font=(FONT_FAMILY, 11),
                 relief="flat", bd=4).pack(fill="x", pady=(2, 8), ipady=3)

        # Yeni parola onay
        tk.Label(frame, text="Yeni Parola (Tekrar):", bg=t["bg"], fg=t["fg"],
                 font=(FONT_FAMILY, 10), anchor="w").pack(fill="x")
        confirm_pw_var = tk.StringVar()
        tk.Entry(frame, textvariable=confirm_pw_var, show="●",
                 bg=t["entry_bg"], fg=t["entry_fg"],
                 insertbackground=t["fg"], font=(FONT_FAMILY, 11),
                 relief="flat", bd=4).pack(fill="x", pady=(2, 8), ipady=3)

        # Durum mesajı
        status_var = tk.StringVar()
        tk.Label(frame, textvariable=status_var, bg=t["bg"],
                 fg=t["error"], font=(FONT_FAMILY, 10)).pack(pady=(5, 5))

        def on_change():
            old_pw = old_pw_var.get()
            new_pw = new_pw_var.get()
            confirm_pw = confirm_pw_var.get()

            if not old_pw:
                status_var.set("Mevcut parolayı girin.")
                return
            if not new_pw:
                status_var.set("Yeni parolayı girin.")
                return
            if len(new_pw) < 8:
                status_var.set("Yeni parola en az 8 karakter olmalıdır.")
                return
            if new_pw != confirm_pw:
                status_var.set("Yeni parolalar eşleşmiyor.")
                return
            if old_pw == new_pw:
                status_var.set("Yeni parola eskisiyle aynı olamaz.")
                return

            status_var.set("Değiştiriliyor…")
            dialog.update_idletasks()

            success = self._data_mgr.change_master_password(old_pw, new_pw)
            if success:
                dialog.destroy()
                messagebox.showinfo(
                    "Başarılı",
                    "Master parola başarıyla değiştirildi.",
                    parent=self.root,
                )
            else:
                status_var.set("Mevcut parola yanlış!")

        btn_frame = tk.Frame(frame, bg=t["bg"])
        btn_frame.pack(fill="x", pady=(5, 0))

        tk.Button(btn_frame, text="Değiştir", command=on_change,
                  bg=t["accent"], fg=t["accent_fg"],
                  activebackground=t["button_active"],
                  font=(FONT_FAMILY, 10, "bold"), relief="flat",
                  bd=0, cursor="hand2", padx=14, pady=6).pack(side="left")

        tk.Button(btn_frame, text="İptal", command=dialog.destroy,
                  bg=t["button_bg"], fg=t["button_fg"],
                  activebackground=t["button_active"],
                  font=(FONT_FAMILY, 10, "bold"), relief="flat",
                  bd=0, cursor="hand2", padx=14, pady=6).pack(side="left", padx=(8, 0))

    # ==================================================================
    #  Sistem tepsisi (pystray)
    # ==================================================================
    def _setup_tray(self) -> None:
        if not HAS_PYSTRAY:
            return
        try:
            icon_img = Image.new("RGB", (64, 64), "#1e66f5")
            draw = ImageDraw.Draw(icon_img)
            draw.rectangle([20, 30, 44, 52], fill="#ffffff")
            draw.arc([24, 16, 40, 38], 0, 180, fill="#ffffff", width=3)

            menu = pystray.Menu(
                MenuItem("Aç", self._tray_open, default=True),
                MenuItem("Kilitle", self._tray_lock),
                pystray.Menu.SEPARATOR,
                MenuItem("Çıkış", self._tray_quit),
            )
            self._tray = pystray.Icon(APP_NAME, icon_img, APP_NAME, menu)
            threading.Thread(target=self._tray.run, daemon=True).start()
            self._tray_running = True
        except Exception:
            self._tray = None
            self._tray_running = False

    def _tray_open(self, _icon=None, _item=None):
        self.root.after(0, self._show_window)

    def _tray_lock(self, _icon=None, _item=None):
        self.root.after(0, self._lock_app)

    def _tray_quit(self, _icon=None, _item=None):
        self.root.after(0, self._quit_app)

    def _show_window(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    # ==================================================================
    #  Uygulama durumu
    # ==================================================================
    def _on_close(self) -> None:
        if self._tray and self._tray_running:
            self.root.withdraw()
        else:
            self._quit_app()

    def _lock_app(self) -> None:
        if self._data_mgr:
            self._data_mgr.lock()
        self._selected_pwd_id = None
        self._selected_note_id = None
        self._show_login()

    def _quit_app(self) -> None:
        if self._data_mgr and self._data_mgr.is_authenticated:
            self._data_mgr.save()
        if self._clipboard_timer:
            self._clipboard_timer.cancel()
        if self._tray:
            try:
                self._tray.stop()
            except Exception:
                pass
        self.root.destroy()
