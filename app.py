from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
import os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'vgsch-secret-key-2024'
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'documents')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB

# Разрешенные типы файлов
ALLOWED_EXTENSIONS = {
    'pdf', 'doc', 'docx', 'txt',
    'xls', 'xlsx', 'ppt', 'pptx',
    'jpg', 'jpeg', 'png', 'gif',
    'zip', 'rar', '7z'
}

# Категории документов
CATEGORIES = {
    'prikazy': 'Приказы',
    'normativka': 'Нормативная документация',
    'posobiya': 'Пособия и методички',
    'docs': 'Общая документация',
    'other': 'Другие документы'
}


@app.context_processor
def inject_categories():
    return dict(categories=CATEGORIES)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def ensure_folders_exist():
    for category in CATEGORIES.keys():
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


@app.errorhandler(413)
def too_large(e):
    flash('Файл слишком большой! Максимальный размер: 50 MB')
    return redirect(url_for('admin_panel'))


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/documents/<category>')
def show_documents(category):
    if category not in CATEGORIES:
        return "Категория не найдена", 404

    category_path = os.path.join(app.config['UPLOAD_FOLDER'], category)
    os.makedirs(category_path, exist_ok=True)

    documents = []
    if os.path.exists(category_path):
        for filename in os.listdir(category_path):
            if not filename.startswith('.'):
                file_path = os.path.join(category_path, filename)
                if os.path.isfile(file_path):
                    stat = os.stat(file_path)
                    size_mb = stat.st_size / 1024 / 1024
                    size_text = f"{round(stat.st_size / 1024, 2)} KB" if size_mb < 1 else f"{round(size_mb, 2)} MB"
                    documents.append({
                        'name': filename,
                        'size': size_text,
                        'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%d.%m.%Y %H:%M'),
                        'type': get_file_type(filename)
                    })

    documents.sort(key=lambda x: x['name'])
    return render_template('category.html', category=category, category_name=CATEGORIES[category], documents=documents)


@app.route('/download/<category>/<filename>')
def download_file(category, filename):
    if category not in CATEGORIES:
        return "Категория не найдена", 404
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], category), filename, as_attachment=True)


@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Файл не выбран')
            return redirect(request.url)

        file = request.files['file']
        category = request.form.get('category')

        if file.filename == '':
            flash('Файл не выбран')
            return redirect(request.url)

        if category not in CATEGORIES:
            flash('Неверная категория')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], category, filename)
            file.save(file_path)
            flash(f'✅ Файл "{filename}" успешно загружен в категорию "{CATEGORIES[category]}"')
        else:
            flash('❌ Недопустимый тип файла')

    all_documents = {}
    for category in CATEGORIES.keys():
        category_path = os.path.join(app.config['UPLOAD_FOLDER'], category)
        documents = []
        if os.path.exists(category_path):
            for filename in os.listdir(category_path):
                if not filename.startswith('.'):
                    file_path = os.path.join(category_path, filename)
                    if os.path.isfile(file_path):
                        stat = os.stat(file_path)
                        size_mb = stat.st_size / 1024 / 1024
                        size_text = f"{round(stat.st_size / 1024, 2)} KB" if size_mb < 1 else f"{round(size_mb, 2)} MB"
                        documents.append({
                            'name': filename,
                            'size': size_text,
                            'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%d.%m.%Y %H:%M'),
                            'type': get_file_type(filename)
                        })
            documents.sort(key=lambda x: x['name'])
            all_documents[category] = documents
        else:
            all_documents[category] = []

    return render_template('admin.html', documents=all_documents)


@app.route('/view/<category>/<filename>')
def view_file(category, filename):
    if category not in CATEGORIES:
        return "Категория не найдена", 404
    return render_template('viewer.html', category=category, filename=filename, category_name=CATEGORIES[category])


@app.route('/admin/delete/<category>/<filename>')
def delete_file(category, filename):
    if category not in CATEGORIES:
        flash('Категория не найдена')
        return redirect(url_for('admin_panel'))

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], category, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        flash(f'🗑️ Файл "{filename}" удален')
    else:
        flash('❌ Файл не найден')

    return redirect(url_for('admin_panel'))


if __name__ == '__main__':
    ensure_folders_exist()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)