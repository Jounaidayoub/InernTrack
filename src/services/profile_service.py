"""
Profile Service

Handles user profile operations for resume generation.

Author: InternTrack
Version: 1.0
"""

from typing import Dict, Any
from .base import ServiceResult
from src.database_client import DatabaseClient


class ProfileService:
    """Service for user profile operations."""

    def __init__(self):
        self.db = DatabaseClient()

    def get_profile(self) -> ServiceResult:
        """Get user profile with all related data."""
        try:
            data = self.db.get_master_profile_data()
            if data:
                return ServiceResult(success=True, data=data)
            return ServiceResult(
                success=True,
                data={'profile': None, 'experiences': [], 'projects': [], 'education': []}
            )
        except Exception as e:
            return ServiceResult(success=False, error=str(e), status_code=500)

    def save_profile(self, data: Dict[str, Any]) -> ServiceResult:
        """Save or update user profile."""
        try:
            if not data.get('full_name') or not data.get('email'):
                return ServiceResult(
                    success=False,
                    error="full_name and email are required",
                    status_code=400
                )

            profile_id = self.db.save_user_profile(data)
            return ServiceResult(success=True, data={'id': profile_id})
        except Exception as e:
            return ServiceResult(success=False, error=str(e), status_code=500)

    # Experience methods
    def add_experience(self, data: Dict[str, Any]) -> ServiceResult:
        """Add a new experience entry."""
        try:
            profile = self.db.get_user_profile()
            if not profile:
                return ServiceResult(
                    success=False,
                    error="Profile must be created first",
                    status_code=400
                )
            
            exp_id = self.db.create_user_experience(profile['id'], data)
            return ServiceResult(success=True, data={'id': exp_id})
        except Exception as e:
            return ServiceResult(success=False, error=str(e), status_code=500)

    def update_experience(self, exp_id: int, data: Dict[str, Any]) -> ServiceResult:
        """Update an experience entry."""
        try:
            success = self.db.update_user_experience(exp_id, data)
            if success:
                return ServiceResult(success=True)
            return ServiceResult(success=False, error="Experience not found", status_code=404)
        except Exception as e:
            return ServiceResult(success=False, error=str(e), status_code=500)

    def delete_experience(self, exp_id: int) -> ServiceResult:
        """Delete an experience entry."""
        try:
            success = self.db.delete_user_experience(exp_id)
            if success:
                return ServiceResult(success=True)
            return ServiceResult(success=False, error="Experience not found", status_code=404)
        except Exception as e:
            return ServiceResult(success=False, error=str(e), status_code=500)

    # Project methods
    def add_project(self, data: Dict[str, Any]) -> ServiceResult:
        """Add a new project entry."""
        try:
            profile = self.db.get_user_profile()
            if not profile:
                return ServiceResult(
                    success=False,
                    error="Profile must be created first",
                    status_code=400
                )
            
            project_id = self.db.create_user_project(profile['id'], data)
            return ServiceResult(success=True, data={'id': project_id})
        except Exception as e:
            return ServiceResult(success=False, error=str(e), status_code=500)

    def update_project(self, project_id: int, data: Dict[str, Any]) -> ServiceResult:
        """Update a project entry."""
        try:
            success = self.db.update_user_project(project_id, data)
            if success:
                return ServiceResult(success=True)
            return ServiceResult(success=False, error="Project not found", status_code=404)
        except Exception as e:
            return ServiceResult(success=False, error=str(e), status_code=500)

    def delete_project(self, project_id: int) -> ServiceResult:
        """Delete a project entry."""
        try:
            success = self.db.delete_user_project(project_id)
            if success:
                return ServiceResult(success=True)
            return ServiceResult(success=False, error="Project not found", status_code=404)
        except Exception as e:
            return ServiceResult(success=False, error=str(e), status_code=500)

    # Education methods
    def add_education(self, data: Dict[str, Any]) -> ServiceResult:
        """Add a new education entry."""
        try:
            profile = self.db.get_user_profile()
            if not profile:
                return ServiceResult(
                    success=False,
                    error="Profile must be created first",
                    status_code=400
                )
            
            edu_id = self.db.create_user_education(profile['id'], data)
            return ServiceResult(success=True, data={'id': edu_id})
        except Exception as e:
            return ServiceResult(success=False, error=str(e), status_code=500)

    def update_education(self, edu_id: int, data: Dict[str, Any]) -> ServiceResult:
        """Update an education entry."""
        try:
            success = self.db.update_user_education(edu_id, data)
            if success:
                return ServiceResult(success=True)
            return ServiceResult(success=False, error="Education not found", status_code=404)
        except Exception as e:
            return ServiceResult(success=False, error=str(e), status_code=500)

    def delete_education(self, edu_id: int) -> ServiceResult:
        """Delete an education entry."""
        try:
            success = self.db.delete_user_education(edu_id)
            if success:
                return ServiceResult(success=True)
            return ServiceResult(success=False, error="Education not found", status_code=404)
        except Exception as e:
            return ServiceResult(success=False, error=str(e), status_code=500)

    # Generated Resume methods
    def save_resume_generation(self, internship_id: int, content_json: str) -> ServiceResult:
        """Save a generated resume."""
        try:
            profile = self.db.get_user_profile()
            if not profile:
                return ServiceResult(
                    success=False,
                    error="Profile must be created first",
                    status_code=400
                )
            
            resume_id = self.db.save_generated_resume(internship_id, profile['id'], content_json)
            return ServiceResult(success=True, data={'id': resume_id})
        except Exception as e:
            return ServiceResult(success=False, error=str(e), status_code=500)

    def update_resume_content(self, resume_id: int, edited_json: str) -> ServiceResult:
        """Update resume content."""
        try:
            success = self.db.update_generated_resume(resume_id, edited_json)
            if success:
                return ServiceResult(success=True)
            return ServiceResult(success=False, error="Resume not found", status_code=404)
        except Exception as e:
            return ServiceResult(success=False, error=str(e), status_code=500)

    def get_resume(self, resume_id: int) -> ServiceResult:
        """Get generated resume."""
        try:
            resume = self.db.get_generated_resume(resume_id)
            if resume:
                return ServiceResult(success=True, data=resume)
            return ServiceResult(success=False, error="Resume not found", status_code=404)
        except Exception as e:
            return ServiceResult(success=False, error=str(e), status_code=500)
    
    def get_resume_for_internship(self, internship_id: int) -> ServiceResult:
        """Get latest resume for an internship."""
        try:
            resume = self.db.get_resume_for_internship(internship_id)
            return ServiceResult(success=True, data=resume) # Can be None, which is fine
        except Exception as e:
            return ServiceResult(success=False, error=str(e), status_code=500)
