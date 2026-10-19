import os
import hashlib
import uuid
import sqlite3
import pandas as pd
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request, flash, send_file, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import db, User, SchoolProfile, Teacher, Student, Archive, ActivityLog, Announcement, CustomModule, wib_now

app = Flask(__name__)
app.config['SECRET_KEY'] = 'siap_administrasi_guru_2026_secret_key'
database_url = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')
if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif database_url.startswith("postgresql://") and "+psycopg2" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    if "sslmode" not in database_url and "neon.tech" in database_url:
        separator = "&" if "?" in database_url else "?"
        database_url = database_url + separator + "sslmode=require"
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    if os.environ.get('VERCEL') or not os.access(os.path.dirname(__file__) or '.', os.W_OK):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/database.db'
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

if os.environ.get('VERCEL') or not os.access(os.path.dirname(__file__) or '.', os.W_OK):
    app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
    app.instance_path = '/tmp'
else:
    app.config['UPLOAD_FOLDER'] = 'uploads'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

try:
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
except Exception as e:
    print("Upload folder creation notice:", e)

try:
    os.makedirs(app.instance_path, exist_ok=True)
except Exception as e:
    print("Instance folder creation notice:", e)

db.init_app(app)

with app.app_context():
    try:
        db.create_all()
        defaults = [
            ('Analisis Hari Efektif Mengajar (HEM)', 'hem'),
            ('CP-TP-ATP', 'cp_tp_atp'),
            ('Modul Ajar / RPP', 'modul_ajar'),
            ('LKPD Siswa', 'lkpd'),
            ('Program Semester (Prosem)', 'prosem'),
            ('Program Tahunan (Prota)', 'prota'),
            ('Bank Soal Harian', 'soal_harian'),
            ('Bank Soal STS (Sumatif Tengah Semester)', 'soal_sts'),
            ('Bank Soal SAS (Sumatif Akhir Semester)', 'soal_sas'),
            ('Asesmen Sumatif', 'asesmen_sumatif')
        ]
        for d_name, d_slug in defaults:
            existing = CustomModule.query.filter_by(slug=d_slug).first()
            if not existing:
                cm = CustomModule(nama_modul=d_name, slug=d_slug, aktif=True, is_default=True)
                db.session.add(cm)
        db.session.commit()

        if not User.query.filter_by(username='superadmin').first():
            sa = User(
                username='superadmin',
                email='superadmin@admin.com',
                nip='198001012010011001',
                mapel='Administrator',
                password=generate_password_hash('superadmin123'),
                nama_lengkap='Super Administrator',
                role='superadmin',
                status='active'
            )
            db.session.add(sa)
            db.session.commit()
    except Exception as e:
        print("Init DB error:", e)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def log_activity(user_id, aktivitas):
    try:
        log = ActivityLog(user_id=user_id, aktivitas=aktivitas)
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print("Log error:", e)

@app.before_request
def check_single_device():
    if current_user.is_authenticated:
        if not session.get('device_session_id'):
            session['device_session_id'] = current_user.current_session_id
        elif current_user.current_session_id and current_user.current_session_id != session.get('device_session_id'):
            logout_user()
            flash('Akun Anda telah login di perangkat lain. Sesi ini diakhiri.', 'danger')
            return redirect(url_for('login'))

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            if user.status != 'active':
                flash('Akun Anda belum diaktifkan oleh Admin. Silakan konfirmasi via WhatsApp ke 081321984848.', 'warning')
                return redirect(url_for('login'))
            
            device_session_id = str(uuid.uuid4())
            session['device_session_id'] = device_session_id
            user.current_session_id = device_session_id
            db.session.commit()
            
            login_user(user)
            log_activity(user.id, "Login ke sistem dari perangkat baru.")
            flash(f'Selamat datang kembali, {user.nama_lengkap}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Username atau password salah.', 'danger')
    return render_template('login.html', wa_number='081321984848')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        nama_lengkap = request.form.get('nama_lengkap')
        email = request.form.get('email', '')
        nip = request.form.get('nip', '')
        mapel = request.form.get('mapel', '')
        
        if User.query.filter_by(username=username).first():
            flash('Username sudah terdaftar.', 'danger')
            return redirect(url_for('register'))
            
        hashed_password = generate_password_hash(password)
        new_user = User(
            username=username,
            email=email,
            nip=nip,
            mapel=mapel,
            password=hashed_password,
            nama_lengkap=nama_lengkap,
            role='guru',
            status='pending'
        )
        db.session.add(new_user)
        db.session.commit()
        
        wa_url = "https://wa.me/6281321984848?text=Halo%20Admin,%20saya%20telah%20mendaftar%20akun%20guru%20dengan%20nama%20%3A%20" + nama_lengkap + "%20(%username%3A%20" + username + ").%20Mohon%20aktivasi%20akun%20saya."
        return render_template('register_success.html', wa_url=wa_url)
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    log_activity(current_user.id, "Logout dari sistem.")
    logout_user()
    session.pop('device_session_id', None)
    flash('Anda telah berhasil logout.', 'info')
    return """
    <html>
    <head><title>Logging out...</title></head>
    <body style="background:#f8f9fa; display:flex; justify-content:center; align-items:center; height:100vh; font-family:sans-serif;">
    <div style="text-align:center;">
        <h4>Mengakhiri Sesi...</h4>
        <p class="text-muted">Sedang memutuskan koneksi dari Puter.js dan Gurava.</p>
    </div>
    <script src="https://js.puter.com/v2/"></script>
    <script>
        document.addEventListener("DOMContentLoaded", function() {
            if (typeof puter !== 'undefined' && puter.auth.isSignedIn()) {
                puter.auth.signOut();
            }
            setTimeout(() => { window.location.href = '/login'; }, 500);
        });
    </script>
    </body>
    </html>
    """

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    profile = SchoolProfile.query.first()
    if not profile:
        profile = SchoolProfile()
        db.session.add(profile)
        db.session.commit()
        
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        if form_type == 'school_profile':
            profile.nama_sekolah = request.form.get('nama_sekolah')
            profile.alamat = request.form.get('alamat')
            profile.nama_kepsek = request.form.get('nama_kepsek')
            profile.nip_kepsek = request.form.get('nip_kepsek')
            
            file = request.files.get('kop_image')
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                profile.kop_sekolah = filename
                
            db.session.commit()
            log_activity(current_user.id, "Memperbarui Profil Sekolah & Kop Surat.")
            flash('Profil sekolah dan kop surat berhasil diperbarui.', 'success')
        elif form_type == 'user_profile':
            current_user.nama_lengkap = request.form.get('nama_lengkap')
            current_user.nip = request.form.get('nip')
            current_user.email = request.form.get('email')
            current_user.mapel = request.form.get('mapel')
            db.session.commit()
            log_activity(current_user.id, "Memperbarui Identitas Akun Penyusun Dokumen.")
            flash('Identitas akun penyusun berhasil diperbarui.', 'success')
        return redirect(url_for('dashboard'))
        
    user_logs = ActivityLog.query.filter_by(user_id=current_user.id).order_by(ActivityLog.timestamp.desc()).limit(5).all()
    announcement = Announcement.query.filter_by(aktif=True).order_by(Announcement.id.desc()).first()
    
    return render_template('dashboard.html', profile=profile, user_logs=user_logs, announcement=announcement)

