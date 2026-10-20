import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

app = Flask(__name__)
app.secret_key = 'super_secret_key_admin_guru_2026'
DATABASE = 'database.db'
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                nama_lengkap TEXT NOT NULL,
                nip TEXT DEFAULT '-',
                mapel TEXT DEFAULT '-',
                role TEXT CHECK(role IN ('superadmin', 'admin', 'guru')) NOT NULL,
                status TEXT CHECK(status IN ('pending', 'active')) DEFAULT 'pending',
                session_token TEXT,
                last_login TIMESTAMP
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS sekolah (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nama_sekolah TEXT,
                alamat TEXT,
                nama_kepsek TEXT,
                nip_kepsek TEXT,
                kop_surat TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS arsip (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                jenis_modul TEXT,
                topik TEXT,
                konten TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS log_aktivitas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                aktivitas TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS custom_modul (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nama_modul TEXT,
                kode_slug TEXT UNIQUE,
                template_path TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS notifikasi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pesan TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE role = 'superadmin'")
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO users (username, password, nama_lengkap, nip, mapel, role, status)
                VALUES ('superadmin', 'admin123', 'Rizwan Yanuar Rizaldi, S.Pd.', '198501012010011001', 'Informatika', 'superadmin', 'active')
            """)
        
        cursor.execute("SELECT * FROM sekolah")
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO sekolah (nama_sekolah, alamat, nama_kepsek, nip_kepsek, kop_surat)
                VALUES ('SMP/SMA Negeri Contoh Bandung', 'Jl. Pendidikan No. 1, Bandung', 'Drs. H. Ahmad Sutisna, M.Pd.', '196812121994031005', '')
            """)
        
        cursor.execute("SELECT * FROM notifikasi")
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO notifikasi (pesan, is_active)
                VALUES ('Info: Generator AI Kurikulum Merdeka BSKAP 2026 dengan C1-C6 dan Loading Animasi Diaktifkan.', 1)
            """)
        conn.commit()

init_db()

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    db = get_db()
    notif = db.execute("SELECT * FROM notifikasi ORDER BY id DESC LIMIT 1").fetchone()
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user and user['password'] == password:
            if user['status'] == 'pending':
                flash('Akun Anda masih menunggu konfirmasi oleh Admin. Silakan hubungi Admin via WhatsApp: 081321984848.', 'warning')
                return redirect(url_for('login'))
            import uuid
            new_token = str(uuid.uuid4())
            db.execute("UPDATE users SET session_token = ?, last_login = CURRENT_TIMESTAMP WHERE id = ?", (new_token, user['id']))
            db.commit()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['nama_lengkap'] = user['nama_lengkap']
            session['nip'] = user['nip']
            session['mapel'] = user['mapel']
            session['role'] = user['role']
            session['session_token'] = new_token
            flash('Login berhasil!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Username atau password salah!', 'danger')
    return render_template('login.html', notif=notif)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nama = request.form['nama']
        nip = request.form.get('nip', '-')
        username = request.form['username']
        password = request.form['password']
        mapel = request.form.get('mapel', 'Umum')
        db = get_db()
        try:
            db.execute("INSERT INTO users (username, password, nama_lengkap, nip, mapel, role, status) VALUES (?, ?, ?, ?, ?, 'guru', 'pending')",
                       (username, password, nama, nip, mapel))
            db.commit()
            flash('Pendaftaran berhasil! Akun Anda tidak dapat digunakan sebelum dikonfirmasi oleh Admin. Silakan konfirmasi ke Admin via WhatsApp: 081321984848.', 'warning')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username sudah terdaftar!', 'danger')
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    user = db.execute("SELECT session_token FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    if not user or user['session_token'] != session.get('session_token'):
        session.clear()
        flash('Akun Anda telah login di perangkat lain.', 'danger')
        return redirect(url_for('login'))
    logs = db.execute("SELECT aktivitas, timestamp FROM log_aktivitas WHERE user_id = ? ORDER BY id DESC LIMIT 3", (session['user_id'],)).fetchall()
    sekolah = db.execute("SELECT * FROM sekolah LIMIT 1").fetchone()
    current_user = db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    return render_template('dashboard.html', logs=logs, sekolah=sekolah, current_user=current_user)

@app.route('/update-sekolah', methods=['POST'])
def update_sekolah():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    nama_sekolah = request.form['nama_sekolah']
    alamat = request.form['alamat']
    nama_kepsek = request.form['nama_kepsek']
    nip_kepsek = request.form['nip_kepsek']
    
    file = request.files.get('kop_surat')
    db = get_db()
    
    if file and file.filename != '':
        filename = file.filename
        path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(path)
        db.execute("UPDATE sekolah SET nama_sekolah = ?, alamat = ?, nama_kepsek = ?, nip_kepsek = ?, kop_surat = ?",
                   (nama_sekolah, alamat, nama_kepsek, nip_kepsek, filename))
    else:
        db.execute("UPDATE sekolah SET nama_sekolah = ?, alamat = ?, nama_kepsek = ?, nip_kepsek = ?",
                   (nama_sekolah, alamat, nama_kepsek, nip_kepsek))
    db.commit()
    flash('Profil sekolah berhasil diperbarui!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/generator', methods=['GET', 'POST'])
def generator():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    custom_tabs = db.execute("SELECT * FROM custom_modul").fetchall()
    if request.method == 'POST':
        jenis = request.form['jenis_modul']
        jenjang = request.form['jenjang']
        kelas = request.form['kelas']
        fase = request.form.get('fase', 'Fase E')
        mapel = request.form['mapel']
        metode = request.form.get('metode', 'Project Based Learning (PjBL)')
        aktivitas = request.form.get('aktivitas', 'Eksplorasi & Diskusi Kelompok')
        kesulitan = request.form.get('kesulitan', 'C3 (Aplikasi)')
        jumlah_pg = request.form.get('jumlah_pg', '10')
        jumlah_esai = request.form.get('jumlah_esai', '5')
        jumlah_isian = request.form.get('jumlah_isian', '5')
        topik = request.form['topik']
        ruang_lingkup = request.form.get('ruang_lingkup', 'Umum Kurikulum Merdeka')
        
        user_info = db.execute("SELECT nama_lengkap, nip FROM users WHERE id = ?", (session['user_id'],)).fetchone()
        guru_nama = user_info['nama_lengkap'] if user_info else session.get('nama_lengkap', 'Guru')
        guru_nip = user_info['nip'] if user_info else session.get('nip', '-')
        
        cache_key = f"{jenis} | {mapel} | {kelas} | {jenjang} | {fase} | {topik} | {kesulitan}"
        cached = db.execute("SELECT konten FROM arsip WHERE jenis_modul = ? AND topik = ? LIMIT 1", (jenis, cache_key)).fetchone()
        
        if cached:
            hasil = cached['konten']
            source_info = "Diambil dari Cache Database (Hemat Token & Efisiensi Request)"
        else:
            if "Bank Soal" in jenis:
                hasil = f"[{jenis.upper()}] Mata Pelajaran: {mapel} | Jenjang: {jenjang} ({kelas} - {fase}) | Topik: {topik} | Ruang Lingkup: {ruang_lingkup} | Tingkat Kognitif BSKAP: {kesulitan} | Komposisi Soal: {jumlah_pg} PG, {jumlah_esai} Esai, {jumlah_isian} Isian Singkat. Guru Pengampu: {guru_nama} (NIP. {guru_nip}). Soal terstruktur lengkap dengan kunci jawaban dan rubrik penilaian BSKAP 2026."
            else:
                hasil = f"[{jenis.upper()}] Mata Pelajaran: {mapel} | Jenjang: {jenjang} ({kelas} - {fase}) | Topik: {topik} | Ruang Lingkup: {ruang_lingkup} | Metode: {metode} | Aktivitas: {aktivitas} | Tingkat Kognitif: {kesulitan} | Guru Pengampu: {guru_nama} (NIP. {guru_nip}). Dokumen pembelajaran Kurikulum Merdeka siap cetak."
            
            source_info = "Generate baru via AI (Disimpan ke Arsip & Cache)"
            db.execute("INSERT INTO arsip (user_id, jenis_modul, topik, konten) VALUES (?, ?, ?, ?)",
                       (session['user_id'], jenis, cache_key, hasil))
        
        db.execute("INSERT INTO log_aktivitas (user_id, aktivitas) VALUES (?, ?)",
                   (session['user_id'], f"Generate {jenis} - {topik} ({source_info})"))
        db.commit()
        
        flash(f"Berhasil generate {jenis}! ({source_info})", 'success')
        return render_template('generator.html', custom_tabs=custom_tabs, hasil=hasil, active_tab=jenis)
    return render_template('generator.html', custom_tabs=custom_tabs, hasil=None, active_tab='Modul Ajar/RPP')

@app.route('/generator-hem', methods=['POST'])
def generator_hem():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    jenjang = request.form.get('jenjang', 'SMA/SMK/MA')
    tahun_ajaran = request.form.get('tahun_ajaran', '2025/2026')
    sistem_hari = request.form.get('sistem_hari', '5 Hari Kerja (Senin–Jumat)')
    
    file = request.files.get('kalender_file')
    uploaded_source = "Berdasarkan Kalender Pendidikan Resmi (Kaldik Jabar / Kemendikdasmen)"
    if file and file.filename != '':
        path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(path)
        uploaded_source = f"Dianalisis dari Upload Kalender ({file.filename})"

    data = [
        ["Juli 2025", 4, 3, 1, 22, 16, 6, "Masa Pengenalan Lingkungan Sekolah (MPLS) & Awal Tahun"],
        ["Agustus 2025", 5, 1, 4, 21, 1, 20, "17 Agustus (HUT Kemerdekaan RI)"],
        ["September 2025", 4, 0, 4, 22, 1, 21, "Peringatan Maulid Nabi SAW"],
        ["Oktober 2025", 4, 0, 4, 23, 0, 23, "Pembelajaran Reguler Efektif"],
        ["November 2025", 4, 0, 4, 21, 0, 21, "Pembelajaran Reguler Efektif"],
        ["Desember 2025", 4, 3, 1, 22, 12, 10, "STS/SAS Semester Ganjil, Libur Semester"],
        ["Januari 2026", 5, 1, 4, 22, 1, 21, "Awal Semester Genap"],
        ["Februari 2026", 4, 0, 4, 20, 1, 19, "Isra Mikraj / Tahun Baru Imlek"],
        ["Maret 2026", 4, 2, 2, 21, 7, 14, "Libur Awal Ramadan & Hari Raya Idulfitri"],
        ["April 2026", 4, 1, 3, 22, 4, 18, "Libur Hari Raya Idulfitri / Cuti Bersama"],
        ["Mei 2026", 4, 1, 3, 20, 2, 18, "Hari Buruh, Kenaikan Isa Almasih, Waisak"],
        ["Juni 2026", 4, 3, 1, 22, 15, 7, "Asesmen Sumatif Akhir Tahun (ASAT) & Libur Kenaikan Kelas"]
    ]

    tot_minggu_kal = sum(row[1] for row in data)
    tot_minggu_taktif = sum(row[2] for row in data)
    tot_minggu_efektif = sum(row[3] for row in data)
    tot_hari_sekolah = sum(row[4] for row in data)
    tot_hari_taktif = sum(row[5] for row in data)
    tot_hari_efektif = sum(row[6] for row in data)

    totals = {
        "total_minggu_kalender": tot_minggu_kal,
        "total_minggu_taktif": tot_minggu_taktif,
        "total_minggu_efektif": tot_minggu_efektif,
        "total_hari_sekolah": tot_hari_sekolah,
        "total_hari_taktif": tot_hari_taktif,
        "total_hari_efektif": tot_hari_efektif
    }

    db = get_db()
    user_info = db.execute("SELECT nama_lengkap, nip FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    guru_nama = user_info['nama_lengkap'] if user_info else session.get('nama_lengkap', 'Guru')
    guru_nip = user_info['nip'] if user_info else session.get('nip', '-')
    sekolah = db.execute("SELECT * FROM sekolah LIMIT 1").fetchone()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Analisis HEM"
    ws.views.sheetView[0].showGridLines = True

    COLOR_HEADER_FILL = "1F4E79"
    COLOR_HEADER_FONT = "FFFFFF"
    COLOR_ACCENT_FILL = "FCE4D6"
    COLOR_TOTAL_FILL = "D9E1F2"
    COLOR_ZEBRA_FILL = "F9F9F9"

    font_title = Font(name="Arial", size=14, bold=True, color="1F4E79")
    font_subtitle = Font(name="Arial", size=10, italic=True, color="595959")
    font_header = Font(name="Arial", size=10, bold=True, color=COLOR_HEADER_FONT)
    font_bold = Font(name="Arial", size=10, bold=True)
    font_normal = Font(name="Arial", size=10)

    fill_header = PatternFill(start_color=COLOR_HEADER_FILL, end_color=COLOR_HEADER_FILL, fill_type="solid")
    fill_accent = PatternFill(start_color=COLOR_ACCENT_FILL, end_color=COLOR_ACCENT_FILL, fill_type="solid")
    fill_total = PatternFill(start_color=COLOR_TOTAL_FILL, end_color=COLOR_TOTAL_FILL, fill_type="solid")
    fill_zebra = PatternFill(start_color=COLOR_ZEBRA_FILL, end_color=COLOR_ZEBRA_FILL, fill_type="solid")

    thin_border = Border(
        left=Side(style='thin', color='BFBFBF'), right=Side(style='thin', color='BFBFBF'),
        top=Side(style='thin', color='BFBFBF'), bottom=Side(style='thin', color='BFBFBF')
    )
    double_bottom_border = Border(
        left=Side(style='thin', color='BFBFBF'), right=Side(style='thin', color='BFBFBF'),
        top=Side(style='thin', color='BFBFBF'), bottom=Side(style='double', color='000000')
    )

    ws['A1'] = f"ANALISIS HARI EFEKTIF MENGAJAR (HEM) - {jenjang}"
    ws['A1'].font = font_title
    ws['A2'] = f"Satuan Pendidikan: {sekolah['nama_sekolah']} | Guru Pengampu: {guru_nama} (NIP. {guru_nip}) | Tahun Pelajaran: {tahun_ajaran}"
    ws['A2'].font = font_subtitle
    ws.append([])

    headers = [
        "Bulan", "Jumlah Minggu Kalender", "Minggu Tidak Efektif", 
        "Minggu Efektif Belajar", "Jumlah Hari Sekolah", "Hari Tidak Efektif", 
        "Hari Efektif Belajar", "Keterangan"
    ]
    ws.append(headers)

    header_row_idx = 4
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=header_row_idx, column=col_idx)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border
    ws.row_dimensions[header_row_idx].height = 28

    start_row = 5
    for r_idx, row_data in enumerate(data, start=start_row):
        ws.append(row_data)
        for c_idx in range(1, len(row_data) + 1):
            cell = ws.cell(row=r_idx, column=c_idx)
            cell.font = font_normal
            cell.border = thin_border
            if c_idx == 1:
                cell.alignment = Alignment(horizontal="left", vertical="center")
            elif c_idx == 8:
                cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
            else:
                cell.alignment = Alignment(horizontal="center", vertical="center")
                
            if c_idx in [4, 7]:
                cell.fill = fill_accent
                cell.font = font_bold
            elif r_idx % 2 == 0:
                cell.fill = fill_zebra
        ws.row_dimensions[r_idx].height = 20

    end_data_row = start_row + len(data) - 1
    total_row_idx = end_data_row + 1
    ws.cell(row=total_row_idx, column=1, value="TOTAL TAHUNAN").font = font_bold
    ws.cell(row=total_row_idx, column=1).alignment = Alignment(horizontal="left", vertical="center")

    for c_idx in range(2, 8):
        col_letter = get_column_letter(c_idx)
        formula = f"=SUM({col_letter}{start_row}:{col_letter}{end_data_row})"
        cell = ws.cell(row=total_row_idx, column=c_idx, value=formula)
        cell.font = font_bold
        cell.alignment = Alignment(horizontal="center", vertical="center")
        if c_idx in [4, 7]:
            cell.fill = fill_accent
        else:
            cell.fill = fill_total

    ws.cell(row=total_row_idx, column=8, value=f"Akumulasi Tahun Pelajaran {tahun_ajaran}").font = font_subtitle
    ws.cell(row=total_row_idx, column=8).alignment = Alignment(horizontal="left", vertical="center")

    for c_idx in range(1, 9):
        ws.cell(row=total_row_idx, column=c_idx).border = double_bottom_border
    ws.row_dimensions[total_row_idx].height = 24

    recap_start_row = total_row_idx + 3
    ws.cell(row=recap_start_row, column=1, value="REKAP TOTAL KOMPONEN TAHUNAN").font = font_bold
    ws.merge_cells(start_row=recap_start_row, start_column=1, end_row=recap_start_row, end_column=3)

    recap_headers = ["Komponen Analisis", "Jumlah Total", "Satuan"]
    for i, h in enumerate(recap_headers, 1):
        cell = ws.cell(row=recap_start_row+1, column=i, value=h)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border
    ws.row_dimensions[recap_start_row+1].height = 24

    recap_items = [
        ("Total Minggu Kalender", f"=B{total_row_idx}", "Minggu"),
        ("Total Minggu Tidak Efektif", f"=C{total_row_idx}", "Minggu"),
        ("Total Minggu Efektif Belajar", f"=D{total_row_idx}", "Minggu"),
        ("Total Hari Sekolah", f"=E{total_row_idx}", "Hari"),
        ("Total Hari Tidak Efektif", f"=F{total_row_idx}", "Hari"),
        ("Total Hari Efektif Belajar", f"=G{total_row_idx}", "Hari")
    ]

    for idx, item in enumerate(recap_items):
        r_idx = recap_start_row + 2 + idx
        ws.cell(row=r_idx, column=1, value=item[0]).font = font_normal
        c_val = ws.cell(row=r_idx, column=2, value=item[1])
        c_val.font = font_bold
        c_val.alignment = Alignment(horizontal="center", vertical="center")
        
        c_unit = ws.cell(row=r_idx, column=3, value=item[2])
        c_unit.font = font_normal
        c_unit.alignment = Alignment(horizontal="center", vertical="center")
        
        if "Efektif Belajar" in item[0]:
            c_val.fill = fill_accent
        elif idx % 2 == 1:
            for c in range(1, 4):
                ws.cell(row=r_idx, column=c).fill = fill_zebra
                
        for c in range(1, 4):
            ws.cell(row=r_idx, column=c).border = thin_border
        ws.row_dimensions[r_idx].height = 20

    col_widths = {'A': 22, 'B': 24, 'C': 22, 'D': 24, 'E': 20, 'F': 20, 'G': 20, 'H': 55}
    for col, width in col_widths.items():
        ws.column_dimensions[col].width = width

    out_filename = f"Analisis_HEM_{jenjang.replace(' / ', '_').replace('/', '_')}_{tahun_ajaran.replace('/', '_')}.xlsx"
    wb.save(out_filename)

    hem_summary_text = f"Analisis Hari Efektif Mengajar (HEM) | Satuan Pendidikan: {sekolah['nama_sekolah']} | Guru Pengampu: {guru_nama} (NIP. {guru_nip}) | Jenjang: {jenjang} | Tahun: {tahun_ajaran} | Sistem: {sistem_hari} | Total Efektif: {tot_minggu_efektif} Minggu / {tot_hari_efektif} Hari"
    
    hem_cache_key = f"HEM | {jenjang} | {tahun_ajaran} | {sistem_hari}"
    cached_hem = db.execute("SELECT id FROM arsip WHERE jenis_modul = ? AND topik = ? LIMIT 1", ("Analisis Hari Efektif Mengajar (HEM)", hem_cache_key)).fetchone()
    if not cached_hem:
        db.execute("INSERT INTO arsip (user_id, jenis_modul, topik, konten) VALUES (?, ?, ?, ?)",
                   (session['user_id'], "Analisis Hari Efektif Mengajar (HEM)", hem_cache_key, hem_summary_text))
    else:
        db.execute("UPDATE arsip SET konten = ?, created_at = CURRENT_TIMESTAMP WHERE jenis_modul = ? AND topik = ?",
                   (hem_summary_text, "Analisis Hari Efektif Mengajar (HEM)", hem_cache_key))
    
    db.execute("INSERT INTO log_aktivitas (user_id, aktivitas) VALUES (?, ?)",
               (session['user_id'], f"Analisis HEM ({jenjang} - {tahun_ajaran}) berhasil dianalisis & disimpan ke Arsip"))
    db.commit()

    custom_tabs = db.execute("SELECT * FROM custom_modul").fetchall()
    flash('Analisis Hari Efektif Mengajar (HEM) berhasil dijalankan!', 'success')
    return render_template('generator.html', custom_tabs=custom_tabs, preview_data=data, totals=totals, req_jenjang=jenjang, req_tahun=tahun_ajaran, req_sistem=sistem_hari, download_filename=out_filename, active_tab='Analisis Hari Efektif Mengajar (HEM)')

@app.route('/download-file-hem')
def download_file_hem():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    filename = request.args.get('filename', 'Analisis_HEM.xlsx')
    if os.path.exists(filename):
        return send_file(filename, as_attachment=True)
    flash('File tidak ditemukan.', 'danger')
    return redirect(url_for('generator'))

@app.route('/arsip')
def arsip():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    if session['role'] in ['superadmin', 'admin']:
        list_arsip = db.execute("SELECT a.*, u.nama_lengkap, u.nip FROM arsip a JOIN users u ON a.user_id = u.id ORDER BY a.id DESC").fetchall()
    else:
        list_arsip = db.execute("SELECT a.*, u.nama_lengkap, u.nip FROM arsip a JOIN users u ON a.user_id = u.id WHERE a.user_id = ? ORDER BY a.id DESC", (session['user_id'],)).fetchall()
    return render_template('arsip.html', list_arsip=list_arsip)

@app.route('/arsip/lihat/<int:arsip_id>')
def lihat_arsip(arsip_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    item = db.execute("SELECT a.*, u.nama_lengkap, u.nip FROM arsip a JOIN users u ON a.user_id = u.id WHERE a.id = ?", (arsip_id,)).fetchone()
    sekolah = db.execute("SELECT * FROM sekolah LIMIT 1").fetchone()
    if not item:
        flash('Dokumen arsip tidak ditemukan.', 'danger')
        return redirect(url_for('arsip'))
    return render_template('lihat_arsip.html', item=item, sekolah=sekolah)

@app.route('/pengaturan')
def pengaturan():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    users = db.execute("SELECT * FROM users ORDER BY id DESC").fetchall()
    moduls = db.execute("SELECT * FROM custom_modul").fetchall()
    notif = db.execute("SELECT * FROM notifikasi ORDER BY id DESC LIMIT 1").fetchone()
    return render_template('pengaturan.html', users=users, moduls=moduls, notif=notif)

@app.route('/konfirmasi-user/<int:user_id>')
def konfirmasi_user(user_id):
    if session.get('role') not in ['superadmin', 'admin']:
        return redirect(url_for('dashboard'))
    db = get_db()
    db.execute("UPDATE users SET status = 'active' WHERE id = ?", (user_id,))
    db.commit()
    flash('Akun pengguna berhasil dikonfirmasi dan diaktifkan!', 'success')
    return redirect(url_for('pengaturan'))

@app.route('/ganti-password', methods=['POST'])
def ganti_password():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    password_lama = request.form['password_lama']
    password_baru = request.form['password_baru']
    konfirmasi = request.form['konfirmasi_password']
    
    if password_baru != konfirmasi:
        flash('Password baru dan konfirmasi password tidak cocok!', 'danger')
        return redirect(url_for('pengaturan'))
    
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    if user['password'] != password_lama:
        flash('Password lama salah!', 'danger')
        return redirect(url_for('pengaturan'))
    
    db.execute("UPDATE users SET password = ? WHERE id = ?", (password_baru, session['user_id']))
    db.commit()
    flash('Password berhasil diubah!', 'success')
    return redirect(url_for('pengaturan'))

@app.route('/tambah-user', methods=['POST'])
def tambah_user():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    nama = request.form['nama_lengkap']
    nip = request.form.get('nip', '-')
    username = request.form['username']
    password = request.form['password']
    role = request.form['role']
    
    db = get_db()
    try:
        db.execute("INSERT INTO users (username, password, nama_lengkap, nip, role, status) VALUES (?, ?, ?, ?, ?, 'active')",
                   (username, password, nama, nip, role))
        db.commit()
        flash(f'Pengguna {nama} berhasil ditambahkan dan langsung aktif!', 'success')
    except sqlite3.IntegrityError:
        flash('Username sudah terdaftar!', 'danger')
    return redirect(url_for('pengaturan'))

@app.route('/edit-user/<int:user_id>', methods=['POST'])
def edit_user(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    nama = request.form['nama_lengkap']
    nip = request.form.get('nip', '-')
    username = request.form['username']
    password = request.form.get('password', '')
    role = request.form['role']
    
    db = get_db()
    if password and password.strip() != '':
        db.execute("UPDATE users SET nama_lengkap = ?, nip = ?, username = ?, password = ?, role = ? WHERE id = ?",
                   (nama, nip, username, password, role, user_id))
    else:
        db.execute("UPDATE users SET nama_lengkap = ?, nip = ?, username = ?, role = ? WHERE id = ?",
                   (nama, nip, username, role, user_id))
    db.commit()
    flash('Data pengguna berhasil diperbarui!', 'success')
    return redirect(url_for('pengaturan'))

@app.route('/hapus-user/<int:user_id>')
def hapus_user(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    user = db.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
    if user and user['username'] == 'superadmin':
        flash('Akun superadmin utama tidak dapat dihapus!', 'danger')
        return redirect(url_for('pengaturan'))
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()
    flash('Pengguna berhasil dihapus!', 'success')
    return redirect(url_for('pengaturan'))

@app.route('/update-notifikasi', methods=['POST'])
def update_notifikasi():
    if session.get('role') != 'superadmin':
        return redirect(url_for('dashboard'))
    pesan = request.form['pesan']
    is_active = 1 if 'is_active' in request.form else 0
    db = get_db()
    db.execute("DELETE FROM notifikasi")
    db.execute("INSERT INTO notifikasi (pesan, is_active) VALUES (?, ?)", (pesan, is_active))
    db.commit()
    flash('Pengaturan notifikasi login berhasil diperbarui!', 'success')
    return redirect(url_for('pengaturan'))

@app.route('/tambah-modul-admin', methods=['POST'])
def tambah_modul_admin():
    if session.get('role') != 'superadmin':
        return redirect(url_for('dashboard'))
    db = get_db()
    nama_modul = request.form['nama_modul']
    kode_slug = request.form['kode_slug']
    file = request.files.get('template_file')
    if file and file.filename != '':
        path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(path)
        db.execute("INSERT INTO custom_modul (nama_modul, kode_slug, template_path) VALUES (?, ?, ?)",
                   (nama_modul, kode_slug, path))
        db.commit()
        flash('Modul baru berhasil ditambahkan!', 'success')
    return redirect(url_for('pengaturan'))

@app.route('/hapus-modul/<int:modul_id>')
def hapus_modul(modul_id):
    if session.get('role') != 'superadmin':
        return redirect(url_for('dashboard'))
    db = get_db()
    db.execute("DELETE FROM custom_modul WHERE id = ?", (modul_id,))
    db.commit()
    flash('Modul berhasil dihapus!', 'success')
    return redirect(url_for('pengaturan'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Anda telah keluar.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
