import os
import sqlite3
import calendar
from flask import Flask, render_template_string, request, redirect, url_for, session, send_file, flash
from werkzeug.security import generate_password_hash, check_password_hash
from docx import Document

from config import DB_NAME, SECRET_KEY, HOLIDAYS_DB
from database import init_db, log_user_activity, check_module_active
from templates_html import BASE_LAYOUT, LOGIN_TEMPLATE

app = Flask(__name__)
app.secret_key = SECRET_KEY

init_db()

@app.route('/login', methods=['GET', 'POST'])
def login():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT pesan FROM notifications ORDER BY id DESC LIMIT 1")
    notif_row = cursor.fetchone()
    latest_notification = notif_row[0] if notif_row else None
    conn.close()

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, password, nama_lengkap, role FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['nama'] = user[3]
            session['role'] = user[4]
            log_user_activity(username, "Login", f"User {username} berhasil masuk ke sistem.", request.remote_addr)
            return redirect(url_for('dashboard'))
        else:
            flash('Username atau password salah!', 'error')
            
    return render_template_string(LOGIN_TEMPLATE, latest_notification=latest_notification)

@app.route('/logout')
def logout():
    if 'username' in session:
        log_user_activity(session['username'], "Logout", f"User {session['username']} keluar dari sistem.", request.remote_addr)
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    role = session.get('role')
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    if role in ['superadmin', 'admin']:
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM online_users")
        total_online = cursor.fetchone()[0]
        cursor.execute("SELECT username, role, last_seen FROM online_users")
        online_list = cursor.fetchall()
        conn.close()

        content = f'''
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6">
                <div class="flex items-center justify-between mb-4">
                    <span class="text-sm font-medium text-slate-400">Total User Terdaftar</span>
                    <i class="fa-solid fa-users text-blue-400 text-xl"></i>
                </div>
                <h3 class="text-3xl font-bold text-white">{total_users} Akun</h3>
                <p class="text-xs text-slate-500 mt-1">Superadmin, Admin, & Guru</p>
            </div>
            <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6">
                <div class="flex items-center justify-between mb-4">
                    <span class="text-sm font-medium text-slate-400">User Sedang Online</span>
                    <i class="fa-solid fa-circle-dot text-emerald-400 text-xl"></i>
                </div>
                <h3 class="text-3xl font-bold text-emerald-400">{total_online} Aktif</h3>
                <p class="text-xs text-slate-500 mt-1">Sesi aktif saat ini</p>
            </div>
        </div>

        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <h3 class="text-base font-bold text-white mb-4">Daftar User Sedang Online</h3>
            <div class="overflow-x-auto">
                <table class="w-full text-left text-sm text-slate-300">
                    <thead class="bg-slate-800/50 text-xs uppercase text-slate-400">
                        <tr><th class="p-3">Username</th><th class="p-3">Role</th><th class="p-3">Waktu Akses Terakhir</th></tr>
                    </thead>
                    <tbody class="divide-y divide-slate-800">
        '''
        for o in online_list:
            content += f'<tr><td class="p-3 font-medium text-white">{o[0]}</td><td class="p-3 uppercase text-xs text-blue-400">{o[1]}</td><td class="p-3 text-xs text-slate-500">{o[2]}</td></tr>'
        content += '''
                    </tbody>
                </table>
            </div>
        </div>
        '''
        return render_template_string(BASE_LAYOUT, title=f"Dashboard {role.capitalize()}", content=content)

    else:
        cursor.execute("SELECT COUNT(*) FROM arsip_dokumen")
        total_arsip = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM arsip_dokumen WHERE is_cached_hit = 1")
        total_cache_hits = cursor.fetchone()[0]
        cursor.execute("SELECT * FROM arsip_dokumen ORDER BY id DESC LIMIT 5")
        recent_arsip = cursor.fetchall()
        conn.close()

        content = f'''
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6">
                <div class="flex items-center justify-between mb-4">
                    <span class="text-sm font-medium text-slate-400">Total Dokumen AI / Word</span>
                    <i class="fa-solid fa-file-word text-blue-400 text-xl"></i>
                </div>
                <h3 class="text-3xl font-bold text-white">{total_arsip}</h3>
                <p class="text-xs text-slate-500 mt-1">Tersimpan dalam arsip</p>
            </div>
            <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6">
                <div class="flex items-center justify-between mb-4">
                    <span class="text-sm font-medium text-slate-400">Cache Hits (Efisiensi)</span>
                    <i class="fa-solid fa-bolt text-amber-400 text-xl"></i>
                </div>
                <h3 class="text-3xl font-bold text-amber-400">{total_cache_hits} Request</h3>
                <p class="text-xs text-slate-500 mt-1">Diambil instan dari cache serupa</p>
            </div>
            <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6">
                <div class="flex items-center justify-between mb-4">
                    <span class="text-sm font-medium text-slate-400">Status Sistem AI</span>
                    <i class="fa-solid fa-robot text-emerald-400 text-xl"></i>
                </div>
                <h3 class="text-3xl font-bold text-emerald-400">Online</h3>
                <p class="text-xs text-slate-500 mt-1">Modular & Aman</p>
            </div>
        </div>

        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <h3 class="text-base font-bold text-white mb-4">Arsip Dokumen Terakhir</h3>
            <div class="overflow-x-auto">
                <table class="w-full text-left text-sm text-slate-300">
                    <thead class="bg-slate-800/50 text-xs uppercase text-slate-400">
                        <tr><th class="p-3">Kategori</th><th class="p-3">Judul</th><th class="p-3">Pembuat</th><th class="p-3">Sumber</th><th class="p-3">Tanggal</th><th class="p-3">Aksi</th></tr>
                    </thead>
                    <tbody class="divide-y divide-slate-800">
        '''
        for row in recent_arsip:
            source_badge = '<span class="text-[10px] bg-amber-500/10 text-amber-400 px-2 py-0.5 rounded font-mono">Cache Serupa</span>' if row[6] == 1 else '<span class="text-[10px] bg-blue-500/10 text-blue-400 px-2 py-0.5 rounded font-mono">Baru (AI)</span>'
            content += f'<tr><td class="p-3 uppercase text-xs text-blue-400">{row[2]}</td><td class="p-3 font-medium text-white">{row[3]}</td><td class="p-3 text-xs text-slate-400">{row[1]}</td><td class="p-3">{source_badge}</td><td class="p-3 text-xs text-slate-500">{row[5]}</td><td class="p-3"><a href="/download_docx/{row[0]}" class="text-xs bg-blue-600/20 text-blue-400 border border-blue-500/30 px-3 py-1.5 rounded-lg hover:bg-blue-600 hover:text-white">Download Word</a></td></tr>'
        content += '''
                    </tbody>
                </table>
            </div>
        </div>
        '''
        return render_template_string(BASE_LAYOUT, title="Dashboard Guru", content=content)