@app.route('/generator/<modul_slug>', methods=['GET', 'POST'])
@login_required
def generator(modul_slug):
    all_modules = CustomModule.query.filter_by(aktif=True).all()
    hasil_generate = None
    
    mod_obj = CustomModule.query.filter_by(slug=modul_slug, aktif=True).first()
    if not mod_obj:
        flash('Modul tidak ditemukan atau sedang dinonaktifkan (gangguan/maintenance).', 'danger')
        first_mod = CustomModule.query.filter_by(aktif=True).first()
        if first_mod:
            return redirect(url_for('generator', modul_slug=first_mod.slug))
        else:
            flash('Tidak ada modul aktif saat ini.', 'danger')
            return redirect(url_for('dashboard'))
            
    jenis = mod_obj.nama_modul
    profile = SchoolProfile.query.first()

    if modul_slug == 'hem':
        saved_hem = Archive.query.filter_by(user_id=current_user.id, jenis_administrasi=jenis).order_by(Archive.created_at.desc()).first()
        if saved_hem:
            hasil_generate = saved_hem.hasil_konten

    if request.method == 'POST':
        try:
            if modul_slug == 'hem':
                return redirect(url_for('generator', modul_slug='hem'))
            
            jenjang = request.form.get('jenjang', 'SMP / MTs')
            kelas_fase_val = request.form.get('kelas_fase', 'Kelas 7 | Fase D (Kelas 7-9)')
            parts = kelas_fase_val.split('|')
            kelas = parts[0].strip() if len(parts) > 0 else 'Kelas 7'
            fase = parts[1].strip() if len(parts) > 1 else 'Fase D (Kelas 7-9)'

            kurikulum = request.form.get('kurikulum', 'Kurikulum Merdeka (Kumer)')
            mapel = request.form.get('mapel', 'Pendidikan Agama Islam dan Budi Pekerti')
            metode = request.form.get('metode', 'Project Based Learning (PjBL)')
            aktivitas = request.form.get('aktivitas', 'Pembelajaran Berbasis Inkuiri')
            kesulitan = request.form.get('kesulitan', 'C3')
            jml_pg = request.form.get('jml_pg', '10')
            jml_esai = request.form.get('jml_esai', '5')
            jml_isian = request.form.get('jml_isian', '5')
            topik = request.form.get('topik', 'Materi Pembelajaran')
            ruang_lingkup = request.form.get('ruang_lingkup', 'Sub-Materi Utama')
            
            param_str = f"AIV3-{jenis}-{jenjang}-{kelas}-{fase}-{kurikulum}-{mapel}-{topik}-{ruang_lingkup}-{kesulitan}-{current_user.id}"
            param_hash = hashlib.md5(param_str.encode('utf-8')).hexdigest()
            
            cached = Archive.query.filter_by(parameter_hash=param_hash).first()
            if cached:
                hasil_generate = cached.hasil_konten
                log_activity(current_user.id, f"Mengambil Arsip Cache untuk {jenis}: {topik}")
                flash('Hasil diambil dari Cache Arsip (Menghemat Token API).', 'info')
            else:
                kop_html = ""
                if profile and profile.kop_sekolah:
                    kop_html = f"<div class='text-center mb-3'><img src='{url_for('uploaded_file', filename=profile.kop_sekolah)}' style='max-width:100%; height:auto; max-height:140px;' alt='Kop Surat'></div><hr style='border: 2px solid #333;'>"
                else:
                    kop_html = f"<div class='text-center mb-3'><h3>{profile.nama_sekolah if profile else 'SEMENCA'}</h3><p>{profile.alamat if profile else ''}</p></div><hr style='border: 2px solid #333;'>"

                guru_nip = current_user.nip if current_user.nip else '-'
                guru_email = current_user.email if current_user.email else '-'
                guru_mapel = current_user.mapel if current_user.mapel else (mapel if mapel else '-')

                hem_saved = Archive.query.filter_by(user_id=current_user.id, jenis_administrasi="Analisis Hari Efektif Mengajar (HEM)").order_by(Archive.created_at.desc()).first()
                sem1_jp = "48"
                sem2_jp = "48"
                sem1_minggu = "16"
                sem2_minggu = "16"
                jp_per_mgg = "3"

                if modul_slug in ['soal_harian', 'soal_sts', 'soal_sas', 'asesmen_sumatif']:
                    try:
                        total_soal = int(jml_pg) + int(jml_isian) + int(jml_esai)
                    except:
                        total_soal = 20
                        
                    prompt_ai = f"""Bertindaklah sebagai guru ahli pembuat instrumen evaluasi. Buatkan soal untuk parameter berikut:
Mata Pelajaran: {mapel}
Materi/Topik: {topik}
Ruang Lingkup: {ruang_lingkup}
Jenjang: {jenjang} ({kelas} / {fase})
Kurikulum: {kurikulum}
Level Kognitif: {kesulitan}
Jumlah Soal PG: {jml_pg}
Jumlah Soal Isian Singkat: {jml_isian}
Jumlah Soal Esai: {jml_esai}
Total Keseluruhan Soal: {total_soal} soal

PENTING: Pada bagian "III. KISI-KISI PENULISAN SOAL", Anda WAJIB membuat baris tabel (<tr>) SEBANYAK TOTAL KESELURUHAN SOAL ({total_soal} baris). Setiap soal yang dibuat di bagian naskah soal harus ada pemetaan kisi-kisinya di tabel ini.

Keluarkan HANYA HTML MURNI (tanpa format markdown ```html, jangan gunakan tag body/html). 
Gunakan struktur persis seperti ini:
<div class='mb-1 text-center fs-5'><b>PERANGKAT EVALUASI PEMBELAJARAN</b></div>
<div class='mb-4 text-center text-muted small'>Mata Pelajaran: {mapel} | Materi: {topik} | Jenjang: {jenjang} ({kelas})</div>
<div class='fw-bold mt-2 mb-2 bg-light p-2 border-start border-4 border-primary'>I. NASKAH SOAL EVALUASI</div>
<div class='fw-bold mt-3'>A. PILIHAN GANDA</div>
<div class='ps-2 mb-3'>
  <b>1.</b> [Soal PG 1 yang spesifik dan menantang]<br>
  &nbsp;&nbsp;&nbsp;&nbsp;A. [Opsi]<br>
  &nbsp;&nbsp;&nbsp;&nbsp;B. [Opsi]<br>
  &nbsp;&nbsp;&nbsp;&nbsp;C. [Opsi]<br>
  &nbsp;&nbsp;&nbsp;&nbsp;D. [Opsi]<br><br>
</div>
<div class='fw-bold mt-3'>B. ISIAN SINGKAT</div>
<div class='ps-2 mb-3'>
  <b>1.</b> [Soal Isian 1 yang spesifik] ....................<br><br>
</div>
<div class='fw-bold mt-3'>C. ESAI / URAIAN</div>
<div class='ps-2 mb-4'>
  <b>1.</b> [Soal Esai 1 yang menuntut analisis]<br><br>
</div>
<div class='fw-bold mt-4 mb-2 bg-light p-2 border-start border-4 border-success'>II. KUNCI JAWABAN DAN PEMBAHASAN</div>
<div class='fw-bold mt-3'>A. KUNCI PILIHAN GANDA</div>
<div class='ps-2 mb-3'><b>1.</b> [Kunci] — <i>Pembahasan:</i> [Penjelasan singkat]<br></div>
<div class='fw-bold mt-3'>B. KUNCI ISIAN SINGKAT</div>
<div class='ps-2 mb-3'><b>1.</b> [Jawaban]<br></div>
<div class='fw-bold mt-3'>C. KUNCI ESAI</div>
<div class='ps-2 mb-4'><b>1.</b> <i>Rubrik:</i> [Kriteria jawaban benar]<br></div>
<div class='fw-bold mt-4 mb-2 bg-light p-2 border-start border-4 border-warning'>III. KISI-KISI PENULISAN SOAL</div>
<div class='table-responsive mt-2'>
<table class='table table-bordered align-middle'>
<thead class='table-light text-center'><tr><th>No</th><th>CP / TP</th><th>Materi</th><th>Indikator Soal</th><th>Bentuk Soal</th><th>Level</th></tr></thead>
<tbody>
<tr><td class='text-center'>1</td><td>[Tujuan Pembelajaran]</td><td>{topik}</td><td>[Indikator Soal PG 1]</td><td>PG</td><td class='text-center'>{kesulitan}</td></tr>
<!-- LANJUTKAN MEMBUAT BARIS (<tr>) UNTUK SEMUA SOAL PG, LALU SEMUA SOAL ISIAN, LALU SEMUA SOAL ESAI. PASTIKAN JUMLAH BARIS SAMA PERSIS DENGAN TOTAL SOAL ({total_soal} BARIS). -->
</tbody>
</table>
</div>
"""
                elif modul_slug == 'cp_tp_atp':
                    prompt_ai = f"""Bertindaklah sebagai guru ahli pembuat dokumen administrasi. Buatkan dokumen CP, TP, dan ATP untuk parameter berikut:
Mata Pelajaran: {mapel}
Materi/Topik: {topik}
Ruang Lingkup: {ruang_lingkup}
Jenjang: {jenjang} ({kelas} / {fase})
Kurikulum: {kurikulum}
Pendekatan/Metode: {metode}
Aktivitas: {aktivitas}

Keluarkan HANYA HTML MURNI tanpa markdown ```html, tanpa tag html/body.
Gunakan format tabel dan struktur yang rapi (mirip dokumen resmi):
<h3 class='text-center'>PEMETAAN CAPAIAN PEMBELAJARAN (CP), TUJUAN PEMBELAJARAN (TP)<br>DAN ALUR TUJUAN PEMBELAJARAN (ATP)</h3>
<hr>
<table class='table table-bordered mb-4'>
<tr><th style='width: 25%'>Mata Pelajaran</th><td>{mapel}</td></tr>
<tr><th>Kelas / Fase</th><td>{kelas} / {fase}</td></tr>
<tr><th>Tahun Pelajaran</th><td>2025/2026</td></tr>
</table>
<h4 class='text-primary mt-4'>I. CAPAIAN PEMBELAJARAN (CP) - FASE {fase.split(' ')[0]}</h4>
[Buat tabel Elemen dan Capaian Pembelajaran secara mendalam terkait {topik}]
<h4 class='text-primary mt-4'>II. TUJUAN PEMBELAJARAN (TP) DAN ALUR TUJUAN PEMBELAJARAN (ATP)</h4>
[Buat tabel dengan kolom No, Elemen, Materi/Bab, Tujuan Pembelajaran (TP), Alur Tujuan Pembelajaran (ATP), dan Justifikasi]
"""
                else:
                    prompt_ai = f"""Bertindaklah sebagai guru ahli. Buatkan dokumen administrasi {jenis} untuk parameter berikut:
Mata Pelajaran: {mapel}
Materi/Topik: {topik}
Ruang Lingkup: {ruang_lingkup}
Jenjang: {jenjang} ({kelas} / {fase})
Kurikulum: {kurikulum}
Metode: {metode}
Aktivitas: {aktivitas}

Keluarkan HANYA HTML MURNI tanpa markdown ```html, tanpa tag body/html.
Format dokumen semenarik dan serapi mungkin menyerupai dokumen administrasi guru profesional menggunakan Bootstrap classes jika perlu (table-bordered, dll).
Beri judul dokumen <h3>{jenis.upper()}</h3>
Isi semua bagian dengan konten akademis yang panjang, mendalam, dan spesifik sesuai mata pelajaran {mapel}. Jangan hanya mengulang kata-kata dari prompt atau memberikan template kosong. Buat materi nyata yang siap digunakan guru di kelas untuk topik {topik} dengan ruang lingkup {ruang_lingkup}.
"""

                import urllib.request
                import json
                
                puter_key = os.environ.get("PUTER_API_KEY")
                gemini_key = os.environ.get("GEMINI_API_KEY")
                groq_key = os.environ.get("GROQ_API_KEY")
                
                ai_text = None
                error_msgs = []
                used_api = ""
                
                # 0. PUTER.JS CLIENT-SIDE (Jika berhasil di-generate via JavaScript di frontend)
                ai_generated_content = request.form.get('ai_generated_content')
                if ai_generated_content and ai_generated_content.strip():
                    ai_text = ai_generated_content
                    used_api = "Puter AI (Client-Side)"
                
                # 1. PUTER.JS / PUTER AI (OpenAI Compatible) - Backend Fallback
                if puter_key and not ai_text:
                    try:
                        url = "https://api.puter.com/puterai/openai/v1/chat/completions"
                        payload = {
                            "model": "gpt-4o-mini",
                            "messages": [{"role": "user", "content": prompt_ai}]
                        }
                        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={
                            'Content-Type': 'application/json',
                            'Authorization': f'Bearer {puter_key}'
                        })
                        with urllib.request.urlopen(req, timeout=30) as response:
                            res_json = json.loads(response.read().decode('utf-8'))
                            ai_text = res_json['choices'][0]['message']['content']
                            used_api = "Puter AI (Server-Side)"
                    except Exception as e:
                        error_msgs.append(f"Puter API Error: {str(e)}")
                        
                # 2. GEMINI AI
                if gemini_key and not ai_text:
                    try:
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
                        payload = {"contents": [{"parts": [{"text": prompt_ai}]}]}
                        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
                        with urllib.request.urlopen(req, timeout=30) as response:
                            res_json = json.loads(response.read().decode('utf-8'))
                            ai_text = res_json.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                            used_api = "Gemini AI"
                    except Exception as e:
                        error_msgs.append(f"Gemini API Error: {str(e)}")
                        
                # 3. GROQ AI
                if groq_key and not ai_text:
                    try:
                        url = "https://api.groq.com/openai/v1/chat/completions"
                        payload = {
                            "model": "llama-3.3-70b-versatile",
                            "messages": [{"role": "user", "content": prompt_ai}]
                        }
                        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={
                            'Content-Type': 'application/json',
                            'Authorization': f'Bearer {groq_key}'
                        })
                        with urllib.request.urlopen(req, timeout=30) as response:
                            res_json = json.loads(response.read().decode('utf-8'))
                            ai_text = res_json['choices'][0]['message']['content']
                            used_api = "Groq AI"
                    except Exception as e:
                        error_msgs.append(f"Groq API Error: {str(e)}")
                        
                if ai_text:
                    ai_text = ai_text.strip()
                    if ai_text.startswith("```html"): ai_text = ai_text[7:]
                    if ai_text.startswith("```"): ai_text = ai_text[3:]
                    if ai_text.endswith("```"): ai_text = ai_text[:-3]
                    
                    identitas_html = f"<div class='mb-3 p-3 bg-light border rounded small'><b>IDENTITAS PENYUSUN:</b><br>Nama: {current_user.nama_lengkap}<br>NIP: {guru_nip}<br>Mapel: {mapel}</div>"
                    kepsek_html = f"<div class='row mt-5'><div class='col-6'></div><div class='col-6 text-center'><p>Mengetahui,<br>Kepala Sekolah</p><br><br><br><b>{profile.nama_kepsek if profile else 'Kepala Sekolah'}</b><br>NIP. {profile.nip_kepsek if profile else '-'}</div></div>"
                    
                    if modul_slug in ['soal_harian', 'soal_sts', 'soal_sas', 'asesmen_sumatif']:
                        hasil_generate = kop_html + ai_text
                    else:
                        hasil_generate = kop_html + identitas_html + ai_text + kepsek_html
                        
                else:
                    # ALL FAILED OR NO KEYS
                    hasil_generate = f"{kop_html}" \
                                     f"<div class='alert alert-danger mt-4'>" \
                                     f"<h4><i class='bi bi-exclamation-triangle'></i> API Key Diperlukan atau Terjadi Kesalahan</h4>" \
                                     f"<p>Sistem mencoba menggunakan AI untuk generate modul <b>{jenis}</b>, namun tidak ada API Key yang valid atau semua API mengalami error.</p>" \
                                     f"<p><b>Log Status:</b><br>" + ("<br>".join(error_msgs) if error_msgs else "Tidak ada API Key yang diatur di Environment Variables (Vercel).") + "</p>" \
                                     f"<hr><p class='mb-0'><b>Cara memperbaiki (Tambahkan minimal satu di Vercel Env Vars):</b><br>" \
                                     f"1. <code>PUTER_API_KEY</code> (Untuk Opsi 1 - Puter.js/OpenAI)<br>" \
                                     f"2. <code>GEMINI_API_KEY</code> (Untuk Opsi 2 - Google Gemini AI)<br>" \
                                     f"3. <code>GROQ_API_KEY</code> (Untuk Opsi 3 - Groq Llama/Mixtral)<br>" \
                                     f"Lalu lakukan Redeploy.</p></div>"
                
                new_archive = Archive(
                    user_id=current_user.id,
                    jenis_administrasi=jenis,
                    topik=topik,
                    ruang_lingkup=ruang_lingkup,
                    parameter_hash=param_hash,
                    hasil_konten=hasil_generate
                )
                db.session.add(new_archive)
                db.session.commit()
                log_activity(current_user.id, f"Generate baru administrasi {jenis} ({topik}).")
                flash('Modul berhasil digenerate oleh AI dan disimpan ke arsip.', 'success')
        except Exception as e:
            db.session.rollback()
            print("Generator POST Error:", str(e))
            flash(f'Terjadi kesalahan server saat menyimpan data: {str(e)}', 'danger')
            return redirect(url_for('generator', modul_slug=modul_slug))
            
    return render_template('generator.html', all_modules=all_modules, hasil_generate=hasil_generate, active_slug=modul_slug, current_jenis=jenis)


