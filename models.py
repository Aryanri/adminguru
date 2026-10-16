from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False) # can be email or username
    email = db.Column(db.String(120), nullable=True)
    nip = db.Column(db.String(50), nullable=True)
    mapel = db.Column(db.String(100), nullable=True)
    password = db.Column(db.String(200), nullable=False)
    nama_lengkap = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='guru') # superadmin, admin, guru
    status = db.Column(db.String(20), nullable=False, default='pending') # active, pending, inactive
    current_session_id = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    archives = db.relationship('Archive', backref='user', lazy=True)
    activity_logs = db.relationship('ActivityLog', backref='user', lazy=True)

class SchoolProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kop_sekolah = db.Column(db.Text, nullable=True)
    nama_sekolah = db.Column(db.String(150), default="SMN 1 Contoh")
    alamat = db.Column(db.Text, default="Jl. Pendidikan No. 1")
    nama_kepsek = db.Column(db.String(150), default="Dr. Kepala Sekolah, M.Pd.")
    nip_kepsek = db.Column(db.String(50), default="196501011988031001")

class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nip = db.Column(db.String(50), unique=True, nullable=False)
    nama = db.Column(db.String(150), nullable=False)
    mapel = db.Column(db.String(100), nullable=False)
    kontak = db.Column(db.String(50), nullable=True)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nis = db.Column(db.String(50), unique=True, nullable=False)
    nama = db.Column(db.String(150), nullable=False)
    kelas = db.Column(db.String(20), nullable=False)
    jenis_kelamin = db.Column(db.String(20), nullable=True)

class Archive(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    jenis_administrasi = db.Column(db.String(100), nullable=False)
    topik = db.Column(db.String(255), nullable=False)
    ruang_lingkup = db.Column(db.Text, nullable=True)
    parameter_hash = db.Column(db.String(255), index=True, nullable=False)
    hasil_konten = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    aktivitas = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pesan = db.Column(db.Text, nullable=False)
    aktif = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CustomModule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama_modul = db.Column(db.String(100), unique=True, nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    template_filename = db.Column(db.String(255), nullable=True)
    script_code = db.Column(db.Text, nullable=True)
    aktif = db.Column(db.Boolean, default=True)
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