@app.route('/history')
def history_menu():
    if 'user_id' not in session: return redirect(url_for('login'))
    if not check_module_active('history_menu'):
        return render_template_string(BASE_LAYOUT, title="Modul Dinonaktifkan", content='<div class="bg-red-500/10 text-red-400 p-6 rounded-2xl">Modul History dinonaktifkan.</div>')
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, kategori, judul, topik_normal, is_cached_hit, created_at FROM arsip_dokumen ORDER BY id DESC")
    history_list = cursor.fetchall()
    conn.close()

    content = f'''
    <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6">
        <div class="flex items-center justify-between mb-4">
            <div>
                <h3 class="text-base font-bold text-white">Riwayat Dokumen Administrasi & Cache Serupa</h3>
                <p class="text-xs text-slate-400 mt-0.5">Menampilkan seluruh riwayat generate dokumen oleh semua guru.</p>
            </div>
            <span class="text-xs bg-blue-600/20 text-blue-400 border border-blue-500/30 px-3 py-1 rounded-xl font-medium">Total: {len(history_list)} Dokumen</span>
        </div>
        <div class="overflow-x-auto">
            <table class="w-full text-left text-sm text-slate-300">
                <thead class="bg-slate-800/50 text-xs uppercase text-slate-400">
                    <tr><th class="p-3">ID</th><th class="p-3">Pembuat</th><th class="p-3">Kategori</th><th class="p-3">Judul / Topik</th><th class="p-3">Status Request</th><th class="p-3">Waktu</th><th class="p-3">Aksi</th></tr>
                </thead>
                <tbody class="divide-y divide-slate-800">
    '''
    for h in history_list:
        status_tag = '<span class="text-xs bg-amber-500/10 text-amber-400 border border-amber-500/20 px-2.5 py-1 rounded-full font-mono">Cache Hit (Serupa)</span>' if h[5] == 1 else '<span class="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2.5 py-1 rounded-full font-mono">Generated (Fresh)</span>'
        content += f'''
            <tr>
                <td class="p-3 font-mono text-xs text-slate-500">#{h[0]}</td>
                <td class="p-3 font-medium text-white">{h[1]}</td>
                <td class="p-3 uppercase text-xs text-blue-400">{h[2]}</td>
                <td class="p-3"><strong class="text-white block">{h[3]}</strong><span class="text-xs text-slate-400">Topik: {h[4]}</span></td>
                <td class="p-3">{status_tag}</td>
                <td class="p-3 text-xs text-slate-500">{h[6]}</td>
                <td class="p-3"><a href="/download_docx/{h[0]}" class="text-xs bg-blue-600/20 text-blue-400 border border-blue-500/30 px-3 py-1.5 rounded-lg hover:bg-blue-600 hover:text-white">Download</a></td>
            </tr>
        '''
    content += '''
                </tbody>
            </table>
        </div>
    </div>
    '''
    return render_template_string(BASE_LAYOUT, title="Riwayat Generate Dokumen", content=content)

