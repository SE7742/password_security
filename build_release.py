"""
Releases için EXE üretir — build yolu geliştirme ortamı içermez, sadece SecureVault adı kalır.

Kullanım:
    python build_release.py

EXE, proje kökündeki releases/ klasörüne yazılır.
"""
import os
import shutil
import subprocess
import sys
import tempfile

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Geliştirme ortamı yolları içermeyen nötr bir dizinde build et
    build_root = os.path.join(tempfile.gettempdir(), "SecureVault_build")
    build_dir = os.path.join(build_root, "src")
    os.makedirs(build_dir, exist_ok=True)

    # Gerekli dosya/klasörleri kopyala
    for name in ["main.py", "requirements.txt", "securevault", "SecureVault.spec"]:
        src = os.path.join(script_dir, name)
        dst = os.path.join(build_dir, name)
        if os.path.isfile(src):
            shutil.copy2(src, dst)
        elif os.path.isdir(src):
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)

    # PyInstaller ile build (temp dizinde geliştirme ortamı adı yok)
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm",
         "SecureVault.spec"],
        cwd=build_dir,
        check=True,
    )

    exe_src = os.path.join(build_dir, "dist", "SecureVault.exe")
    releases_dir = os.path.join(script_dir, "releases")
    os.makedirs(releases_dir, exist_ok=True)
    exe_dst = os.path.join(releases_dir, "SecureVault.exe")

    shutil.copy2(exe_src, exe_dst)
    print(f"EXE yazıldı: {exe_dst}")
    shutil.rmtree(build_root, ignore_errors=True)

if __name__ == "__main__":
    main()