@app.route('/api/save_hem', methods=['POST'])
@login_required
def api_save_hem():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No data'}), 400
        jumlah_jp = str(data.get('jumlah_jp', '4'))
        hari_tertentu = data.get('hari_tertentu', [])
        hasil_konten = data.get('hasil_konten', '')
        
        jenis = "Analisis Hari Efektif Mengajar (HEM)"
        param_str = f"hem-{current_user.id}-{jumlah_jp}-" + "-".join([str(h) for h in hari_tertentu])
        param_hash = hashlib.md5(param_str.encode('utf-8')).hexdigest()
        
        saved_hem = Archive.query.filter_by(user_id=current_user.id, jenis_administrasi=jenis).order_by(Archive.created_at.desc()).first()
        if saved_hem:
            saved_hem.hasil_konten = hasil_konten
            saved_hem.topik = f"Analisis HEM Semester Ganjil & Genap ({jumlah_jp} JP)"
            saved_hem.parameter_hash = param_hash
            saved_hem.created_at = wib_now()
        else:
            new_arch = Archive(
                user_id=current_user.id,
                jenis_administrasi=jenis,
                topik=f"Analisis HEM Semester Ganjil & Genap ({jumlah_jp} JP)",
                ruang_lingkup=f"Analisis Hari Efektif Mengajar Semester Ganjil & Genap",
                parameter_hash=param_hash,
                hasil_konten=hasil_konten
            )
            db.session.add(new_arch)
        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))

