import sqlite3
from werkzeug.security import generate_password_hash
from config import DB_NAME

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            nama_lengkap TEXT,
            email TEXT,
            role TEXT NOT NULL DEFAULT 'guru'
        )
    ''')
    cursor.execute("SELECT * FROM users WHERE username = 'superadmin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password, nama_lengkap, email, role) VALUES (?, ?, ?, ?, ?)",
                       ('superadmin', generate_password_hash('super123'), 'Super Administrator', 'super@siakad.sch.id', 'superadmin'))
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password, nama_lengkap, email, role) VALUES (?, ?, ?, ?, ?)",
                       ('admin', generate_password_hash('admin123'), 'Administrator Sekolah', 'admin@siakad.sch.id', 'admin'))
    cursor.execute("SELECT * FROM users WHERE username = 'guru'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password, nama_lengkap, email, role) VALUES (?, ?, ?, ?, ?)",
                       ('guru', generate_password_hash('guru123'), 'Rizwan Yanuar Rizaldi, S.Pd', 'rizwan@sekolah.sch.id', 'guru'))

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS profil_sekolah (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_sekolah TEXT,
            npsn TEXT,
            kepala_sekolah TEXT,
            nip_kepsek TEXT,
            nama_guru TEXT,
            nip_guru TEXT,
            alamat TEXT
        )
    ''')
    cursor.execute("SELECT * FROM profil_sekolah WHERE id = 1")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO profil_sekolah (nama_sekolah, npsn, kepala_sekolah, nip_kepsek, nama_guru, nip_guru, alamat) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       ('SDN / SMP / SMA Negeri Teladan', '20278900', 'Drs. H. Ahmad Fauzi, M.Pd.', '196501011989031005', 'Rizwan Yanuar Rizaldi, S.Pd', '198801012014021001', 'Jl. Pendidikan No. 45, Bandung Barat'))

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS arsip_dokumen (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            kategori TEXT,
            judul TEXT,
            topik_normal TEXT,
            konten TEXT,
            is_cached_hit INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            aktivitas TEXT,
            detail TEXT,
            kota TEXT,
            ip_address TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pesan TEXT,
            tanggal TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute("SELECT COUNT(*) FROM notifications")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO notifications (pesan) VALUES (?)", 
                       ("Pembaruan Sistem v3.0: Struktur File Modular untuk Performa Ringan & Keamanan Terjaga.",))

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS modules_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module_name TEXT UNIQUE,
            module_key TEXT UNIQUE,
            is_active INTEGER DEFAULT 1
        )
    ''')
    default_modules = [
        ('Data Kelas & Siswa', 'data_kelas', 1),
        ('Profil Sekolah', 'profil_sekolah', 1),
        ('AI Generator Dokumen Word', 'ai_generator', 1),
        ('Riwayat Generate (History)', 'history_menu', 1)
    ]
    for m in default_modules:
        cursor.execute("INSERT OR IGNORE INTO modules_status (module_name, module_key, is_active) VALUES (?, ?, ?)", m)

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS online_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            role TEXT,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def log_user_activity(username, aktivitas, detail, ip='127.0.0.1'):
    kota = 'Bandung (Lokal)' if ip in ['127.0.0.1', 'localhost'] else 'Jakarta Pusat'
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO activity_logs (username, aktivitas, detail, kota, ip_address) VALUES (?, ?, ?, ?, ?)",
                   (username, aktivitas, detail, kota, ip))
    cursor.execute("INSERT OR REPLACE INTO online_users (username, role, last_seen) VALUES (?, (SELECT role FROM users WHERE username=?), CURRENT_TIMESTAMP)",
                   (username, username))
    conn.commit()
    conn.close()

def check_module_active(key):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT is_active FROM modules_status WHERE module_key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] == 1 if row else True
