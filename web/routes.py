"""
Flask routes for internship tracking web UI.

Provides pages and JSON APIs for:
- Internships listing and detail
- Companies listing and detail
- Scrape runs (audit log)
- Database status
- CSV export

Author: El Moujahid Marouane
Version: 2.0
"""

from flask import Blueprint, render_template, request, jsonify, current_app
from src.database_client import DatabaseClient
import csv
import io
import os

bp = Blueprint('main', __name__)


# ============================================================================
# PAGES
# ============================================================================

@bp.route('/')
def index():
    """Home page - redirects to internships."""
    return render_template('internships.html')


@bp.route('/internships')
def internships_page():
    """Internships listing page."""
    return render_template('internships.html')


@bp.route('/companies')
def companies_page():
    """Companies listing page."""
    return render_template('companies.html')


@bp.route('/internship/<int:intern_id>')
def internship_detail_page(intern_id):
    """Internship detail page."""
    db = DatabaseClient()
    internship = db.get_internship(intern_id)
    if not internship:
        return render_template('404.html'), 404
    return render_template('internship_detail.html', internship=internship)


@bp.route('/company/<int:company_id>')
def company_detail_page(company_id):
    """Company detail page."""
    db = DatabaseClient()
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute('SELECT * FROM companies WHERE id = ?', (company_id,))
        row = cur.fetchone()
        if not row:
            return render_template('404.html'), 404
        company = dict(row)
        
        # Get internships for this company
        cur.execute('''
            SELECT id, title, location, status, is_remote, date_posted
            FROM internships 
            WHERE company_id = ?
            ORDER BY date_scraped DESC
        ''', (company_id,))
        internships = [dict(r) for r in cur.fetchall()]
        
    return render_template('company_detail.html', company=company, internships=internships)


@bp.route('/db')
def db_status_page():
    """Database status page."""
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
        pass

    est_bytes = page_count * page_size if page_count and page_size else None

    return render_template(
        'db_status.html', 
        stats=stats, 
        db_file=db_file, 
        file_size=file_size, 
        page_count=page_count, 
        page_size=page_size, 
        est_bytes=est_bytes
    )


# ============================================================================
# INTERNSHIPS API
# ============================================================================

@bp.route('/api/internships')
def api_internships():
    """List internships with filters and pagination."""
    q = request.args.get('q')
    site = request.args.get('site')
    is_remote = request.args.get('is_remote')
    status = request.args.get('status')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 25))

    # Convert is_remote to boolean
    if is_remote is not None:
        is_remote = is_remote.lower() in ('true', '1', 'yes')

    offset = (page - 1) * per_page

    db = DatabaseClient()
    items = db.list_internships(
        search=q,
        site=site,
        is_remote=is_remote,
        status=status,
        limit=per_page,
        offset=offset
    )

    # Get total count
    total = None
    try:
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) as c FROM internships')
        total = cur.fetchone()['c']
        conn.close()
    except Exception:
        pass

    return jsonify({
        'items': items,
        'page': page,
        'per_page': per_page,
        'total': total
    })


@bp.route('/api/internship/<int:intern_id>')
def api_internship_detail(intern_id):
    """Get internship details."""
    db = DatabaseClient()
    internship = db.get_internship(intern_id)
    if not internship:
        return jsonify({'error': 'not found'}), 404
    return jsonify(internship)


# ============================================================================
# COMPANIES API
# ============================================================================

@bp.route('/api/companies')
def api_companies():
    """List companies with filters and pagination."""
    q = request.args.get('q')
    industry = request.args.get('industry')
    country = request.args.get('country')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 25))
    offset = (page - 1) * per_page

    db = DatabaseClient()
    items = db.list_companies(
        search=q,
        industry=industry,
        country=country,
        limit=per_page,
        offset=offset
    )

    total = None
    try:
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) as c FROM companies')
        total = cur.fetchone()['c']
        conn.close()
    except Exception:
        pass

    return jsonify({
        'items': items,
        'page': page,
        'per_page': per_page,
        'total': total
    })


@bp.route('/api/company/<int:company_id>')
def api_company_detail(company_id):
    """Get company details."""
    db = DatabaseClient()
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute('SELECT * FROM companies WHERE id = ?', (company_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({'error': 'not found'}), 404
        return jsonify(dict(row))


# ============================================================================
# SCRAPE RUNS API
# ============================================================================

@bp.route('/api/scrape_runs')
def api_scrape_runs():
    """List recent scrape runs."""
    limit = int(request.args.get('limit', 20))
    db = DatabaseClient()
    runs = db.list_scrape_runs(limit=limit)
    return jsonify({'items': runs})


# ============================================================================
# DATABASE STATUS API
# ============================================================================

@bp.route('/api/db_status')
def api_db_status():
    """Get database status and statistics."""
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
        pass

    est_bytes = page_count * page_size if page_count and page_size else None

    return jsonify({
        'stats': stats,
        'db_file': db_file,
        'file_size': file_size,
        'page_count': page_count,
        'page_size': page_size,
        'estimated_bytes': est_bytes
    })


# ============================================================================
# EXPORT
# ============================================================================

@bp.route('/export/internships.csv')
def export_internships():
    """Export internships as CSV."""
    db = DatabaseClient()
    items = db.list_internships(limit=10000, offset=0)

    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header with new schema fields
    writer.writerow([
        'company_name', 'title', 'job_url', 'location', 'site', 
        'is_remote', 'status', 'date_posted', 'date_scraped'
    ])
    
    for it in items:
        writer.writerow([
            it.get('company_name'),
            it.get('title'),
            it.get('job_url'),
            it.get('location'),
            it.get('site'),
            it.get('is_remote'),
            it.get('status'),
            it.get('date_posted'),
            it.get('date_scraped')
        ])

    output.seek(0)
    return current_app.response_class(
        output.read(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=internships.csv'}
    )