@app.route('/manage-users', methods=['GET', 'POST'])
@app.route('/manage-users', methods=['GET', 'POST'])
def manage_users():
    if session.get('role') not in ['superadmin', 'admin']: return redirect(url_for('dashboard'))
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            admin_pass = request.form.get('admin_pass')
            cursor.execute("SELECT password FROM users WHERE id = ?", (session['user_id'],))
            current_user_pw = cursor.fetchone()[0]
            if not check_password_hash(current_user_pw, admin_pass):
                flash('Password Superadmin/Admin salah! Aksi dibatalkan.', 'error')
                return redirect(url_for('manage_users'))
                
            username = request.form['username']
            password = generate_password_hash(request.form['password'])
            nama_lengkap = request.form['nama_lengkap']
            email = request.form['email']
            role = request.form['role']
            try:
                cursor.execute("INSERT INTO users (username, password, nama_lengkap, email, role) VALUES (?, ?, ?, ?, ?)",
                               (username, password, nama_lengkap, email, role))
                conn.commit()
                log_user_activity(session['username'], "Tambah User", f"Menambahkan user baru: {username} ({role})", request.remote_addr)
                flash('User baru berhasil ditambahkan!', 'success')
            except Exception as e:
                flash(f'Gagal menambah user: {e}', 'error')
                
        elif action == 'edit':
            # Edit user without admin password confirmation as requested
            user_id = request.form['user_id']
            username = request.form['username']
            email = request.form['email']
            nama_lengkap = request.form['nama_lengkap']
            role = request.form['role']
            new_password = request.form.get('password')
            
            try:
                if new_password and new_password.strip() != '':
                    hashed_pw = generate_password_hash(new_password)
                    cursor.execute("UPDATE users SET username=?, email=?, nama_lengkap=?, role=?, password=? WHERE id=?",
                                   (username, email, nama_lengkap, role, hashed_pw, user_id))
                else:
                    cursor.execute("UPDATE users SET username=?, email=?, nama_lengkap=?, role=? WHERE id=?",
                                   (username, email, nama_lengkap, role, user_id))
                conn.commit()
                log_user_activity(session['username'], "Edit User", f"Mengubah data user ID {user_id} ({username})", request.remote_addr)
                flash('Data user berhasil diperbarui!', 'success')
            except Exception as e:
                flash(f'Gagal mengupdate user: {e}', 'error')
                
        elif action == 'delete':
            admin_pass = request.form.get('admin_pass')
            cursor.execute("SELECT password FROM users WHERE id = ?", (session['user_id'],))
            current_user_pw = cursor.fetchone()[0]
            if not check_password_hash(current_user_pw, admin_pass):
                flash('Password Superadmin/Admin salah! Aksi dibatalkan.', 'error')
                return redirect(url_for('manage_users'))
                
            user_id = request.form['user_id']
            cursor.execute("DELETE FROM users WHERE id=?", (user_id,))
            conn.commit()
            log_user_activity(session['username'], "Hapus User", f"Menghapus user ID {user_id}", request.remote_addr)
            flash('User berhasil dihapus!', 'success')

    cursor.execute("SELECT id, username, nama_lengkap, email, role FROM users")
    users = cursor.fetchall()
    conn.close()

    content = f'''
    <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 mb-8">
        <h3 class="text-base font-bold text-white mb-4">Tambah User Baru</h3>
        <form method="POST" class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <input type="hidden" name="action" value="add">
            <div>
                <label class="block text-xs font-semibold uppercase text-slate-400 mb-1">Username</label>
                <input type="text" name="username" required class="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 text-sm text-white">
            </div>
            <div>
                <label class="block text-xs font-semibold uppercase text-slate-400 mb-1">Password</label>
                <input type="password" name="password" required class="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 text-sm text-white">
            </div>
            <div>
                <label class="block text-xs font-semibold uppercase text-slate-400 mb-1">Nama Lengkap</label>
                <input type="text" name="nama_lengkap" required class="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 text-sm text-white">
            </div>
            <div>
                <label class="block text-xs font-semibold uppercase text-slate-400 mb-1">Email</label>
                <input type="email" name="email" required class="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 text-sm text-white">
            </div>
            <div>
                <label class="block text-xs font-semibold uppercase text-slate-400 mb-1">Role</label>
                <select name="role" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 text-sm text-white">
                    <option value="guru">Guru</option>
                    <option value="admin">Admin</option>
                    <option value="superadmin">Superadmin</option>
                </select>
            </div>
            <div>
                <label class="block text-xs font-semibold uppercase text-slate-400 mb-1">Password Anda (Konfirmasi)</label>
                <input type="password" name="admin_pass" required placeholder="Password Anda" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 text-sm text-white">
            </div>
            <div class="md:col-span-3">
                <button type="submit" class="bg-blue-600 hover:bg-blue-500 text-white font-medium px-5 py-2.5 rounded-xl text-sm shadow-lg shadow-blue-600/30">Tambah User</button>
            </div>
        </form>
    </div>

    <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6">
        <h3 class="text-base font-bold text-white mb-4">Daftar Seluruh User Terdaftar</h3>
        <div class="overflow-x-auto">
            <table class="w-full text-left text-sm text-slate-300">
                <thead class="bg-slate-800/50 text-xs uppercase text-slate-400">
                    <tr><th class="p-3">Username</th><th class="p-3">Nama Lengkap</th><th class="p-3">Email</th><th class="p-3">Role</th><th class="p-3">Aksi</th></tr>
                </thead>
                <tbody class="divide-y divide-slate-800">
    '''
    for u in users:
        content += f'''
            <tr>
                <td class="p-3 font-medium text-white">{u[1]}</td>
                <td class="p-3">{u[2]}</td>
                <td class="p-3 text-slate-400">{u[3]}</td>
                <td class="p-3 uppercase text-xs text-blue-400 font-semibold">{u[4]}</td>
                <td class="p-3 flex items-center space-x-2">
                    <button onclick="document.getElementById('edit_modal_{u[0]}').classList.remove('hidden')" class="text-xs bg-amber-600/20 text-amber-400 border border-amber-500/30 px-3 py-1.5 rounded-lg hover:bg-amber-600 hover:text-white">Edit</button>
                    <form method="POST" onsubmit="return confirm('Hapus user ini?');" style="display:inline;">
                        <input type="hidden" name="action" value="delete">
                        <input type="hidden" name="user_id" value="{u[0]}">
                        <input type="password" name="admin_pass" required placeholder="Password Anda" class="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-xs text-white mb-1" style="width:110px;">
                        <button type="submit" class="text-xs bg-red-600/20 text-red-400 border border-red-500/30 px-3 py-1 rounded-lg hover:bg-red-600 hover:text-white">Hapus</button>
                    </form>
                </td>
            </tr>

            <!-- Modal Edit User (Tanpa Konfirmasi Password Admin) -->
            <div id="edit_modal_{u[0]}" class="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center hidden z-50 p-4">
                <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 w-full max-w-lg shadow-2xl">
                    <div class="flex items-center justify-between mb-4">
                        <h4 class="font-bold text-white text-base">Edit User: {u[1]}</h4>
                        <button onclick="document.getElementById('edit_modal_{u[0]}').classList.add('hidden')" class="text-slate-400 hover:text-white"><i class="fa-solid fa-xmark text-lg"></i></button>
                    </div>
                    <form method="POST" class="space-y-4">
                        <input type="hidden" name="action" value="edit">
                        <input type="hidden" name="user_id" value="{u[0]}">
                        <div>
                            <label class="block text-xs uppercase text-slate-400 mb-1">Username</label>
                            <input type="text" name="username" value="{u[1]}" required class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white">
                        </div>
                        <div>
                            <label class="block text-xs uppercase text-slate-400 mb-1">Nama Lengkap</label>
                            <input type="text" name="nama_lengkap" value="{u[2]}" required class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white">
                        </div>
                        <div>
                            <label class="block text-xs uppercase text-slate-400 mb-1">Email</label>
                            <input type="email" name="email" value="{u[3]}" required class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white">
                        </div>
                        <div>
                            <label class="block text-xs uppercase text-slate-400 mb-1">Role</label>
                            <select name="role" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white">
                                <option value="guru" {"selected" if u[4] == 'guru' else ""}>Guru</option>
                                <option value="admin" {"selected" if u[4] == 'admin' else ""}>Admin</option>
                                <option value="superadmin" {"selected" if u[4] == 'superadmin' else ""}>Superadmin</option>
                            </select>
                        </div>
                        <div>
                            <label class="block text-xs uppercase text-slate-400 mb-1">Password Baru (Opsional)</label>
                            <input type="password" name="password" placeholder="Kosongkan jika tidak ingin mengubah password" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white">
                        </div>
                        <div class="flex justify-end space-x-3 pt-2">
                            <button type="button" onclick="document.getElementById('edit_modal_{u[0]}').classList.add('hidden')" class="bg-slate-800 text-slate-300 px-4 py-2 rounded-xl text-sm">Batal</button>
                            <button type="submit" class="bg-blue-600 hover:bg-blue-500 text-white font-medium px-5 py-2 rounded-xl text-sm shadow-lg">Simpan Perubahan</button>
                        </div>
                    </form>
                </div>
            </div>
        '''
    content += '''
                </tbody>
            </table>
        </div>
    </div>
    '''
    return render_template_string(BASE_LAYOUT, title="Manajemen Data User", content=content)

