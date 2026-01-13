"""
Resume Controller

Handles resume generation API routes.

Author: InternTrack
Version: 1.0
"""

import json
from flask import request, render_template

from .base import BaseController
from src.services import ResumeService, ProfileService


class ResumeController(BaseController):
    """Controller for resume generation routes."""

    def register_routes(self):
        """Register resume routes."""
        self.bp.add_url_rule(
            '/api/resume/generate/<int:internship_id>',
            'api_generate_resume',
            self.generate_resume,
            methods=['POST']
        )
        self.bp.add_url_rule(
            '/api/resume/<int:resume_id>',
            'api_get_resume',
            self.get_resume
        )
        self.bp.add_url_rule(
            '/api/resume/<int:resume_id>',
            'api_save_resume',
            self.save_resume,
            methods=['PUT']
        )
        self.bp.add_url_rule(
            '/api/resume/internship/<int:internship_id>',
            'api_get_resume_for_internship',
            self.get_resume_for_internship
        )
        self.bp.add_url_rule(
            '/resume/<int:resume_id>',
            'view_resume',
            self.view_resume
        )

    def generate_resume(self, internship_id: int):
        """Generate a tailored resume for an internship."""
        service = ResumeService()
        result = service.generate_resume(internship_id)
        return self.service_to_response(result)

    def get_resume(self, resume_id: int):
        """Get a generated resume by ID."""
        service = ResumeService()
        result = service.get_resume(resume_id)
        return self.service_to_response(result)

    def save_resume(self, resume_id: int):
        """Save edited resume."""
        if not request.is_json:
            return self.error_response('JSON required', 400)

        # Convert resume dict back to JSON string for storage
        edited_json = json.dumps(request.json.get('resume', {}))

        service = ResumeService()
        result = service.save_edited_resume(resume_id, edited_json)
        return self.service_to_response(result)

    def get_resume_for_internship(self, internship_id: int):
        """Get existing resume for an internship (if any)."""
        service = ResumeService()
        result = service.get_resume_for_internship(internship_id)
        return self.service_to_response(result)

    def view_resume(self, resume_id: int):
        """View a generated resume."""
        service = ResumeService()
        result = service.get_resume(resume_id)
        if not result.success:
            return render_template('404.html'), 404
        
        resume_data = result.data['resume']
        
        return render_template('resume.html', resume=resume_data)
