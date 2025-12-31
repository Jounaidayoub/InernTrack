"""Flask blueprint providing pages and JSON APIs for internships and companies."""
from flask import Blueprint, render_template, request, jsonify, send_file, current_app, url_for
from src.database_client import DatabaseClient
import csv
import io
import os

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    # Home can redirect to internships dashboard
    return render_template('internships.html')

@bp.route('/internships')
def internships_page():
    return render_template('internships.html')

@bp.route('/companies')
def companies_page():
    return render_template('companies.html')

# JSON API for internships with filtering, sorting, pagination
@bp.route('/api/internships')
def api_internships():
    q = request.args.get('q')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 25))
    sort = request.args.get('sort', 'created_at')
    order = request.args.get('order', 'desc')

    # Map sort param to allowed columns
    allowed_sorts = {'company': 'company', 'created_at': 'created_at', 'application_deadline': 'application_deadline', 'location': 'location'}
    sort_col = allowed_sorts.get(sort, 'created_at')
    offset = (page - 1) * per_page

    db = DatabaseClient()
    items = db.list_internships(search=q, limit=per_page, offset=offset)

    # basic total (inefficient for large DBs but acceptable here)
    total = None
    try:
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) as c FROM internships')
        total = cur.fetchone()['c']
    finally:
        conn.close()

    return jsonify({
        'items': items,
        'page': page,
        'per_page': per_page,
        'total': total
    })

@bp.route('/api/internship/<int:intern_id>')
def api_internship_detail(intern_id):
    db = DatabaseClient()
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute('SELECT internships.*, companies.name as company FROM internships LEFT JOIN companies ON internships.company_id = companies.id WHERE internships.id = ?', (intern_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({'error': 'not found'}), 404
        return jsonify(dict(row))

@bp.route('/api/companies')
def api_companies():
    q = request.args.get('q')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 25))
    offset = (page - 1) * per_page

    db = DatabaseClient()
    items = db.list_companies(search=q, limit=per_page, offset=offset)

    total = None
    try:
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) as c FROM companies')
        total = cur.fetchone()['c']
    finally:
        conn.close()

    return jsonify({'items': items, 'page': page, 'per_page': per_page, 'total': total})

@bp.route('/api/company/<int:company_id>')
def api_company_detail(company_id):
    db = DatabaseClient()
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute('SELECT * FROM companies WHERE id = ?', (company_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({'error': 'not found'}), 404
        return jsonify(dict(row))

@bp.route('/export/internships.csv')
def export_internships():
    db = DatabaseClient()
    items = db.list_internships(limit=10000, offset=0)

    output = io.StringIO()
    writer = csv.writer(output)
    # header
    writer.writerow(['company', 'title', 'url', 'location', 'status', 'created_at'])
    for it in items:
        writer.writerow([it.get('company'), it.get('title'), it.get('url'), it.get('location'), it.get('status'), it.get('created_at')])

    output.seek(0)
    return current_app.response_class(output.read(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=internships.csv'})


@bp.route('/db')
def db_status_page():
    """Render a simple page showing database status and table counts."""
    db = DatabaseClient()
    stats = db.get_stats()

    # file size
    try:
        db_file = db.db_path
        file_size = os.path.getsize(db_file)
    except Exception:
        db_file = getattr(db, 'db_path', 'unknown')
        file_size = None

    # estimate using PRAGMA
    page_count = None
    page_size = None
    try:
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute('PRAGMA page_count')
        page_count = cur.fetchone()[0]
        cur.execute('PRAGMA page_size')
        page_size = cur.fetchone()[0]
        conn.close()
    except Exception:
        page_count = None
        page_size = None

    est_bytes = page_count * page_size if page_count and page_size else None

    return render_template('db_status.html', stats=stats, db_file=db_file, file_size=file_size, page_count=page_count, page_size=page_size, est_bytes=est_bytes)


@bp.route('/api/db_status')
def api_db_status():
    db = DatabaseClient()
    stats = db.get_stats()
    try:
        db_file = db.db_path
        file_size = os.path.getsize(db_file)
    except Exception:
        db_file = getattr(db, 'db_path', 'unknown')
        file_size = None

    page_count = None
    page_size = None
    try:
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute('PRAGMA page_count')
        page_count = cur.fetchone()[0]
        cur.execute('PRAGMA page_size')
        page_size = cur.fetchone()[0]
        conn.close()
    except Exception:
        page_count = None
        page_size = None

    est_bytes = page_count * page_size if page_count and page_size else None

    return jsonify({
        'stats': stats,
        'db_file': db_file,
        'file_size': file_size,
        'page_count': page_count,
        'page_size': page_size,
        'estimated_bytes': est_bytes
    })