@app.route('/online-users')
def online_users():
    if session.get('role') not in ['superadmin', 'admin']: return redirect(url_for('dashboard'))
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT username, role, last_seen FROM online_users")
    online_list = cursor.fetchall()
    conn.close()

    content = f'''
    <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6">
        <h3 class="text-base font-bold text-white mb-4">Daftar Pengguna yang Sedang Aktif / Online</h3>
        <div class="overflow-x-auto">
            <table class="w-full text-left text-sm text-slate-300">
                <thead class="bg-slate-800/50 text-xs uppercase text-slate-400">
                    <tr><th class="p-3">Username</th><th class="p-3">Role</th><th class="p-3">Waktu Terakhir Aktif</th><th class="p-3">Status</th></tr>
                </thead>
                <tbody class="divide-y divide-slate-800">
    '''
    for o in online_list:
        content += f'<tr><td class="p-3 font-medium text-white">{o[0]}</td><td class="p-3 uppercase text-xs text-blue-400">{o[1]}</td><td class="p-3 text-xs text-slate-500">{o[2]}</td><td class="p-3"><span class="text-xs bg-emerald-500/10 text-emerald-400 px-2.5 py-1 rounded-full">Online</span></td></tr>'
    content += '''
                </tbody>
            </table>
        </div>
    </div>
    '''
    return render_template_string(BASE_LAYOUT, title="User Sedang Online", content=content)

