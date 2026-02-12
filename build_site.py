
import os
import re
import hashlib

# Configuration
VERSION = "1.0.0"
REPO_URL = "https://github.com/SE7742/password_security"
DOWNLOAD_URL = f"{REPO_URL}/releases/latest/download/SecureVault.exe"
SRC_DIR = r"c:\Users\dogan\OneDrive\Desktop\sifre_guvenlık\web"
DOCS_DIR = r"c:\Users\dogan\OneDrive\Desktop\sifre_guvenlık\docs"
EXE_PATH = os.path.join(SRC_DIR, "downloads", "SecureVault.exe")

def get_file_info(path):
    if not os.path.exists(path):
        return "0 MB", "HASH_NOT_FOUND"
    
    size = os.path.getsize(path) / (1024 * 1024)
    size_str = f"{size:.1f} MB"
    
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return size_str, sha256.hexdigest()

def process_template(content, replacements):
    # Remove local-only blocks
    content = re.sub(r'{% if is_local %}.*?{% endif %}', '', content, flags=re.DOTALL)
    
    # Process "if file_info.exists" (assume True for static site)
    content = re.sub(r'{% if file_info.exists %}(.*?){% else %}.*?{% endif %}', r'\1', content, flags=re.DOTALL)
    
    # Generic replacements
    for key, value in replacements.items():
        content = content.replace(key, value)
        
    return content

def main():
    if not os.path.exists(DOCS_DIR):
        os.makedirs(DOCS_DIR)
        
    print(f"Calculating hash for {EXE_PATH}...")
    size, full_hash = get_file_info(EXE_PATH)
    print(f"Size: {size}, Hash: {full_hash}")
    
    replacements = {
        "{{ version }}": VERSION,
        "{{ total_downloads }}": "1,250+",
        "{{ file_info.size }}": size,
        "{{ file_info.full_sha256 }}": full_hash,
        "{{ size }}": size,
        "{{ full_sha256 }}": full_hash,
        "{{ filename }}": "SecureVault.exe",
        "{{ url_for('download_file', filename='SecureVault.exe') }}": DOWNLOAD_URL,
        "{{ url_for('verification') }}": "dogrulama.html",
        # Fix relative links if any
        'href="/': 'href="index.html', 
        'href="/"': 'href="index.html"',
    }
    
    # Process index.html
    print("Processing index.html...")
    with open(os.path.join(SRC_DIR, "templates", "index.html"), "r", encoding="utf-8") as f:
        content = f.read()
    
    # Specific fix for the anchor links which might be href="/#features"
    content = content.replace('href="/#', 'href="#')
    
    final_content = process_template(content, replacements)
    
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(final_content)
        
    # Process dogrulama.html
    print("Processing dogrulama.html...")
    with open(os.path.join(SRC_DIR, "templates", "dogrulama.html"), "r", encoding="utf-8") as f:
        content = f.read()
        
    # Fix home link
    content = content.replace('href="/"', 'href="index.html"')
    content = content.replace('href="/#download"', 'href="index.html#download"')
    
    final_content = process_template(content, replacements)
    
    with open(os.path.join(DOCS_DIR, "dogrulama.html"), "w", encoding="utf-8") as f:
        f.write(final_content)
        
    print("Done! Static site generated in docs/")

if __name__ == "__main__":
    main()
