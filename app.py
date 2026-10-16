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
from models import db, User, SchoolProfile, Teacher, Student, Archive, ActivityLog, Announcement, CustomModule

app = Flask(__name__)
app.config['SECRET_KEY'] = 'siap_administrasi_guru_2026_secret_key'
db_url = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
if db_url:
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    if db_url.startswith("postgresql://") and "+psycopg2" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
if os.environ.get('VERCEL') or not os.access(os.path.dirname(__file__) or '.', os.W_OK):
    app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
else:
    app.config['UPLOAD_FOLDER'] = 'uploads'

try:
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
except Exception as e:
    print("Upload folder creation notice:", e)

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
        if current_user.current_session_id != session.get('device_session_id'):
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

    if request.method == 'POST':
        jenjang = request.form.get('jenjang')
        kelas_fase_val = request.form.get('kelas_fase', 'Kelas 7 | Fase D (Kelas 7-9)')
        parts = kelas_fase_val.split('|')
        kelas = parts[0].strip() if len(parts) > 0 else 'Kelas 7'
        fase = parts[1].strip() if len(parts) > 1 else 'Fase D (Kelas 7-9)'

        kurikulum = request.form.get('kurikulum')
        mapel = request.form.get('mapel')
        metode = request.form.get('metode')
        aktivitas = request.form.get('aktivitas')
        kesulitan = request.form.get('kesulitan', 'C3')
        jml_pg = request.form.get('jml_pg', '10')
        jml_esai = request.form.get('jml_esai', '5')
        jml_isian = request.form.get('jml_isian', '5')
        topik = request.form.get('topik')
        ruang_lingkup = request.form.get('ruang_lingkup')
        
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

            hasil_generate = f"{kop_html}"                              f"<div class='mb-3 p-3 bg-light border rounded small'>"                              f"<b>IDENTITAS PENYUSUN DOKUMEN:</b><br>"                              f"Nama Lengkap: {current_user.nama_lengkap}<br>"                              f"NIP: {guru_nip}<br>"                              f"Alamat Email: {guru_email}<br>"                              f"Mata Pelajaran: {guru_mapel}"                              f"</div>"                              f"<h3>DOKUMEN ADMINISTRASI GURU: {jenis.upper()}</h3>"                              f"<hr><p><b>Jenjang:</b> {jenjang} | <b>Kelas & Fase:</b> {kelas} ({fase}) | <b>Kurikulum:</b> {kurikulum}</p>"                              f"<p><b>Mata Pelajaran:</b> {guru_mapel} | <b>Metode:</b> {metode}</p>"                              f"<p><b>Topik Materi:</b> {topik}</p>"                              f"<p><b>Ruang Lingkup:</b> {ruang_lingkup}</p>"                              f"<p><b>Tingkat Kesulitan (BSKAP 2026):</b> {kesulitan}</p>"                              f"<h4>Rincian / Soal Tergenerate:</h4>"                              f"<ul>"                              f"<li>Jumlah Pilihan Ganda: {jml_pg} soal (Level C1-C6)</li>"                              f"<li>Jumlah Isian Singkat: {jml_isian} soal</li>"                              f"<li>Jumlah Esai: {jml_esai} soal</li>"                              f"</ul>"                              f"<div style='border:1px dashed #ccc; padding:15px; background:#f9f9f9;'>"                              f"<b>Konten AI (Ringkas & Langsung ke Inti):</b><br>"                              f"1. Analisis Pembelajaran & Capaian Pembelajaran Kurikulum {kurikulum}.<br>"                              f"2. Langkah kegiatan pembelajaran berbasis aktivitas {aktivitas}.<br>"                              f"3. Instrumen Penilaian dan Rubrik Evaluasi Peserta Didik siap cetak."                              f"</div>"                              f"<div class='row mt-5'>"                              f"<div class='col-6'></div>"                              f"<div class='col-6 text-center'>"                              f"<p>Mengetahui,<br>Kepala Sekolah</p><br><br>"                              f"<b>{profile.nama_kepsek if profile else 'Kepala Sekolah'}</b><br>"                              f"NIP. {profile.nip_kepsek if profile else '-'}"                              f"</div>"                              f"</div>"
            
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
            
    return render_template('generator.html', all_modules=all_modules, hasil_generate=hasil_generate, active_slug=modul_slug, current_jenis=jenis)

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
    with app.app_context():
        db_path = os.path.join(app.instance_path, 'database.db') if os.path.exists(app.instance_path) else 'database.db'
        if not os.path.exists(db_path) and os.path.exists('instance/database.db'):
            db_path = 'instance/database.db'
            
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='custom_module';")
            tbl_exists = cursor.fetchone()
            if tbl_exists:
                cursor.execute("PRAGMA table_info(custom_module);")
                columns = [col[1] for col in cursor.fetchall()]
                if 'aktif' not in columns:
                    cursor.execute("ALTER TABLE custom_module ADD COLUMN aktif BOOLEAN DEFAULT 1;")
                    conn.commit()
                if 'is_default' not in columns:
                    cursor.execute("ALTER TABLE custom_module ADD COLUMN is_default BOOLEAN DEFAULT 0;")
                    conn.commit()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user';")
            if cursor.fetchone():
                cursor.execute("PRAGMA table_info(user);")
                user_cols = [col[1] for col in cursor.fetchall()]
                if 'email' not in user_cols:
                    cursor.execute("ALTER TABLE user ADD COLUMN email VARCHAR(120);")
                    conn.commit()
                if 'nip' not in user_cols:
                    cursor.execute("ALTER TABLE user ADD COLUMN nip VARCHAR(50);")
                    conn.commit()
                if 'mapel' not in user_cols:
                    cursor.execute("ALTER TABLE user ADD COLUMN mapel VARCHAR(100);")
                    conn.commit()
            conn.close()
        except Exception as e:
            print("Pre-migration note:", e)

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
            
    app.run(debug=True, port=5000)
