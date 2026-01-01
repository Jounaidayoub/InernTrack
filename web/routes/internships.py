"""
Internships Controller

Handles internship-related API routes.

Author: El Moujahid Marouane
Version: 2.0
"""

from flask import request, jsonify

from .base import BaseController
from src.services import InternshipService


class InternshipsController(BaseController):
    """Controller for internship API routes."""
    
    def register_routes(self):
        """Register internship routes."""
        self.bp.add_url_rule('/api/internships', 'api_internships', self.list_internships)
        self.bp.add_url_rule('/api/internship/<int:intern_id>', 'api_internship_detail', self.get_internship)
        self.bp.add_url_rule('/api/internships/filters', 'api_internship_filters', self.get_filter_options)
        self.bp.add_url_rule(
            '/api/internship/<int:intern_id>/status', 
            'api_update_internship_status', 
            self.update_user_status,
            methods=['PUT', 'PATCH']
        )
    
    def list_internships(self):
        """List internships with advanced filters, sorting and pagination."""
        # Parse request parameters
        q = request.args.get('q')
        site = request.args.get('site')
        is_remote = request.args.get('is_remote')
        status = request.args.get('status')
        user_status = request.args.get('user_status')
        
        # Multi-value filters (comma-separated)
        user_statuses = request.args.get('user_statuses')
        if user_statuses:
            user_statuses = [s.strip() for s in user_statuses.split(',') if s.strip()]
        
        company_ids = request.args.get('company_ids')
        if company_ids:
            try:
                company_ids = [int(c.strip()) for c in company_ids.split(',') if c.strip()]
            except ValueError:
                company_ids = None
        
        locations = request.args.get('locations')
        if locations:
            locations = [l.strip() for l in locations.split(',') if l.strip()]
        
        # Sorting
        sort_by = request.args.get('sort_by', 'date_scraped')
        sort_order = request.args.get('sort_order', 'desc')
        
        # Pagination
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
            user_status=user_status,
            user_statuses=user_statuses,
            company_ids=company_ids,
            locations=locations,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            per_page=per_page
        )
        
        return jsonify(result.data)
    
    def get_internship(self, intern_id: int):
        """Get internship details."""
        service = InternshipService()
        result = service.get_internship(intern_id)
        return self.service_to_response(result)
    
    def get_filter_options(self):
        """Get available filter options for dropdowns."""
        service = InternshipService()
        result = service.get_filter_options()
        return jsonify(result.data)
    
    def update_user_status(self, intern_id: int):
        """Update user status for an internship."""
        if not request.is_json:
            return self.error_response('JSON required', 400)
        
        data = request.json
        user_status = data.get('user_status')
        
        if not user_status:
            return self.error_response('user_status is required', 400)
        
        service = InternshipService()
        result = service.update_user_status(
            intern_id,
            user_status,
            user_notes=data.get('user_notes'),
            user_rating=data.get('user_rating')
        )
        
        return self.service_to_response(result)
