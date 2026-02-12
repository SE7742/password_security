"""Eski Türkçe karakterli klasörü ASCII isimle değiştirir. Bir kez çalıştırıp silebilirsiniz."""
import os
import sys

# Proje kökü = bu script'in bulunduğu klasör
root = os.path.dirname(os.path.abspath(__file__))
os.chdir(root)

# şifre_güvenlik -> releases_legacy (EXE zaten releases/ içinde, bu kopya)
old_name = "şifre_güvenlik"
new_name = "releases_legacy"
old_path = os.path.join(root, old_name)
new_path = os.path.join(root, new_name)

if os.path.exists(old_path):
    if os.path.exists(new_path):
        import shutil
        shutil.rmtree(new_path)
    os.rename(old_path, new_path)
    print(f"Tamam: '{old_name}' -> '{new_name}' olarak değiştirildi.")
else:
    print(f"'{old_name}' klasörü bulunamadı (zaten kaldırılmış olabilir).")
    for x in sorted(os.listdir(root)):
        if os.path.isdir(os.path.join(root, x)):
            print(f"  [klasör] {x!r}")