@app.route('/superadmin/notifications', methods=['GET', 'POST'])
def manage_notifications():
    if session.get('role') != 'superadmin': return redirect(url_for('dashboard'))
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    if request.method == 'POST':
        pesan = request.form['pesan']
        cursor.execute("INSERT INTO notifications (pesan) VALUES (?)", (pesan,))
        conn.commit()
        log_user_activity(session['username'], "Update Notifikasi", "Membuat pengumuman login baru.", request.remote_addr)
        flash('Notifikasi berhasil diterbitkan!', 'success')
        
    cursor.execute("SELECT id, pesan, tanggal FROM notifications ORDER BY id DESC")
    notifs = cursor.fetchall()
    conn.close()
    
    content = f'''
    <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 mb-8 max-w-2xl">
        <h3 class="text-base font-bold text-white mb-2">Buat Pengumuman / Notifikasi Terbaru</h3>
        <form method="POST" class="space-y-4">
            <div>
                <label class="block text-xs uppercase text-slate-400 mb-1">Isi Pesan Pengumuman</label>
                <textarea name="pesan" rows="3" required class="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 text-sm text-white"></textarea>
            </div>
            <button type="submit" class="bg-blue-600 text-white px-5 py-2.5 rounded-xl text-sm shadow-lg">Terbitkan Pengumuman</button>
        </form>
    </div>
    '''
    return render_template_string(BASE_LAYOUT, title="Kelola Notifikasi Login", content=content)

@app.route('/superadmin/activity-logs')
def activity_logs():
    if session.get('role') != 'superadmin': return redirect(url_for('dashboard'))
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT username, aktivitas, detail, kota, ip_address, timestamp FROM activity_logs ORDER BY id DESC LIMIT 50")
    logs = cursor.fetchall()
    conn.close()

    content = f'''
    <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6">
        <h3 class="text-base font-bold text-white mb-2">Log Aktivitas Seluruh Pengguna</h3>
        <div class="overflow-x-auto">
            <table class="w-full text-left text-sm text-slate-300">
                <thead class="bg-slate-800/50 text-xs uppercase text-slate-400">
                    <tr><th class="p-3">Waktu</th><th class="p-3">Username</th><th class="p-3">Aktivitas</th><th class="p-3">Detail</th><th class="p-3">Kota</th><th class="p-3">IP</th></tr>
                </thead>
                <tbody class="divide-y divide-slate-800">
    '''
    for l in logs:
        content += f'<tr><td class="p-3 text-xs text-slate-500">{l[5]}</td><td class="p-3 font-medium text-white">{l[0]}</td><td class="p-3 text-xs text-blue-400">{l[1]}</td><td class="p-3 text-slate-300">{l[2]}</td><td class="p-3 text-xs text-slate-400">{l[3]}</td><td class="p-3 text-xs font-mono text-slate-400">{l[4]}</td></tr>'
    content += '</tbody></table></div></div>'
    return render_template_string(BASE_LAYOUT, title="Log Aktivitas", content=content)

@app.route('/superadmin/module-settings', methods=['GET', 'POST'])
def module_settings():
    if session.get('role') != 'superadmin': return redirect(url_for('dashboard'))
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if request.method == 'POST':
        module_key = request.form['module_key']
        status = int(request.form['status'])
        cursor.execute("UPDATE modules_status SET is_active = ? WHERE module_key = ?", (status, module_key))
        conn.commit()
        log_user_activity(session['username'], "Pengaturan Modul", f"Mengubah status {module_key} ke {status}", request.remote_addr)
        flash('Status modul diperbarui!', 'success')
    cursor.execute("SELECT module_name, module_key, is_active FROM modules_status")
    mods = cursor.fetchall()
    conn.close()

    content = '<div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-2xl"><h3 class="text-base font-bold text-white mb-4">Pengaturan Modul</h3><div class="space-y-3">'
    for m in mods:
        badge = '<span class="text-xs bg-emerald-500/10 text-emerald-400 px-3 py-1 rounded-full">Aktif</span>' if m[2] == 1 else '<span class="text-xs bg-red-500/10 text-red-400 px-3 py-1 rounded-full">Nonaktif</span>'
        toggle_val = 0 if m[2] == 1 else 1
        toggle_text = 'Matikan' if m[2] == 1 else 'Aktifkan'
        content += f'<div class="bg-slate-800/50 p-4 rounded-xl flex items-center justify-between"><div><h4 class="font-bold text-white text-sm">{m[0]}</h4><span class="text-xs text-slate-400 font-mono">{m[1]}</span></div><div class="flex items-center space-x-3">{badge}<form method="POST"><input type="hidden" name="module_key" value="{m[1]}"><input type="hidden" name="status" value="{toggle_val}"><button type="submit" class="text-xs px-3 py-1.5 rounded-lg bg-slate-700 text-white">{toggle_text}</button></form></div></div>'
    content += '</div></div>'
    return render_template_string(BASE_LAYOUT, title="Pengaturan Modul", content=content)

@app.route('/data-kelas')
def data_kelas():
    if 'user_id' not in session: return redirect(url_for('login'))
    if not check_module_active('data_kelas'):
        return render_template_string(BASE_LAYOUT, title="Dinonaktifkan", content='<div class="bg-red-500/10 text-red-400 p-6 rounded-2xl">Modul nonaktif.</div>')
    return render_template_string(BASE_LAYOUT, title="Data Kelas", content='<div class="bg-slate-900 border border-slate-800 rounded-2xl p-6"><h3 class="text-base font-bold text-white mb-4">Data Kelas & Siswa</h3><p class="text-sm text-slate-300">Modul data kelas aktif.</p></div>')