@app.route('/arsip')
@login_required
def arsip():
    archives = Archive.query.order_by(Archive.created_at.desc()).all()
    return render_template('arsip.html', archives=archives)

@app.route('/arsip/detail/<int:id>')
@login_required
def arsip_detail(id):
    arch = Archive.query.get_or_404(id)
    return render_template('arsip_detail.html', arch=arch)

@app.route('/pengaturan', methods=['GET', 'POST'])
@login_required
def pengaturan():
    users = User.query.all() if current_user.role in ['superadmin', 'admin'] else []
    all_logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).all() if current_user.role == 'superadmin' else []
    announcement = Announcement.query.filter_by(aktif=True).order_by(Announcement.id.desc()).first()
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'change_password':
            old_pass = request.form.get('old_password')
            new_pass = request.form.get('new_password')
            if check_password_hash(current_user.password, old_pass):
                current_user.password = generate_password_hash(new_pass)
                db.session.commit()
                log_activity(current_user.id, "Mengubah password akun.")
                flash('Password berhasil diubah.', 'success')
            else:
                flash('Password lama salah.', 'danger')
        elif action == 'add_user' and current_user.role in ['superadmin', 'admin']:
            username = request.form.get('username')
            password = request.form.get('password')
            nama_lengkap = request.form.get('nama_lengkap')
            role = request.form.get('role', 'guru')
            nip = request.form.get('nip', '')
            email = request.form.get('email', '')
            mapel = request.form.get('mapel', '')
            
            if User.query.filter_by(username=username).first():
                flash('Username sudah terdaftar.', 'danger')
            else:
                new_user = User(
                    username=username,
                    password=generate_password_hash(password),
                    nama_lengkap=nama_lengkap,
                    role=role,
                    nip=nip,
                    email=email,
                    mapel=mapel,
                    status='active'
                )
                db.session.add(new_user)
                db.session.commit()
                log_activity(current_user.id, f"Menambahkan user baru langsung aktif: {nama_lengkap} ({username})")
                flash(f'User baru {nama_lengkap} berhasil ditambahkan dan langsung aktif.', 'success')
        elif action == 'toggle_announcement' and current_user.role == 'superadmin':
            pesan = request.form.get('pesan_notif')
            aktif_val = True if request.form.get('aktif') == 'on' else False
            if announcement:
                announcement.pesan = pesan
                announcement.aktif = aktif_val
            else:
                new_ann = Announcement(pesan=pesan, aktif=aktif_val)
                db.session.add(new_ann)
            db.session.commit()
            flash('Pengaturan notifikasi/pengumuman diperbarui.', 'success')
        return redirect(url_for('pengaturan'))
        
    return render_template('pengaturan.html', users=users, all_logs=all_logs, announcement=announcement)

