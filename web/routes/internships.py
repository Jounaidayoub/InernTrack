"""
Internships Controller

Handles internship-related API routes.

Author: El Moujahid Marouane
Version: 1.0
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
    
    def list_internships(self):
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
    
    def get_internship(self, intern_id: int):
        """Get internship details."""
        service = InternshipService()
        result = service.get_internship(intern_id)
        return self.service_to_response(result)