@app.route('/profil-sekolah', methods=['GET', 'POST'])
def profil_sekolah():
    if 'user_id' not in session: return redirect(url_for('login'))
    if not check_module_active('profil_sekolah'):
        return render_template_string(BASE_LAYOUT, title="Dinonaktifkan", content='<div class="bg-red-500/10 text-red-400 p-6 rounded-2xl">Modul nonaktif.</div>')
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if request.method == 'POST':
        cursor.execute("UPDATE profil_sekolah SET nama_sekolah=?, npsn=?, kepala_sekolah=?, nip_kepsek=?, nama_guru=?, nip_guru=?, alamat=? WHERE id=1",
                       (request.form['nama_sekolah'], request.form['npsn'], request.form['kepala_sekolah'], request.form['nip_kepsek'], request.form['nama_guru'], request.form['nip_guru'], request.form['alamat']))
        conn.commit()
        flash('Profil berhasil diperbarui!', 'success')
    cursor.execute("SELECT * FROM profil_sekolah WHERE id=1")
    p = cursor.fetchone()
    conn.close()

    content = f'''
    <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-2xl">
        <h3 class="text-base font-bold text-white mb-4">Profil Sekolah & Guru Pengguna</h3>
        <form method="POST" class="space-y-4">
            <div><label class="block text-xs uppercase text-slate-400 mb-1">Nama Sekolah</label><input type="text" name="nama_sekolah" value="{p[1]}" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 text-sm text-white"></div>
            <div class="grid grid-cols-2 gap-4">
                <div><label class="block text-xs uppercase text-slate-400 mb-1">NPSN</label><input type="text" name="npsn" value="{p[2]}" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 text-sm text-white"></div>
                <div><label class="block text-xs uppercase text-slate-400 mb-1">NIP Kepsek</label><input type="text" name="nip_kepsek" value="{p[4]}" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 text-sm text-white"></div>
            </div>
            <div><label class="block text-xs uppercase text-slate-400 mb-1">Nama Kepala Sekolah</label><input type="text" name="kepala_sekolah" value="{p[3]}" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 text-sm text-white"></div>
            <div class="grid grid-cols-2 gap-4">
                <div><label class="block text-xs uppercase text-slate-400 mb-1">Nama Guru</label><input type="text" name="nama_guru" value="{p[5]}" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 text-sm text-white"></div>
                <div><label class="block text-xs uppercase text-slate-400 mb-1">NIP Guru</label><input type="text" name="nip_guru" value="{p[6]}" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 text-sm text-white"></div>
            </div>
            <div><label class="block text-xs uppercase text-slate-400 mb-1">Alamat</label><textarea name="alamat" rows="2" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 text-sm text-white">{p[7]}</textarea></div>
            <button type="submit" class="w-full bg-blue-600 text-white font-medium py-3 rounded-xl shadow-lg">Simpan Profil</button>
        </form>
    </div>
    '''
    return render_template_string(BASE_LAYOUT, title="Profil Sekolah", content=content)