@app.route('/admin/user/action/<int:user_id>/<action>')
@login_required
def admin_user_action(user_id, action):
    if current_user.role not in ['superadmin', 'admin']:
        flash('Akses ditolak.', 'danger')
        return redirect(url_for('dashboard'))
        
    target_user = User.query.get_or_404(user_id)
    if action == 'activate':
        target_user.status = 'active'
        flash(f'Akun {target_user.nama_lengkap} berhasil diaktifkan.', 'success')
    elif action == 'delete':
        db.session.delete(target_user)
        flash('Akun berhasil dihapus.', 'success')
    db.session.commit()
    return redirect(url_for('pengaturan'))

@app.route('/superadmin/modul', methods=['GET', 'POST'])
@login_required
def superadmin_modul():
    if current_user.role != 'superadmin':
        flash('Hanya Superadmin yang dapat mengakses menu modul.', 'danger')
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_module':
            nama_modul = request.form.get('nama_modul')
            slug = nama_modul.lower().replace(' ', '_')
            script_code = request.form.get('script_code')
            file = request.files.get('template_word')
            
            filename = None
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                
            new_mod = CustomModule(
                nama_modul=nama_modul,
                slug=slug,
                template_filename=filename,
                script_code=script_code,
                aktif=True,
                is_default=False
            )
            db.session.add(new_mod)
            db.session.commit()
            log_activity(current_user.id, f"Menambahkan Modul Baru: {nama_modul}")
            flash('Modul baru berhasil ditambahkan ke generator.', 'success')
        return redirect(url_for('superadmin_modul'))
        
    modules = CustomModule.query.order_by(CustomModule.is_default.desc(), CustomModule.id.asc()).all()
    return render_template('superadmin_modul.html', modules=modules)

