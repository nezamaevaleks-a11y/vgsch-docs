from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, session, jsonify
import os
import json
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'vgsch-secret-key-2024'
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'documents')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB

# ========== ПАРОЛЬ АДМИНКИ ==========
ADMIN_PASSWORD = "1205"  # Измени на свой пароль!

# ========== ФАЙЛЫ НАСТРОЕК ==========
SETTINGS_FILE = os.path.join(os.getcwd(), 'site_settings.json')
STATS_FILE = os.path.join(os.getcwd(), 'view_stats.json')

# ========== НАСТРОЙКИ ПО УМОЛЧАНИЮ ==========
DEFAULT_SETTINGS = {
    'site_title': 'Филиал ВГСО "Северо-Запада"',
    'site_subtitle': 'База документов оперативного состава',
    'background_color': '#f8f9fa',
    'header_color': '#0d6efd',
    'categories': {
        'prikazy': 'Приказы',
        'normativka': 'Нормативная документация',
        'posobiya': 'Пособия и методички',
        'docs': 'Общая документация',
        'other': 'Другие документы'
    }
}


# ========== ФУНКЦИИ ДЛЯ РАБОТЫ С НАСТРОЙКАМИ ==========
def load_settings():
    """Загружает настройки из файла"""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return DEFAULT_SETTINGS.copy()
    return DEFAULT_SETTINGS.copy()


def save_settings(settings):
    """Сохраняет настройки в файл"""
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


def load_stats():
    """Загружает статистику просмотров"""
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_stats(stats):
    """Сохраняет статистику просмотров"""
    with open(STATS_FILE, 'w') as f:
        json.dump(stats, f)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {
        'pdf', 'doc', 'docx', 'txt', 'xls', 'xlsx', 'ppt', 'pptx',
        'jpg', 'jpeg', 'png', 'gif'
    }


def ensure_folders_exist():
    """Создаёт папки для категорий"""
    settings = load_settings()
    for category in settings['categories'].keys():
        category_path = os.path.join(app.config['UPLOAD_FOLDER'], category)
        os.makedirs(category_path, exist_ok=True)


def get_file_type(filename):
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    if ext in ['pdf']:
        return 'pdf'
    elif ext in ['jpg', 'jpeg', 'png', 'gif']:
        return 'image'
    elif ext in ['doc', 'docx']:
        return 'word'
    elif ext in ['xls', 'xlsx']:
        return 'excel'
    elif ext in ['ppt', 'pptx']:
        return 'powerpoint'
    elif ext in ['txt']:
        return 'text'
    else:
        return 'other'


def get_documents_list(category, sort_by='name'):
    """Получает список документов с возможностью сортировки"""
    category_path = os.path.join(app.config['UPLOAD_FOLDER'], category)
    documents = []
    stats = load_stats()

    if os.path.exists(category_path):
        for filename in os.listdir(category_path):
            if not filename.startswith('.'):
                file_path = os.path.join(category_path, filename)
                if os.path.isfile(file_path):
                    stat = os.stat(file_path)
                    size_mb = stat.st_size / 1024 / 1024
                    size_text = f"{round(stat.st_size / 1024, 2)} KB" if size_mb < 1 else f"{round(size_mb, 2)} MB"

                    # Получаем количество просмотров
                    view_key = f"{category}/{filename}"
                    views = stats.get(view_key, 0)

                    documents.append({
                        'name': filename,
                        'size': size_text,
                        'size_bytes': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime),
                        'modified_str': datetime.fromtimestamp(stat.st_mtime).strftime('%d.%m.%Y %H:%M'),
                        'type': get_file_type(filename),
                        'views': views
                    })

    # Сортировка
    if sort_by == 'date':
        documents.sort(key=lambda x: x['modified'], reverse=True)
    elif sort_by == 'name':
        documents.sort(key=lambda x: x['name'].lower())
    elif sort_by == 'views':
        documents.sort(key=lambda x: x['views'], reverse=True)

    return documents


# ========== КОНТЕКСТНЫЙ ПРОЦЕССОР ==========
@app.context_processor
def inject_globals():
    """Добавляет глобальные переменные во все шаблоны"""
    settings = load_settings()
    return {
        'categories': settings['categories'],
        'site_title': settings['site_title'],
        'site_subtitle': settings['site_subtitle'],
        'background_color': settings['background_color'],
        'header_color': settings['header_color']
    }


# ========== ОСНОВНЫЕ МАРШРУТЫ ==========
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/documents/<category>')
def show_documents(category):
    settings = load_settings()
    if category not in settings['categories']:
        return "Категория не найдена", 404

    sort_by = request.args.get('sort', 'name')
    documents = get_documents_list(category, sort_by)

    return render_template('category.html',
                           category=category,
                           category_name=settings['categories'][category],
                           documents=documents,
                           sort_by=sort_by)


@app.route('/download/<category>/<filename>')
def download_file(category, filename):
    return send_from_directory(
        os.path.join(app.config['UPLOAD_FOLDER'], category),
        filename,
        as_attachment=True
    )