@app.route('/ai-generator/<menu>', methods=['GET', 'POST'])
def ai_generator(menu):
    if 'user_id' not in session: return redirect(url_for('login'))
    if not check_module_active('ai_generator'): return render_template_string(BASE_LAYOUT, title="Dinonaktifkan", content='<div class="bg-red-500/10 text-red-400 p-6 rounded-2xl">Modul nonaktif.</div>')
    
    titles = {
        'analisis_hem': 'Analisis Hari Efektif Mengajar (HEM)',
        'jurnal_mengajar': 'Jurnal Mengajar Guru',
        'silabus': 'Silabus', 'modul_ajar': 'Modul Ajar', 'lkpd': 'LKPD',
        'capaian_tujuan': 'Capaian Tujuan', 'tp_atp': 'TP & ATP',
        'prosem': 'Program Semester', 'prota': 'Program Tahunan', 'bank_soal': 'Bank Soal'
    }
    t_text = titles.get(menu, 'AI Generator')
    
    if request.method == 'POST':
        if menu == 'analisis_hem':
            tahun_ajaran = request.form.get('tahun_ajaran', '2026/2027')
            semester = request.form.get('semester', 'Ganjil')
            selected_days = request.form.getlist('hari_mengajar')
            jp_per_temu = int(request.form.get('jp_per_temu', 2))
            
            if not selected_days:
                flash('Pilih minimal satu hari mengajar aktif!', 'error')
                return redirect(url_for('ai_generator', menu='analisis_hem'))
                
            parts = tahun_ajaran.split('/')
            y1 = int(parts[0])
            y2 = int(parts[1]) if len(parts) > 1 else y1 + 1
            
            months = [(y1, 7, 'Juli'), (y1, 8, 'Agustus'), (y1, 9, 'September'), (y1, 10, 'Oktober'), (y1, 11, 'November'), (y1, 12, 'Desember')] if semester == 'Ganjil' else [(y2, 1, 'Januari'), (y2, 2, 'Februari'), (y2, 3, 'Maret'), (y2, 4, 'April'), (y2, 5, 'Mei'), (y2, 6, 'Juni')]
            day_name_map = {0: 'Senin', 1: 'Selasa', 2: 'Rabu', 3: 'Kamis', 4: 'Jumat', 5: 'Sabtu', 6: 'Minggu'}
            
            total_effective_days = 0
            total_effective_weeks = 0
            total_jp = 0
            collision_warnings = []
            report_lines = [f"ANALISIS HARI EFEKTIF MENGAJAR (HEM)", f"Tahun Ajaran: {tahun_ajaran} | Semester: {semester}", f"Hari Aktif: {', '.join(selected_days)} | JP/Pertemuan: {jp_per_temu} JP", "="*60]
            
            for year, month, mname in months:
                cal = calendar.monthcalendar(year, month)
                month_days = 0
                dates_list = []
                for week in cal:
                    week_has_teaching_day = False
                    for day_idx, day_num in enumerate(week):
                        if day_num != 0:
                            dname = day_name_map[day_idx]
                            if dname in selected_days:
                                if (year, month, day_num) in HOLIDAYS_DB:
                                    h_name = HOLIDAYS_DB[(year, month, day_num)]
                                    collision_warnings.append(f"⚠️ PERINGATAN BENTROK: Tanggal {day_num} {mname} {year} ({dname}) bertepatan dengan libur: '{h_name}'. Dikecualikan.")
                                else:
                                    month_days += 1
                                    dates_list.append(f"{day_num} {mname} {year} ({dname})")
                                    week_has_teaching_day = True
                    if week_has_teaching_day:
                        total_effective_weeks += 1
                month_jp = month_days * jp_per_temu
                total_effective_days += month_days
                total_jp += month_jp
                
                report_lines.append(f"\nBulan: {mname} {year} | Hari Efektif: {month_days} hari | JP: {month_jp} JP")
                report_lines.append(f"Daftar Tanggal: {', '.join(dates_list) if dates_list else 'Tidak ada'}")

            if collision_warnings:
                report_lines.insert(3, "\nNOTIFIKASI BENTROK LIBUR NASIONAL / HARI RAYA:")
                for cw in collision_warnings:
                    report_lines.insert(4, cw)
                flash(f"Terdeteksi {len(collision_warnings)} hari efektif berbenturan dengan hari libur nasional.", "success")
            
            report_lines.append("\n" + "="*60)
            report_lines.append(f"TOTAL: {total_effective_days} Hari | {total_effective_weeks} Minggu | {total_jp} JP")
            
            konten = "\n".join(report_lines)
            topik_normal = f"analisis_hem - {tahun_ajaran} - {semester}".strip().lower()
            judul_baru = f"Analisis HEM TA {tahun_ajaran} Semester {semester}"
            
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO arsip_dokumen (username, kategori, judul, topik_normal, konten, is_cached_hit) VALUES (?, ?, ?, ?, ?, 0)",
                           (session['username'], 'analisis_hem', judul_baru, topik_normal, konten))
            conn.commit()
            doc_id = cursor.lastrowid
            conn.close()
            flash('Analisis HEM berhasil digenerate!', 'success')
            return redirect(url_for('download_docx', doc_id=doc_id))
        else:
            topik_raw = request.form.get('topik', 'Semester Ganjil 2026/2027')
            konten = f"Dokumen {t_text} profesional berdasarkan kurikulum merdeka dengan topik: {topik_raw}."
            judul_baru = f"{t_text} - {topik_raw}"
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO arsip_dokumen (username, kategori, judul, topik_normal, konten, is_cached_hit) VALUES (?, ?, ?, ?, ?, 0)",
                           (session['username'], menu, judul_baru, topik_raw.lower(), konten))
            conn.commit()
            doc_id = cursor.lastrowid
            conn.close()
            flash('Dokumen berhasil digenerate!', 'success')
            return redirect(url_for('download_docx', doc_id=doc_id))

    if menu == 'analisis_hem':
        content = '''
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-3xl">
            <div class="mb-6 bg-blue-600/10 border border-blue-500/30 rounded-xl p-4 text-xs text-blue-300">
                <i class="fa-solid fa-calendar-days text-amber-400 mr-2 text-base"></i><strong>Kalkulator HEM & Kalender Pendidikan (2024–2028):</strong> Cek otomatis bentrok hari libur nasional / hari raya.
            </div>
            <h3 class="text-base font-bold text-white mb-4">Pengaturan Analisis Hari Efektif Mengajar</h3>
            <form method="POST" class="space-y-5">
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-xs uppercase text-slate-400 mb-1 font-semibold">Tahun Ajaran</label>
                        <select name="tahun_ajaran" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white">
                            <option value="2024/2025">2024 / 2025</option>
                            <option value="2025/2026">2025 / 2026</option>
                            <option value="2026/2027" selected>2026 / 2027</option>
                            <option value="2027/2028">2027 / 2028</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs uppercase text-slate-400 mb-1 font-semibold">Semester</label>
                        <select name="semester" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white">
                            <option value="Ganjil" selected>Ganjil (Juli - Desember)</option>
                            <option value="Genap">Genap (Januari - Juni)</option>
                        </select>
                    </div>
                </div>
                <div>
                    <label class="block text-xs uppercase text-slate-400 mb-2 font-semibold">Pilih Hari Mengajar Aktif (Checkbox)</label>
                    <div class="grid grid-cols-3 gap-3 bg-slate-800/40 p-4 rounded-xl border border-slate-700/60">
                        <label class="flex items-center space-x-2 text-sm text-slate-200"><input type="checkbox" name="hari_mengajar" value="Senin" checked class="rounded bg-slate-800 text-blue-600"><span>Senin</span></label>
                        <label class="flex items-center space-x-2 text-sm text-slate-200"><input type="checkbox" name="hari_mengajar" value="Selasa" checked class="rounded bg-slate-800 text-blue-600"><span>Selasa</span></label>
                        <label class="flex items-center space-x-2 text-sm text-slate-200"><input type="checkbox" name="hari_mengajar" value="Rabu" checked class="rounded bg-slate-800 text-blue-600"><span>Rabu</span></label>
                        <label class="flex items-center space-x-2 text-sm text-slate-200"><input type="checkbox" name="hari_mengajar" value="Kamis" checked class="rounded bg-slate-800 text-blue-600"><span>Kamis</span></label>
                        <label class="flex items-center space-x-2 text-sm text-slate-200"><input type="checkbox" name="hari_mengajar" value="Jumat" checked class="rounded bg-slate-800 text-blue-600"><span>Jumat</span></label>
                        <label class="flex items-center space-x-2 text-sm text-slate-200"><input type="checkbox" name="hari_mengajar" value="Sabtu" class="rounded bg-slate-800 text-blue-600"><span>Sabtu</span></label>
                    </div>
                </div>
                <div>
                    <label class="block text-xs uppercase text-slate-400 mb-1 font-semibold">Jumlah JP per Pertemuan</label>
                    <input type="number" name="jp_per_temu" value="2" min="1" max="10" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white">
                </div>
                <button type="submit" class="w-full bg-blue-600 hover:bg-blue-500 text-white font-medium py-3 rounded-xl shadow-lg text-sm">Hitung Analisis HEM & Download Word</button>
            </form>
        </div>
        '''
    else:
        content = f'''
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-2xl">
            <h3 class="text-base font-bold text-white mb-2">Generator: {t_text}</h3>
            <form method="POST" class="space-y-4">
                <div><label class="block text-xs uppercase text-slate-400 mb-1">Topik / Periode / Kelas</label><input type="text" name="topik" required value="Semester Ganjil 2026/2027" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 text-sm text-white"></div>
                <button type="submit" class="w-full bg-blue-600 hover:bg-blue-500 text-white font-medium py-3 rounded-xl shadow-lg text-sm">Generate & Download Word</button>
            </form>
        </div>
        '''
    return render_template_string(BASE_LAYOUT, title=t_text, content=content)

