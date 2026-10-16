BASE_LAYOUT = '''
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SIAKAD Multi-Role Administrasi Guru</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap'); body { font-family: 'Inter', sans-serif; }</style>
</head>
<body class="bg-slate-950 text-slate-100 flex h-screen overflow-hidden">
    <aside class="w-64 bg-slate-900 border-r border-slate-800 flex flex-col justify-between hidden md:flex">
        <div>
            <div class="p-5 border-b border-slate-800 flex items-center space-x-3">
                <div class="w-10 h-10 rounded-xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400">
                    <i class="fa-solid fa-shield-halved"></i>
                </div>
                <div>
                    <h1 class="font-bold text-sm tracking-wide text-white">SIAKAD PRO</h1>
                    <p class="text-xs text-blue-400 uppercase font-semibold">{{ session.get('role', 'user') }}</p>
                </div>
            </div>
            
            <nav class="p-4 space-y-1 overflow-y-auto max-h-[calc(100vh-140px)]">
                <a href="{{ url_for('dashboard') }}" class="flex items-center space-x-3 px-3 py-2.5 rounded-xl text-sm font-medium {% if request.endpoint == 'dashboard' %}bg-blue-600 text-white shadow-lg shadow-blue-600/30{% else %}text-slate-400 hover:bg-slate-800 hover:text-white{% endif %}">
                    <i class="fa-solid fa-chart-pie w-5"></i><span>Dashboard</span>
                </a>

                {% if session.get('role') in ['superadmin', 'admin'] %}
                <div class="pt-4 pb-2">
                    <p class="px-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Manajemen Pengguna</p>
                </div>
                <a href="{{ url_for('manage_users') }}" class="flex items-center space-x-3 px-3 py-2.5 rounded-xl text-sm font-medium {% if request.endpoint == 'manage_users' %}bg-blue-600 text-white shadow-lg shadow-blue-600/30{% else %}text-slate-400 hover:bg-slate-800 hover:text-white{% endif %}">
                    <i class="fa-solid fa-users-gear w-5"></i><span>Data User</span>
                </a>
                <a href="{{ url_for('online_users') }}" class="flex items-center space-x-3 px-3 py-2.5 rounded-xl text-sm font-medium {% if request.endpoint == 'online_users' %}bg-blue-600 text-white shadow-lg shadow-blue-600/30{% else %}text-slate-400 hover:bg-slate-800 hover:text-white{% endif %}">
                    <i class="fa-solid fa-circle-dot text-emerald-400 w-5"></i><span>User Sedang Online</span>
                </a>
                {% endif %}

                {% if session.get('role') == 'superadmin' %}
                <div class="pt-4 pb-2">
                    <p class="px-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Superadmin Kontrol</p>
                </div>
                <a href="{{ url_for('manage_notifications') }}" class="flex items-center space-x-3 px-3 py-2.5 rounded-xl text-sm font-medium {% if request.endpoint == 'manage_notifications' %}bg-blue-600 text-white shadow-lg shadow-blue-600/30{% else %}text-slate-400 hover:bg-slate-800 hover:text-white{% endif %}">
                    <i class="fa-solid fa-bullhorn w-5"></i><span>Kelola Notifikasi</span>
                </a>
                <a href="{{ url_for('activity_logs') }}" class="flex items-center space-x-3 px-3 py-2.5 rounded-xl text-sm font-medium {% if request.endpoint == 'activity_logs' %}bg-blue-600 text-white shadow-lg shadow-blue-600/30{% else %}text-slate-400 hover:bg-slate-800 hover:text-white{% endif %}">
                    <i class="fa-solid fa-clipboard-list w-5"></i><span>Log Aktivitas User</span>
                </a>
                <a href="{{ url_for('module_settings') }}" class="flex items-center space-x-3 px-3 py-2.5 rounded-xl text-sm font-medium {% if request.endpoint == 'module_settings' %}bg-blue-600 text-white shadow-lg shadow-blue-600/30{% else %}text-slate-400 hover:bg-slate-800 hover:text-white{% endif %}">
                    <i class="fa-solid fa-sliders w-5"></i><span>Pengaturan Modul</span>
                </a>
                {% endif %}

                {% if session.get('role') in ['superadmin', 'guru'] %}
                <div class="pt-4 pb-2">
                    <p class="px-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Program Akademik</p>
                </div>
                <a href="{{ url_for('data_kelas') }}" class="flex items-center space-x-3 px-3 py-2.5 rounded-xl text-sm font-medium {% if request.endpoint == 'data_kelas' %}bg-blue-600 text-white shadow-lg shadow-blue-600/30{% else %}text-slate-400 hover:bg-slate-800 hover:text-white{% endif %}">
                    <i class="fa-solid fa-users-rectangle w-5"></i><span>Data Kelas & Siswa</span>
                </a>
                <a href="{{ url_for('profil_sekolah') }}" class="flex items-center space-x-3 px-3 py-2.5 rounded-xl text-sm font-medium {% if request.endpoint == 'profil_sekolah' %}bg-blue-600 text-white shadow-lg shadow-blue-600/30{% else %}text-slate-400 hover:bg-slate-800 hover:text-white{% endif %}">
                    <i class="fa-solid fa-school w-5"></i><span>Profil Sekolah</span>
                </a>
                <a href="{{ url_for('history_menu') }}" class="flex items-center space-x-3 px-3 py-2.5 rounded-xl text-sm font-medium {% if request.endpoint == 'history_menu' %}bg-blue-600 text-white shadow-lg shadow-blue-600/30{% else %}text-slate-400 hover:bg-slate-800 hover:text-white{% endif %}">
                    <i class="fa-solid fa-clock-rotate-left w-5"></i><span>Riwayat Generate (History)</span>
                </a>

                <div class="pt-3 pb-1">
                    <p class="px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500">Generator AI & Word</p>
                </div>
                <div class="space-y-1 pl-2 border-l border-slate-800 ml-3">
                    <a href="{{ url_for('ai_generator', menu='analisis_hem') }}" class="block px-3 py-1.5 rounded-lg text-xs font-medium {% if request.view_args and request.view_args.get('menu') == 'analisis_hem' %}text-white bg-blue-600/40{% else %}text-slate-400 hover:text-white hover:bg-slate-800{% endif %}">Analisis HEM</a>
                    <a href="{{ url_for('ai_generator', menu='jurnal_mengajar') }}" class="block px-3 py-1.5 rounded-lg text-xs font-medium {% if request.view_args and request.view_args.get('menu') == 'jurnal_mengajar' %}text-white bg-blue-600/40{% else %}text-slate-400 hover:text-white hover:bg-slate-800{% endif %}">Jurnal Mengajar</a>
                    <a href="{{ url_for('ai_generator', menu='silabus') }}" class="block px-3 py-1.5 rounded-lg text-xs font-medium {% if request.view_args and request.view_args.get('menu') == 'silabus' %}text-white bg-blue-600/40{% else %}text-slate-400 hover:text-white hover:bg-slate-800{% endif %}">Silabus</a>
                    <a href="{{ url_for('ai_generator', menu='modul_ajar') }}" class="block px-3 py-1.5 rounded-lg text-xs font-medium {% if request.view_args and request.view_args.get('menu') == 'modul_ajar' %}text-white bg-blue-600/40{% else %}text-slate-400 hover:text-white hover:bg-slate-800{% endif %}">Modul Ajar</a>
                    <a href="{{ url_for('ai_generator', menu='lkpd') }}" class="block px-3 py-1.5 rounded-lg text-xs font-medium {% if request.view_args and request.view_args.get('menu') == 'lkpd' %}text-white bg-blue-600/40{% else %}text-slate-400 hover:text-white hover:bg-slate-800{% endif %}">LKPD Siswa</a>
                    <a href="{{ url_for('ai_generator', menu='capaian_tujuan') }}" class="block px-3 py-1.5 rounded-lg text-xs font-medium {% if request.view_args and request.view_args.get('menu') == 'capaian_tujuan' %}text-white bg-blue-600/40{% else %}text-slate-400 hover:text-white hover:bg-slate-800{% endif %}">Capaian Tujuan</a>
                    <a href="{{ url_for('ai_generator', menu='tp_atp') }}" class="block px-3 py-1.5 rounded-lg text-xs font-medium {% if request.view_args and request.view_args.get('menu') == 'tp_atp' %}text-white bg-blue-600/40{% else %}text-slate-400 hover:text-white hover:bg-slate-800{% endif %}">Tujuan & Alur Pembelajaran</a>
                    <a href="{{ url_for('ai_generator', menu='prosem') }}" class="block px-3 py-1.5 rounded-lg text-xs font-medium {% if request.view_args and request.view_args.get('menu') == 'prosem' %}text-white bg-blue-600/40{% else %}text-slate-400 hover:text-white hover:bg-slate-800{% endif %}">Program Semester</a>
                    <a href="{{ url_for('ai_generator', menu='prota') }}" class="block px-3 py-1.5 rounded-lg text-xs font-medium {% if request.view_args and request.view_args.get('menu') == 'prota' %}text-white bg-blue-600/40{% else %}text-slate-400 hover:text-white hover:bg-slate-800{% endif %}">Program Tahunan</a>
                    <a href="{{ url_for('ai_generator', menu='bank_soal') }}" class="block px-3 py-1.5 rounded-lg text-xs font-medium {% if request.view_args and request.view_args.get('menu') == 'bank_soal' %}text-white bg-blue-600/40{% else %}text-slate-400 hover:text-white hover:bg-slate-800{% endif %}">Bank Soal (Harian, Sumatif, STS, SAS)</a>
                </div>
                {% endif %}

                <div class="pt-4 pb-2">
                    <p class="px-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Akun</p>
                </div>
                <a href="{{ url_for('settings_password') }}" class="flex items-center space-x-3 px-3 py-2.5 rounded-xl text-sm font-medium {% if request.endpoint == 'settings_password' %}bg-blue-600 text-white shadow-lg shadow-blue-600/30{% else %}text-slate-400 hover:bg-slate-800 hover:text-white{% endif %}">
                    <i class="fa-solid fa-key w-5"></i><span>Ganti Password</span>
                </a>
            </nav>
        </div>

        <div class="p-4 border-t border-slate-800 flex items-center justify-between">
            <div class="flex items-center space-x-3 truncate">
                <div class="w-8 h-8 rounded-full bg-blue-600/20 text-blue-400 flex items-center justify-center font-bold text-xs">
                    {{ session.get('nama', 'U')[0] }}
                </div>
                <div class="truncate">
                    <p class="text-xs font-medium text-white truncate">{{ session.get('nama', 'User') }}</p>
                    <p class="text-[10px] text-blue-400 truncate uppercase">Role: {{ session.get('role') }}</p>
                </div>
            </div>
            <a href="{{ url_for('logout') }}" class="text-slate-400 hover:text-red-400 transition-colors" title="Keluar"><i class="fa-solid fa-power-off"></i></a>
        </div>
    </aside>

    <main class="flex-1 flex flex-col overflow-hidden bg-slate-950">
        <header class="h-16 border-b border-slate-800 bg-slate-900/50 backdrop-blur flex items-center justify-between px-6">
            <h2 class="text-lg font-bold text-white tracking-tight">{{ title }}</h2>
            <div class="flex items-center space-x-3">
                <span class="text-xs bg-slate-800 text-slate-300 border border-slate-700 px-3 py-1 rounded-full font-medium">Role: <span class="text-blue-400 uppercase">{{ session.get('role') }}</span></span>
            </div>
        </header>

        <div class="flex-1 overflow-y-auto p-6">
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="mb-4 p-4 rounded-xl text-sm {% if category == 'success' %}bg-emerald-500/10 border border-emerald-500/20 text-emerald-400{% else %}bg-red-500/10 border border-red-500/20 text-red-400{% endif %}">
                            {{ message }}
                        </div>
                    {% endfor %}
                {% endif %}
            {% endwith %}

            {{ content | safe }}
        </div>
    </main>
</body>
</html>
'''

LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - SIAKAD Multi-Role</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap'); body { font-family: 'Inter', sans-serif; }</style>
</head>
<body class="bg-gradient-to-br from-slate-950 via-slate-900 to-blue-950 min-h-screen flex items-center justify-center p-4">
    <div class="w-full max-w-lg bg-slate-900/90 backdrop-blur-xl border border-slate-800 rounded-2xl shadow-2xl p-8">
        <div class="text-center mb-6">
            <div class="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-blue-600/20 border border-blue-500/30 text-blue-400 text-2xl mb-3 shadow-inner">
                <i class="fa-solid fa-graduation-cap"></i>
            </div>
            <h1 class="text-2xl font-bold text-white tracking-tight">SIAKAD Multi-Role</h1>
            <p class="text-xs text-slate-400 mt-1">Superadmin, Admin, & Guru Administrasi</p>
        </div>

        {% if latest_notification %}
        <div class="mb-6 bg-blue-600/10 border border-blue-500/30 rounded-xl p-4 text-xs text-blue-300 flex items-start space-x-3">
            <i class="fa-solid fa-bullhorn text-blue-400 text-sm mt-0.5"></i>
            <div>
                <strong class="font-semibold block text-blue-200 mb-1">Pengumuman & Update Sistem:</strong>
                <p>{{ latest_notification }}</p>
            </div>
        </div>
        {% endif %}

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="mb-4 p-3 rounded-xl text-xs bg-red-500/10 border border-red-500/20 text-red-400">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <form method="POST" class="space-y-4">
            <div>
                <label class="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">Username</label>
                <input type="text" name="username" required placeholder="superadmin / admin / guru" 
                    class="w-full bg-slate-800/60 border border-slate-700/80 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500">
            </div>
            <div>
                <label class="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">Password</label>
                <input type="password" name="password" required placeholder="••••••••" 
                    class="w-full bg-slate-800/60 border border-slate-700/80 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500">
            </div>
            <button type="submit" class="w-full bg-blue-600 hover:bg-blue-500 text-white font-medium py-3 rounded-xl shadow-lg shadow-blue-600/30 transition-all text-sm">
                Masuk Sistem
            </button>
        </form>

        <div class="mt-6 pt-4 border-t border-slate-800/80 text-center text-xs text-slate-500">
            <p>Akun Demo Default:</p>
            <p class="mt-1 font-mono text-slate-400">Superadmin: superadmin / super123</p>
            <p class="font-mono text-slate-400">Admin: admin / admin123 | Guru: guru / guru123</p>
        </div>
    </div>
</body>
</html>
'''