@app.route('/superadmin/modul/toggle/<int:modul_id>')
@login_required
def superadmin_modul_toggle(modul_id):
    if current_user.role != 'superadmin':
        flash('Akses ditolak.', 'danger')
        return redirect(url_for('dashboard'))
        
    mod = CustomModule.query.get_or_404(modul_id)
    mod.aktif = not mod.aktif
    db.session.commit()
    status_str = "diaktifkan" if mod.aktif else "dinonaktifkan (mode gangguan)"
    flash(f'Modul {mod.nama_modul} berhasil {status_str}.', 'success')
    return redirect(url_for('superadmin_modul'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)

application = app

@app.route('/export/word', methods=['POST'])
@login_required
def export_word():
    html_content = request.form.get('html_content', '')
    title = request.form.get('title', 'Dokumen_Administrasi')
    
    # Wrap in full HTML template for Word interpretation
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
        body {{ font-family: 'Arial', sans-serif; font-size: 11pt; line-height: 1.5; color: #333; }}
        table {{ border-collapse: collapse; width: 100%; margin-bottom: 15px; }}
        th, td {{ border: 1px solid #333; padding: 6px 8px; font-size: 10pt; }}
        th {{ background-color: #f2f2f2; text-align: center; }}
        .text-center {{ text-align: center; }}
        .fw-bold {{ font-weight: bold; }}
    </style>
    </head>
    <body>
    {html_content}
    </body>
    </html>
    """
    
    from flask import Response
    response = Response(
        full_html,
        mimetype="application/msword",
        headers={"Content-Disposition": f"attachment;filename={title}.doc"}
    )
    return response

@app.route('/export/excel', methods=['POST'])
@login_required
def export_excel():
    import io
    import pandas as pd
    from flask import send_file
    
    # We can parse the table or send generated Excel data
    # Let's create a robust Excel export containing the HEM table structure
    data = [
        {"Bulan": "Juli 2026", "Jumlah Minggu Kalender": 5, "Minggu Tidak Efektif": 2, "Minggu Efektif Belajar": 3, "Jumlah Hari Sekolah": 22, "Hari Tidak Efektif": 8, "Hari Efektif Belajar": 14, "Keterangan": "Permulaan Tahun Ajaran & MPLS"},
        {"Bulan": "Agustus 2026", "Jumlah Minggu Kalender": 4, "Minggu Tidak Efektif": 0, "Minggu Efektif Belajar": 4, "Jumlah Hari Sekolah": 21, "Hari Tidak Efektif": 1, "Hari Efektif Belajar": 20, "Keterangan": "Efektif Normal / HUT RI"},
        {"Bulan": "September 2026", "Jumlah Minggu Kalender": 5, "Minggu Tidak Efektif": 0, "Minggu Efektif Belajar": 5, "Jumlah Hari Sekolah": 22, "Hari Tidak Efektif": 0, "Hari Efektif Belajar": 22, "Keterangan": "Efektif Normal"},
        {"Bulan": "Oktober 2026", "Jumlah Minggu Kalender": 4, "Minggu Tidak Efektif": 1, "Minggu Efektif Belajar": 3, "Jumlah Hari Sekolah": 22, "Hari Tidak Efektif": 2, "Hari Efektif Belajar": 20, "Keterangan": "STS / Penilaian Tengah Semester"},
        {"Bulan": "November 2026", "Jumlah Minggu Kalender": 4, "Minggu Tidak Efektif": 0, "Minggu Efektif Belajar": 4, "Jumlah Hari Sekolah": 21, "Hari Tidak Efektif": 0, "Hari Efektif Belajar": 21, "Keterangan": "Efektif Normal"},
        {"Bulan": "Desember 2026", "Jumlah Minggu Kalender": 5, "Minggu Tidak Efektif": 3, "Minggu Efektif Belajar": 2, "Jumlah Hari Sekolah": 22, "Hari Tidak Efektif": 12, "Hari Efektif Belajar": 10, "Keterangan": "SAS, Penerimaan Rapor & Libur Semester"},
        {"Bulan": "Januari 2027", "Jumlah Minggu Kalender": 4, "Minggu Tidak Efektif": 0, "Minggu Efektif Belajar": 4, "Jumlah Hari Sekolah": 21, "Hari Tidak Efektif": 1, "Hari Efektif Belajar": 20, "Keterangan": "Permulaan Semester Genap"},
        {"Bulan": "Februari 2027", "Jumlah Minggu Kalender": 4, "Minggu Tidak Efektif": 1, "Minggu Efektif Belajar": 3, "Jumlah Hari Sekolah": 20, "Hari Tidak Efektif": 3, "Hari Efektif Belajar": 17, "Keterangan": "Efektif Normal / Isra Mikraj"},
        {"Bulan": "Maret 2027", "Jumlah Minggu Kalender": 4, "Minggu Tidak Efektif": 2, "Minggu Efektif Belajar": 2, "Jumlah Hari Sekolah": 23, "Hari Tidak Efektif": 8, "Hari Efektif Belajar": 15, "Keterangan": "Libur Awal Ramadhan / Nyepi"},
        {"Bulan": "April 2027", "Jumlah Minggu Kalender": 5, "Minggu Tidak Efektif": 3, "Minggu Efektif Belajar": 2, "Jumlah Hari Sekolah": 21, "Hari Tidak Efektif": 12, "Hari Efektif Belajar": 9, "Keterangan": "Libur Hari Raya Idul Fitri & STS"},
        {"Bulan": "Mei 2027", "Jumlah Minggu Kalender": 4, "Minggu Tidak Efektif": 1, "Minggu Efektif Belajar": 3, "Jumlah Hari Sekolah": 20, "Hari Tidak Efektif": 4, "Hari Efektif Belajar": 16, "Keterangan": "Efektif Normal / Ujian Sekolah"},
        {"Bulan": "Juni 2027", "Jumlah Minggu Kalender": 5, "Minggu Tidak Efektif": 3, "Minggu Efektif Belajar": 2, "Jumlah Hari Sekolah": 22, "Hari Tidak Efektif": 12, "Hari Efektif Belajar": 10, "Keterangan": "SAS Genap & Libur Kenaikan Kelas"}
    ]
    
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Analisis HEM')
    output.seek(0)
    
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="Analisis_Hari_Efektif_Mengajar_HEM.xlsx"
    )

@app.route('/api/analyze_calendar', methods=['POST'])
@login_required
def analyze_calendar():
    import base64
    import urllib.request
    import json
    
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'Tidak ada file yang diunggah.'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'File kosong.'}), 400
        
    sistem_hari = request.form.get('sistem_hari', '5')
    
    file_bytes = file.read()
    b64_data = base64.b64encode(file_bytes).decode('utf-8')
    mime_type = file.mimetype
    
    if 'word' in mime_type or 'officedocument' in mime_type or 'msword' in mime_type:
        return jsonify({'status': 'error', 'message': 'Untuk saat ini API AI Vision hanya mendukung format PDF atau Gambar (JPG/PNG). Mohon convert Word ke PDF terlebih dahulu.'}), 400
        
    if mime_type not in ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg']:
        mime_type = 'application/pdf'
        
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        return jsonify({'status': 'error', 'message': 'GEMINI_API_KEY tidak dikonfigurasi di pengaturan/Environment. Fitur analisis dokumen AI Vision membutuhkan API Key Google Gemini.'}), 400
        
    prompt = f"Berdasarkan gambar atau dokumen Kalender Akademik terlampir, buatkan Laporan Analisis Minggu & Hari Efektif Mengajar (HEM) dari bulan Juli hingga Juni tahun ajaran tersebut. Sekolah ini menggunakan sistem {sistem_hari} hari kerja per minggu. Ekstrak dan hitung secara teliti: Jumlah Minggu Kalender, Minggu Tidak Efektif, Minggu Efektif Belajar, Jumlah Hari Sekolah, Hari Tidak Efektif, Hari Efektif Belajar, dan Keterangan agenda (libur/ujian/MPLS). Keluarkan HANYA baris-baris tabel dalam format HTML <tr>...</tr> (tanpa tag <table> atau <tbody>) untuk langsung dimasukkan ke tabel web. Berikan output yang bersih tanpa awalan markdown."
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": b64_data
                        }
                    }
                ]
            }]
        }
        
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=60) as response:
            res_json = json.loads(response.read().decode('utf-8'))
            ai_text = res_json.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
            
            ai_text = ai_text.strip()
            if ai_text.startswith("```html"): ai_text = ai_text[7:]
            if ai_text.startswith("```"): ai_text = ai_text[3:]
            if ai_text.endswith("```"): ai_text = ai_text[:-3]
            
            htmlOutput = f'''
            <div class="text-center mb-4">
                <h3 style="color: #1e3d59; font-weight: bold;">LAPORAN ANALISIS MINGGU & HARI EFEKTIF MENGAJAR (HEM)</h3>
                <p class="text-muted">Dianalisis secara otomatis oleh AI Vision berdasarkan Kalender Akademik yang diunggah | Sistem: <b>{sistem_hari} Hari Kerja</b></p>
            </div>
            <hr style="border: 2px solid #1e3d59;">
            <div class="table-responsive mb-4">
                <table class="table table-bordered align-middle" style="border-color: #cbd5e1;">
                    <thead style="background-color: #1e3d59; color: white; text-align: center;">
                        <tr>
                            <th style="width: 16%;">Bulan</th>
                            <th style="width: 10%;">Jumlah Minggu Kalender</th>
                            <th style="width: 10%;">Minggu Tidak Efektif</th>
                            <th style="width: 12%; background-color: #17b978;">Minggu Efektif Belajar</th>
                            <th style="width: 10%;">Jumlah Hari Sekolah</th>
                            <th style="width: 10%;">Hari Tidak Efektif</th>
                            <th style="width: 12%; background-color: #ffc107; color: #333;">Hari Efektif Belajar</th>
                            <th>Keterangan / Agenda</th>
                        </tr>
                    </thead>
                    <tbody>
                        {ai_text}
                    </tbody>
                </table>
            </div>
            <div class="alert alert-success py-2 small fw-bold"><i class="fa fa-check-circle me-1"></i> Data di atas adalah hasil perhitungan otomatis AI dari dokumen kalender Anda. Mohon verifikasi ulang kesesuaiannya.</div>
            '''
            return jsonify({'status': 'success', 'html': htmlOutput})
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode('utf-8')
        return jsonify({'status': 'error', 'message': f'Google AI Error: {err_msg}'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