@app.route('/download_docx/<int:doc_id>')
def download_docx(doc_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT kategori, judul, konten FROM arsip_dokumen WHERE id = ?", (doc_id,))
    row = cursor.fetchone()
    cursor.execute("SELECT nama_sekolah, npsn, kepala_sekolah, nip_kepsek, nama_guru, nip_guru, alamat FROM profil_sekolah WHERE id = 1")
    profil = cursor.fetchone()
    conn.close()
    
    if not row: return redirect(url_for('dashboard'))
    cat, title, text = row
    doc = Document()
    doc.add_heading(profil[1].upper(), level=0)
    doc.add_paragraph(f"NPSN: {profil[2]} | Alamat: {profil[7]}")
    doc.add_heading(title, level=1)
    doc.add_paragraph(text)
    doc.add_paragraph(f"\nMengetahui,\nKepala Sekolah\n\n{profil[3]}\nNIP. {profil[4]}\n\nGuru Pengampu:\n{profil[5]}\nNIP. {profil[6]}")
    
    path = f"/tmp/doc_{doc_id}.docx"
    doc.save(path)
    return send_file(path, as_attachment=True, download_name=f"{cat}.docx")

@app.route('/settings/password', methods=['GET', 'POST'])
def settings_password():
    if 'user_id' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        old_p, new_p = request.form['old_password'], request.form['new_password']
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE id = ?", (session['user_id'],))
        db_p = cursor.fetchone()[0]
        if check_password_hash(db_p, old_p):
            cursor.execute("UPDATE users SET password = ? WHERE id = ?", (generate_password_hash(new_p), session['user_id']))
            conn.commit()
            conn.close()
            flash('Password diubah!', 'success')
        else:
            conn.close()
            flash('Password lama salah!', 'error')
    content = '<div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-md"><h3 class="text-base font-bold text-white mb-4">Ganti Password</h3><form method="POST" class="space-y-4"><div><label class="block text-xs uppercase text-slate-400 mb-1">Lama</label><input type="password" name="old_password" required class="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 text-sm text-white"></div><div><label class="block text-xs uppercase text-slate-400 mb-1">Baru</label><input type="password" name="new_password" required class="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 text-sm text-white"></div><button type="submit" class="bg-blue-600 text-white px-5 py-2.5 rounded-xl text-sm">Simpan</button></form></div>'
    return render_template_string(BASE_LAYOUT, title="Ganti Password", content=content)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)