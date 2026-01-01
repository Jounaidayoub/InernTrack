"""
Companies Controller

Handles company-related API routes including enrichment.

Author: El Moujahid Marouane
Version: 1.0
"""

from flask import request, jsonify

from .base import BaseController
from src.services import CompanyService


class CompaniesController(BaseController):
    """Controller for company API routes."""
    
    def register_routes(self):
        """Register company routes."""
        self.bp.add_url_rule('/api/companies', 'api_companies', self.list_companies)
        self.bp.add_url_rule('/api/company/<int:company_id>', 'api_company_detail', self.get_company)
        self.bp.add_url_rule(
            '/api/company/<int:company_id>/enrich', 
            'api_enrich_company', 
            self.enrich_company, 
            methods=['POST']
        )
        self.bp.add_url_rule(
            '/api/companies/unenriched',
            'api_unenriched_companies',
            self.get_unenriched_companies
        )
        self.bp.add_url_rule(
            '/api/companies/enrich-batch',
            'api_batch_enrich',
            self.batch_enrich,
            methods=['POST']
        )
        self.bp.add_url_rule(
            '/api/company/<int:company_id>/reset-enrichment',
            'api_reset_enrichment',
            self.reset_enrichment,
            methods=['POST']
        )
    
    def list_companies(self):
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
    
    def get_company(self, company_id: int):
        """Get company details."""
        service = CompanyService()
        result = service.get_company(company_id)
        return self.service_to_response(result)
    
    def enrich_company(self, company_id: int):
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
            return self.error_response(result.error, result.status_code)
    
    def get_unenriched_companies(self):
        """Get list of companies that haven't been fully enriched."""
        service = CompanyService()
        result = service.get_unenriched_companies()
        return self.service_to_response(result)
    
    def batch_enrich(self):
        """
        Batch enrich multiple companies.
        
        Request body (optional):
        - company_ids: list of specific company IDs to enrich
        - limit: max number to enrich (default 10)
        """
        company_ids = None
        limit = 10
        
        if request.is_json and request.json:
            company_ids = request.json.get('company_ids')
            limit = request.json.get('limit', 10)
        
        service = CompanyService()
        result = service.batch_enrich_companies(company_ids, limit)
        
        if result.success:
            return jsonify({
                'success': True,
                **result.data
            })
        else:
            return self.error_response(result.error, result.status_code)
    
    def reset_enrichment(self, company_id: int):
        """Reset enrichment status to allow re-enrichment."""
        service = CompanyService()
        result = service.reset_enrichment_status(company_id)
        
        if result.success:
            return jsonify({
                'success': True,
                'company_id': company_id,
                'message': 'Enrichment status reset'
            })
        else:
            return self.error_response(result.error, result.status_code)
