import sys
import subprocess
import os

print("=== MENGATUR LINGKUNGAN APLIKASI ADMINISTRASI GURU ===")
print("Python Executable:", sys.executable)
print("Python Version:", sys.version)

# Upgrade pip, setuptools, wheel
print("Memperbarui pip, setuptools, wheel...")
try:
    subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"], check=True)
except Exception as e:
    print("Warning updating pip/setuptools:", e)

# Packages to install
packages = [
    "Flask",
    "Flask-SQLAlchemy",
    "Flask-Login",
    "Werkzeug",
    "pandas",
    "openpyxl",
    "python-docx",
    "requests"
]

print("Menginstall pustaka satu per satu...")
for pkg in packages:
    print(f"Menginstall {pkg}...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "--prefer-binary", pkg], check=True)
    except Exception as e:
        print(f"Gagal menginstall {pkg}: {e}")

print("=== SELESAI PROSES INSTALASI ===")
print("Menjalankan server Flask (app.py)...")
os.system(f'"{sys.executable}" app.py')
