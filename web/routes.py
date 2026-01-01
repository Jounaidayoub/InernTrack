"""
Flask routes for internship tracking web UI.

Handles HTTP request/response only - business logic is in src/services.py

Provides pages and JSON APIs for:
- Internships listing and detail
- Companies listing and detail
- Company enrichment and contacts
- Scrape runs (audit log)
- Database status
- CSV export

Author: El Moujahid Marouane
Version: 3.0
"""

from flask import Blueprint, render_template, request, jsonify, current_app
from src.services import (
    ServiceResult,
    InternshipService,
    CompanyService,
    ContactService,
    DatabaseService,
    ExportService,
)
import csv
import io

bp = Blueprint('main', __name__)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def service_to_response(result: ServiceResult):
    """Convert ServiceResult to Flask JSON response."""
    if result.success:
        return jsonify(result.data), result.status_code
    else:
        response = {'error': result.error}
        if result.data:
            response.update(result.data)
        return jsonify(response), result.status_code


# =============================================================================
# PAGES
# =============================================================================

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
    service = InternshipService()
    result = service.get_internship(intern_id)
    
    if not result.success:
        return render_template('404.html'), 404
    
    return render_template('internship_detail.html', internship=result.data)


@bp.route('/company/<int:company_id>')
def company_detail_page(company_id):
    """Company detail page."""
    service = CompanyService()
    result = service.get_company_detail(company_id)
    
    if not result.success:
        return render_template('404.html'), 404
    
    return render_template(
        'company_detail.html',
        company=result.data['company'],
        internships=result.data['internships'],
        contacts=result.data['contacts']
    )


@bp.route('/db')
def db_status_page():
    """Database status page."""
    service = DatabaseService()
    result = service.get_full_status()
    
    return render_template(
        'db_status.html',
        stats=result.data['stats'],
        db_file=result.data['db_file'],
        file_size=result.data['file_size'],
        page_count=result.data['page_count'],
        page_size=result.data['page_size'],
        est_bytes=result.data['estimated_bytes']
    )


# =============================================================================
# INTERNSHIPS API
# =============================================================================

@bp.route('/api/internships')
def api_internships():
    """List internships with filters and pagination."""
    # Parse request parameters
    q = request.args.get('q')
    site = request.args.get('site')
    is_remote = request.args.get('is_remote')
    status = request.args.get('status')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 25))
    
    # Convert is_remote to boolean
    if is_remote is not None:
        is_remote = is_remote.lower() in ('true', '1', 'yes')
    
    # Call service
    service = InternshipService()
    result = service.list_internships(
        search=q,
        site=site,
        is_remote=is_remote,
        status=status,
        page=page,
        per_page=per_page
    )
    
    return jsonify(result.data)


@bp.route('/api/internship/<int:intern_id>')
def api_internship_detail(intern_id):
    """Get internship details."""
    service = InternshipService()
    result = service.get_internship(intern_id)
    return service_to_response(result)


# =============================================================================
# COMPANIES API
# =============================================================================

@bp.route('/api/companies')
def api_companies():
    """List companies with filters and pagination."""
    # Parse request parameters
    q = request.args.get('q')
    industry = request.args.get('industry')
    country = request.args.get('country')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 25))
    
    # Call service
    service = CompanyService()
    result = service.list_companies(
        search=q,
        industry=industry,
        country=country,
        page=page,
        per_page=per_page
    )
    
    return jsonify(result.data)


@bp.route('/api/company/<int:company_id>')
def api_company_detail(company_id):
    """Get company details."""
    service = CompanyService()
    result = service.get_company(company_id)
    return service_to_response(result)


# =============================================================================
# COMPANY ENRICHMENT API
# =============================================================================

@bp.route('/api/company/<int:company_id>/enrich', methods=['POST'])
def api_enrich_company(company_id):
    """Enrich company data by scraping their website."""
    # Get optional website URL from request
    website_url = None
    if request.is_json and request.json:
        website_url = request.json.get('website_url')
    
    # Call service
    service = CompanyService()
    result = service.enrich_company(company_id, website_url)
    
    if result.success:
        return jsonify({
            'success': True,
            'company_id': result.data['company_id'],
            'enriched_data': result.data['enriched_data']
        })
    else:
        return jsonify({'error': result.error}), result.status_code


# =============================================================================
# CONTACTS API
# =============================================================================

@bp.route('/api/company/<int:company_id>/contacts')
def api_company_contacts(company_id):
    """Get contacts for a company."""
    service = ContactService()
    result = service.get_contacts_for_company(company_id)
    return jsonify(result.data)


@bp.route('/api/company/<int:company_id>/contacts', methods=['POST'])
def api_add_contact(company_id):
    """Add a contact to a company."""
    if not request.is_json:
        return jsonify({'error': 'JSON required'}), 400
    
    service = ContactService()
    result = service.add_contact(company_id, request.json)
    return service_to_response(result)


@bp.route('/api/contact/<int:contact_id>', methods=['DELETE'])
def api_delete_contact(contact_id):
    """Delete a contact."""
    service = ContactService()
    result = service.delete_contact(contact_id)
    
    if result.success:
        return jsonify({'success': True})
    else:
        return jsonify({'error': result.error}), result.status_code


@bp.route('/api/extract-emails', methods=['POST'])
def api_extract_emails():
    """Extract emails from provided text."""
    if not request.is_json:
        return jsonify({'error': 'JSON required'}), 400
    
    text = request.json.get('text', '')
    service = ContactService()
    result = service.extract_emails_from_text(text)
    return jsonify(result.data)


# =============================================================================
# SCRAPE RUNS API
# =============================================================================

@bp.route('/api/scrape_runs')
def api_scrape_runs():
    """List recent scrape runs."""
    limit = int(request.args.get('limit', 20))
    
    service = DatabaseService()
    result = service.list_scrape_runs(limit=limit)
    return jsonify(result.data)


# =============================================================================
# DATABASE STATUS API
# =============================================================================

@bp.route('/api/db_status')
def api_db_status():
    """Get database status and statistics."""
    service = DatabaseService()
    result = service.get_full_status()
    return jsonify(result.data)


# =============================================================================
# EXPORT
# =============================================================================

@bp.route('/export/internships.csv')
def export_internships():
    """Export internships as CSV."""
    service = ExportService()
    result = service.get_internships_for_export()
    items = result.data
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header with schema fields
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