@app.route('/view/<category>/<filename>')
def view_file(category, filename):
    # Увеличиваем счётчик просмотров
    stats = load_stats()
    view_key = f"{category}/{filename}"
    stats[view_key] = stats.get(view_key, 0) + 1
    save_stats(stats)

    file_type = get_file_type(filename)

    if file_type == 'pdf':
        return send_from_directory(
            os.path.join(app.config['UPLOAD_FOLDER'], category),
            filename
        )
    elif file_type == 'image':
        return send_from_directory(
            os.path.join(app.config['UPLOAD_FOLDER'], category),
            filename
        )
    else:
        settings = load_settings()
        return render_template('viewer.html',
                               category=category,
                               filename=filename,
                               category_name=settings['categories'][category],
                               file_type=file_type)


@app.route('/search')
def search():
    query = request.args.get('q', '').lower().strip()
    results = []
    settings = load_settings()

    if query:
        for category_key, category_name in settings['categories'].items():
            documents = get_documents_list(category_key)
            for doc in documents:
                if query in doc['name'].lower():
                    results.append({
                        **doc,
                        'category': category_key,
                        'category_name': category_name
                    })

    return render_template('search.html', query=query, results=results, count=len(results))


# ========== АДМИН-ПАНЕЛЬ ==========
@app.route('/admin')
def admin_login():
    """Страница входа в админку"""
    password = request.args.get('password', '')
    if password == ADMIN_PASSWORD:
        session['admin_logged_in'] = True
        return redirect(url_for('admin_panel'))

    return '''
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>Вход в админ-панель</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body style="background: #f0f2f5">
        <div class="container mt-5">
            <div class="row justify-content-center">
                <div class="col-md-4">
                    <div class="card shadow">
                        <div class="card-header bg-primary text-white text-center">
                            <h4>🔒 Вход в админ-панель</h4>
                        </div>
                        <div class="card-body">
                            <form method="GET">
                                <input type="password" name="password" class="form-control mb-3" placeholder="Пароль" required>
                                <button type="submit" class="btn btn-primary w-100">Войти</button>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''


@app.route('/admin/dashboard')
def admin_panel():
    """Главная админ-панели"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    settings = load_settings()
    all_documents = {}

    for category in settings['categories'].keys():
        all_documents[category] = get_documents_list(category)

    return render_template('admin.html',
                           documents=all_documents,
                           settings=settings)


@app.route('/admin/upload', methods=['POST'])
def admin_upload():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Нет доступа'})

    files = request.files.getlist('files[]')
    category = request.form.get('category')
    settings = load_settings()

    if category not in settings['categories']:
        return jsonify({'success': False, 'error': 'Неверная категория'})

    success_count = 0
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], category, filename)
            file.save(file_path)
            success_count += 1

    return jsonify({'success': True, 'message': f'Загружено {success_count} файлов'})


@app.route('/admin/delete/<category>/<filename>')
def admin_delete(category, filename):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], category, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        flash(f'Файл {filename} удалён')

    return redirect(url_for('admin_panel'))


@app.route('/admin/rename/<category>/<filename>', methods=['POST'])
def admin_rename(category, filename):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Нет доступа'})

    new_name = request.json.get('new_name', '')
    if not new_name:
        return jsonify({'success': False, 'error': 'Имя не указано'})

    old_path = os.path.join(app.config['UPLOAD_FOLDER'], category, filename)

    # Сохраняем расширение
    ext = filename.rsplit('.', 1)[-1] if '.' in filename else ''
    if '.' not in new_name and ext:
        new_name = f"{new_name}.{ext}"

    new_path = os.path.join(app.config['UPLOAD_FOLDER'], category, new_name)

    if os.path.exists(new_path):
        return jsonify({'success': False, 'error': 'Файл с таким именем уже существует'})

    os.rename(old_path, new_path)
    return jsonify({'success': True, 'message': 'Переименовано'})


@app.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    """Настройки сайта"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        settings = load_settings()

        # Обновляем основные настройки
        settings['site_title'] = request.form.get('site_title', settings['site_title'])
        settings['site_subtitle'] = request.form.get('site_subtitle', settings['site_subtitle'])
        settings['background_color'] = request.form.get('background_color', settings['background_color'])
        settings['header_color'] = request.form.get('header_color', settings['header_color'])

        # Обновляем категории
        new_categories = {}
        for key in request.form.getlist('category_keys[]'):
            name = request.form.get(f'category_name_{key}', '')
            if key and name:
                new_categories[key] = name

        if new_categories:
            settings['categories'] = new_categories

        save_settings(settings)
        flash('✅ Настройки сохранены!')
        return redirect(url_for('admin_panel'))

    settings = load_settings()
    return render_template('admin_settings.html', settings=settings)


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))


# ========== ЗАПУСК ==========
if __name__ == '__main__':
    ensure_folders_exist()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)