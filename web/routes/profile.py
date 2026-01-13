"""
Profile Controller

Handles user profile management routes.

Author: InternTrack
Version: 1.0
"""

from flask import request, render_template

from .base import BaseController
from src.services import ProfileService


class ProfileController(BaseController):
    """Controller for user profile routes."""

    def register_routes(self):
        """Register profile routes."""
        # Page routes
        self.bp.add_url_rule('/profile', 'profile_page', self.profile_page)

        # API routes - Profile
        self.bp.add_url_rule('/api/profile', 'api_get_profile', self.get_profile)
        self.bp.add_url_rule('/api/profile', 'api_save_profile', self.save_profile, methods=['POST'])

        # API routes - Experience
        self.bp.add_url_rule('/api/profile/experience', 'api_add_experience', self.add_experience, methods=['POST'])
        self.bp.add_url_rule('/api/profile/experience/<int:exp_id>', 'api_update_experience', self.update_experience, methods=['PUT'])
        self.bp.add_url_rule('/api/profile/experience/<int:exp_id>', 'api_delete_experience', self.delete_experience, methods=['DELETE'])

        # API routes - Project
        self.bp.add_url_rule('/api/profile/project', 'api_add_project', self.add_project, methods=['POST'])
        self.bp.add_url_rule('/api/profile/project/<int:project_id>', 'api_update_project', self.update_project, methods=['PUT'])
        self.bp.add_url_rule('/api/profile/project/<int:project_id>', 'api_delete_project', self.delete_project, methods=['DELETE'])

        # API routes - Education
        self.bp.add_url_rule('/api/profile/education', 'api_add_education', self.add_education, methods=['POST'])
        self.bp.add_url_rule('/api/profile/education/<int:edu_id>', 'api_update_education', self.update_education, methods=['PUT'])
        self.bp.add_url_rule('/api/profile/education/<int:edu_id>', 'api_delete_education', self.delete_education, methods=['DELETE'])

    def profile_page(self):
        """Render profile management page."""
        service = ProfileService()
        result = service.get_profile()
        return render_template('profile.html', data=result.data)

    def get_profile(self):
        """Get user profile with all data."""
        service = ProfileService()
        result = service.get_profile()
        return self.service_to_response(result)

    def save_profile(self):
        """Save user profile."""
        if not request.is_json:
            return self.error_response('JSON required', 400)

        service = ProfileService()
        result = service.save_profile(request.json)
        return self.service_to_response(result)

    # Experience handlers
    def add_experience(self):
        """Add new experience."""
        if not request.is_json:
            return self.error_response('JSON required', 400)

        service = ProfileService()
        result = service.add_experience(request.json)
        return self.service_to_response(result)

    def update_experience(self, exp_id: int):
        """Update experience."""
        if not request.is_json:
            return self.error_response('JSON required', 400)

        service = ProfileService()
        result = service.update_experience(exp_id, request.json)
        return self.service_to_response(result)

    def delete_experience(self, exp_id: int):
        """Delete experience."""
        service = ProfileService()
        result = service.delete_experience(exp_id)
        return self.service_to_response(result)

    # Project handlers
    def add_project(self):
        """Add new project."""
        if not request.is_json:
            return self.error_response('JSON required', 400)

        service = ProfileService()
        result = service.add_project(request.json)
        return self.service_to_response(result)

    def update_project(self, project_id: int):
        """Update project."""
        if not request.is_json:
            return self.error_response('JSON required', 400)

        service = ProfileService()
        result = service.update_project(project_id, request.json)
        return self.service_to_response(result)

    def delete_project(self, project_id: int):
        """Delete project."""
        service = ProfileService()
        result = service.delete_project(project_id)
        return self.service_to_response(result)

    # Education handlers
    def add_education(self):
        """Add new education."""
        if not request.is_json:
            return self.error_response('JSON required', 400)

        service = ProfileService()
        result = service.add_education(request.json)
        return self.service_to_response(result)

    def update_education(self, edu_id: int):
        """Update education."""
        if not request.is_json:
            return self.error_response('JSON required', 400)

        service = ProfileService()
        result = service.update_education(edu_id, request.json)
        return self.service_to_response(result)

    def delete_education(self, edu_id: int):
        """Delete education."""
        service = ProfileService()
        result = service.delete_education(edu_id)
        return self.service_to_response(result)
