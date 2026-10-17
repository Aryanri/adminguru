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
    return redirect(url_for('login'))

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
            
            param_str = f"{jenis}-{jenjang}-{kelas}-{fase}-{kurikulum}-{mapel}-{topik}-{ruang_lingkup}-{kesulitan}-{current_user.id}"
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

                # Check HEM data for Alokasi Waktu integration if modul is cp_tp_atp
                hem_saved = Archive.query.filter_by(user_id=current_user.id, jenis_administrasi="Analisis Hari Efektif Mengajar (HEM)").order_by(Archive.created_at.desc()).first()
                sem1_jp = "48"
                sem2_jp = "48"
                sem1_minggu = "16"
                sem2_minggu = "16"
                jp_per_mgg = "3"

                if modul_slug == 'cp_tp_atp':
                    hasil_generate = f"{kop_html}" \
                                     f"<div class='mb-3 p-3 bg-light border rounded small'>" \
                                     f"<b>IDENTITAS PENYUSUN DOKUMEN:</b><br>" \
                                     f"Nama Lengkap: {current_user.nama_lengkap}<br>" \
                                     f"NIP: {guru_nip}<br>" \
                                     f"Alamat Email: {guru_email}<br>" \
                                     f"Mata Pelajaran: {mapel}" \
                                     f"</div>" \
                                     f"<h3 class='text-center'>PEMETAAN CAPAIAN PEMBELAJARAN (CP), TUJUAN PEMBELAJARAN (TP)<br>DAN ALUR TUJUAN PEMBELAJARAN (ATP)</h3>" \
                                     f"<hr>" \
                                     f"<table class='table table-bordered mb-4'>" \
                                     f"<tr><th style='width: 25%'>Mata Pelajaran</th><td>{mapel}</td></tr>" \
                                     f"<tr><th>Kelas / Fase</th><td>{kelas} / {fase}</td></tr>" \
                                     f"<tr><th>Sekolah</th><td>{profile.nama_sekolah if profile else 'SD/MI / SMP/MTs / SMA/MA'}</td></tr>" \
                                     f"<tr><th>Tahun Pelajaran</th><td>2025/2026</td></tr>" \
                                     f"<tr><th>Semester</th><td>1 dan 2 (Ganjil & Genap)</td></tr>" \
                                     f"<tr><th>Alokasi Waktu</th><td>3 Jam Pelajaran per minggu</td></tr>" \
                                     f"</table>" \
                                     f"<h4 class='text-primary mt-4'>I. CAPAIAN PEMBELAJARAN (CP) - FASE {fase.split(' ')[0]}</h4>" \
                                     f"<table class='table table-bordered table-striped'>" \
                                     f"<thead class='table-dark'><tr><th style='width: 25%'>Elemen</th><th>Capaian Pembelajaran (CP)</th></tr></thead>" \
                                     f"<tbody>" \
                                     f"<tr><td class='fw-bold'>Pemahaman Konsep</td><td>Peserta didik mampu memahami dan menguasai materi pokok {topik} dengan ruang lingkup {ruang_lingkup} melalui pendekatan {metode} dan aktivitas {aktivitas}.</td></tr>" \
                                     f"<tr><td class='fw-bold'>Keterampilan Proses</td><td>Peserta didik mampu melakukan analisis kritis, pemecahan masalah, serta menerapkan prinsip-prinsip keilmuan {mapel} secara kontekstual.</td></tr>" \
                                     f"</tbody>" \
                                     f"</table>" \
                                     f"<h4 class='text-primary mt-4'>II. TUJUAN PEMBELAJARAN (TP) DAN ALUR TUJUAN PEMBELAJARAN (ATP)</h4>" \
                                     f"<h5 class='mt-3 text-secondary'>SEMESTER 1 (GANJIL)</h5>" \
                                     f"<table class='table table-bordered table-striped align-middle'>" \
                                     f"<thead class='table-dark text-center'><tr><th style='width: 5%'>No</th><th style='width: 20%'>Elemen</th><th style='width: 20%'>Materi/Bab</th><th>Tujuan Pembelajaran (TP)</th><th>Alur Tujuan Pembelajaran (ATP)</th><th style='width: 15%'>Justifikasi</th></tr></thead>" \
                                     f"<tbody>" \
                                     f"<tr><td class='text-center'>1</td><td>Pemahaman Konsep</td><td>Bab 1: Pengantar {topik}</td><td>Memahami konsep dasar {topik} dan ruang lingkup {ruang_lingkup}.</td><td>1. Menjelaskan definisi dasar.<br>2. Mengidentifikasi komponen utama.</td><td>Hierarki Konsep Dasar</td></tr>" \
                                     f"<tr><td class='text-center'>2</td><td>Keterampilan Proses</td><td>Bab 2: Analisis & Eksplorasi {ruang_lingkup}</td><td>Menerapkan metode {metode} dalam studi kasus nyata.</td><td>1. Melakukan observasi.<br>2. Menyusun laporan analisis.</td><td>Konkret ke Abstrak</td></tr>" \
                                     f"</tbody>" \
                                     f"</table>" \
                                     f"<h5 class='mt-4 text-secondary'>SEMESTER 2 (GENAP)</h5>" \
                                     f"<table class='table table-bordered table-striped align-middle'>" \
                                     f"<thead class='table-dark text-center'><tr><th style='width: 5%'>No</th><th style='width: 20%'>Elemen</th><th style='width: 20%'>Materi/Bab</th><th>Tujuan Pembelajaran (TP)</th><th>Alur Tujuan Pembelajaran (ATP)</th><th style='width: 15%'>Justifikasi</th></tr></thead>" \
                                     f"<tbody>" \
                                     f"<tr><td class='text-center'>3</td><td>Pemahaman Konsep</td><td>Bab 3: Pendalaman & Integrasi Materi</td><td>Mengevaluasi penerapan lanjutan {mapel} secara komprehensif.</td><td>1. Studi literatur.<br>2. Diskusi kelompok.</td><td>Mudah ke Sulit</td></tr>" \
                                     f"<tr><td class='text-center'>4</td><td>Keterampilan Proses</td><td>Bab 4: Proyek Akhir Semester ({aktivitas})</td><td>Membuat produk atau proyek nyata berbasis pemecahan masalah.</td><td>1. Perencanaan proyek.<br>2. Eksekusi & Presentasi.</td><td>Integrasi Antar Konsep</td></tr>" \
                                     f"</tbody>" \
                                     f"</table>" \
                                     f"<h4 class='text-primary mt-4'>III. CATATAN IMPLEMENTASI & ALOKASI WAKTU</h4>" \
                                     f"<div class='p-3 bg-light border rounded mb-4'>" \
                                     f"<b>Alokasi Waktu Total:</b><br>" \
                                     f"Semester 1: {sem1_jp} JP ({sem1_minggu} minggu × {jp_per_mgg} JP/minggu) | Semester 2: {sem2_jp} JP ({sem2_minggu} minggu × {jp_per_mgg} JP/minggu) | <b>Total: {int(sem1_jp)+int(sem2_jp)} JP</b><br><br>" \
                                     f"<b>Prinsip Pengurutan ATP:</b><br>" \
                                     f"1. Hierarki Konsep (dasar ke kompleks)<br>" \
                                     f"2. Konkret ke Abstrak<br>" \
                                     f"3. Mudah ke Sulit<br>" \
                                     f"4. Integrasi Antar Konsep dalam Satu Materi" \
                                     f"</div>" \
                                     f"<div class='row mt-5'>" \
                                     f"<div class='col-6'></div>" \
                                     f"<div class='col-6 text-center'>" \
                                     f"<p>Mengetahui,<br>Kepala Sekolah</p><br><br><br>" \
                                     f"<b>{profile.nama_kepsek if profile else 'Kepala Sekolah'}</b><br>" \
                                     f"NIP. {profile.nip_kepsek if profile else '-'}" \
                                     f"</div>" \
                                     f"</div>"
                else:
                    hasil_generate = f"{kop_html}" \
                                     f"<div class='mb-3 p-3 bg-light border rounded small'>" \
                                     f"<b>IDENTITAS PENYUSUN DOKUMEN:</b><br>" \
                                     f"Nama Lengkap: {current_user.nama_lengkap}<br>" \
                                     f"NIP: {guru_nip}<br>" \
                                     f"Alamat Email: {guru_email}<br>" \
                                     f"Mata Pelajaran: {mapel}" \
                                     f"</div>" \
                                     f"<h3>DOKUMEN ADMINISTRASI GURU: {jenis.upper()}</h3>" \
                                     f"<hr><p><b>Jenjang:</b> {jenjang} | <b>Kelas & Fase:</b> {kelas} ({fase}) | <b>Kurikulum:</b> {kurikulum}</p>" \
                                     f"<p><b>Mata Pelajaran:</b> {mapel} | <b>Metode:</b> {metode}</p>" \
                                     f"<p><b>Topik Materi:</b> {topik}</p>" \
                                     f"<p><b>Ruang Lingkup:</b> {ruang_lingkup}</p>" \
                                     f"<p><b>Tingkat Kesulitan:</b> {kesulitan}</p>" \
                                     f"<h4>Rincian / Soal Tergenerate:</h4>" \
                                     f"<ul>" \
                                     f"<li>Jumlah Pilihan Ganda: {jml_pg} soal</li>" \
                                     f"<li>Jumlah Isian Singkat: {jml_isian} soal</li>" \
                                     f"<li>Jumlah Esai: {jml_esai} soal</li>" \
                                     f"</ul>" \
                                     f"<div style='border:1px dashed #ccc; padding:15px; background:#f9f9f9;'>" \
                                     f"<b>Konten AI (Ringkas & Langsung ke Inti):</b><br>" \
                                     f"1. Analisis Pembelajaran & Capaian Pembelajaran Kurikulum {kurikulum}.<br>" \
                                     f"2. Langkah kegiatan pembelajaran berbasis aktivitas {aktivitas}.<br>" \
                                     f"3. Instrumen Penilaian dan Rubrik Evaluasi Peserta Didik siap cetak." \
                                     f"</div>" \
                                     f"<div class='row mt-5'>" \
                                     f"<div class='col-6'></div>" \
                                     f"<div class='col-6 text-center'>" \
                                     f"<p>Mengetahui,<br>Kepala Sekolah</p><br><br><br>" \
                                     f"<b>{profile.nama_kepsek if profile else 'Kepala Sekolah'}</b><br>" \
                                     f"NIP. {profile.nip_kepsek if profile else '-'}" \
                                     f"</div>" \
                                     f"</div>"
                
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
                    status='active' # langsung aktif tanpa konfirmasi
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
