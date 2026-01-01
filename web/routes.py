"""
Flask routes for internship tracking web UI.

Provides pages and JSON APIs for:
- Internships listing and detail
- Companies listing and detail
- Company enrichment and contacts
- Scrape runs (audit log)
- Database status
- CSV export

Author: El Moujahid Marouane
Version: 2.1
"""

from flask import Blueprint, render_template, request, jsonify, current_app
from src.database_client import DatabaseClient
from src.company_enricher import CompanyEnricher, extract_emails_with_context
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
        
        # Get contacts for this company
        cur.execute('''
            SELECT id, name, email, phone, position, linkedin_url, notes, is_primary, last_contacted
            FROM contacts 
            WHERE company_id = ?
            ORDER BY is_primary DESC, created_at DESC
        ''', (company_id,))
        contacts = [dict(r) for r in cur.fetchall()]
        
    return render_template('company_detail.html', company=company, internships=internships, contacts=contacts)


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
# COMPANY ENRICHMENT API
# ============================================================================

@bp.route('/api/company/<int:company_id>/enrich', methods=['POST'])
def api_enrich_company(company_id):
    """
    Enrich company data by scraping their website.
    
    Fetches:
    - Description from /about page
    - Emails from /contact page
    - Social media links
    - Careers page URL
    """
    db = DatabaseClient()
    
    # Get company
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute('SELECT * FROM companies WHERE id = ?', (company_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({'error': 'Company not found'}), 404
        company = dict(row)
    
    # Get website URL
    website_url = request.json.get('website_url') if request.is_json else None
    website_url = website_url or company.get('website') or company.get('company_url')
    
    if not website_url:
        return jsonify({'error': 'No website URL available for this company'}), 400
    
    # Enrich
    enricher = CompanyEnricher(db_client=db)
    try:
        result = enricher.enrich_company(company_id, website_url)
        return jsonify({
            'success': True,
            'company_id': company_id,
            'enriched_data': result
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/company/<int:company_id>/contacts')
def api_company_contacts(company_id):
    """Get contacts for a company."""
    db = DatabaseClient()
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute('''
            SELECT id, name, email, phone, position, linkedin_url, 
                   notes, is_primary, last_contacted, created_at
            FROM contacts 
            WHERE company_id = ?
            ORDER BY is_primary DESC, created_at DESC
        ''', (company_id,))
        contacts = [dict(r) for r in cur.fetchall()]
    return jsonify({'contacts': contacts})


@bp.route('/api/company/<int:company_id>/contacts', methods=['POST'])
def api_add_contact(company_id):
    """Add a contact to a company."""
    if not request.is_json:
        return jsonify({'error': 'JSON required'}), 400
    
    data = request.json
    email = data.get('email')
    name = data.get('name', email.split('@')[0].replace('.', ' ').title() if email else 'Unknown')
    
    if not email:
        return jsonify({'error': 'Email required'}), 400
    
    db = DatabaseClient()
    with db.get_connection() as conn:
        cur = conn.cursor()
        
        # Check if contact exists
        cur.execute(
            'SELECT id FROM contacts WHERE company_id = ? AND email = ?',
            (company_id, email)
        )
        existing = cur.fetchone()
        if existing:
            return jsonify({'error': 'Contact already exists', 'contact_id': existing[0]}), 409
        
        # Insert
        cur.execute('''
            INSERT INTO contacts (company_id, name, email, phone, position, linkedin_url, notes, is_primary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            company_id,
            name,
            email,
            data.get('phone'),
            data.get('position'),
            data.get('linkedin_url'),
            data.get('notes'),
            data.get('is_primary', False)
        ))
        conn.commit()
        contact_id = cur.lastrowid
    
    return jsonify({'success': True, 'contact_id': contact_id}), 201


@bp.route('/api/contact/<int:contact_id>', methods=['DELETE'])
def api_delete_contact(contact_id):
    """Delete a contact."""
    db = DatabaseClient()
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute('DELETE FROM contacts WHERE id = ?', (contact_id,))
        conn.commit()
        if cur.rowcount == 0:
            return jsonify({'error': 'Contact not found'}), 404
    return jsonify({'success': True})


@bp.route('/api/extract-emails', methods=['POST'])
def api_extract_emails():
    """Extract emails from provided text."""
    if not request.is_json:
        return jsonify({'error': 'JSON required'}), 400
    
    text = request.json.get('text', '')
    contacts = extract_emails_with_context(text)
    
    return jsonify({
        'emails': [c['email'] for c in contacts],
        'contacts': contacts
    })


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
