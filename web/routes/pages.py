"""
Pages Controller

Handles HTML page routes.

Author: El Moujahid Marouane
Version: 1.0
"""

from flask import render_template

from .base import BaseController
from src.services import InternshipService, CompanyService, DatabaseService


class PagesController(BaseController):
    """Controller for HTML page routes."""
    
    def register_routes(self):
        """Register page routes."""
        self.bp.add_url_rule('/', 'index', self.index)
        self.bp.add_url_rule('/internships', 'internships_page', self.internships_page)
        self.bp.add_url_rule('/companies', 'companies_page', self.companies_page)
        self.bp.add_url_rule('/internship/<int:intern_id>', 'internship_detail_page', self.internship_detail_page)
        self.bp.add_url_rule('/company/<int:company_id>', 'company_detail_page', self.company_detail_page)
        self.bp.add_url_rule('/db', 'db_status_page', self.db_status_page)
    
    def index(self):
        """Home page - redirects to internships."""
        return render_template('internships.html')
    
    def internships_page(self):
        """Internships listing page."""
        return render_template('internships.html')
    
    def companies_page(self):
        """Companies listing page."""
        return render_template('companies.html')
    
    def internship_detail_page(self, intern_id: int):
        """Internship detail page."""
        service = InternshipService()
        result = service.get_internship(intern_id)
        
        if not result.success:
            return render_template('404.html'), 404
        
        return render_template('internship_detail.html', internship=result.data)
    
    def company_detail_page(self, company_id: int):
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
    
    def db_status_page(self):
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
