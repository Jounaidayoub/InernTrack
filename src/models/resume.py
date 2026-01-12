"""
Pydantic models for resume generation.

These models serve two purposes:
1. Database record representation (UserProfile, UserExperience, etc.)
2. LLM output validation (GeneratedResume and nested models)

Author: InternTrack
Version: 1.0
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ============================================================================
# LLM OUTPUT MODELS (for validating JSON from LLM)
# ============================================================================

class ResumeHeader(BaseModel):
    """Header section of generated resume."""
    name: str
    email: str
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None


class Education(BaseModel):
    """Education entry in generated resume."""
    institution: str
    degree: str
    field_of_study: Optional[str] = None
    location: Optional[str] = None
    start_date: str
    end_date: Optional[str] = None


class Experience(BaseModel):
    """Experience entry in generated resume."""
    company: str
    title: str
    location: Optional[str] = None
    start_date: str
    end_date: Optional[str] = None
    bullets: list[str]


class Project(BaseModel):
    """Project entry in generated resume."""
    title: str
    tech_stack: list[str]
    bullets: list[str]


class GeneratedResume(BaseModel):
    """Complete resume structure returned by LLM."""
    header: ResumeHeader
    education: list[Education]
    experience: list[Experience]
    projects: list[Project]
    skills: list[str]


# ============================================================================
# DATABASE RECORD MODELS (for representing DB rows)
# ============================================================================

class UserProfile(BaseModel):
    """User profile database record."""
    id: Optional[int] = None
    full_name: str
    email: str
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    skills: list[str] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserExperience(BaseModel):
    """User experience database record."""
    id: Optional[int] = None
    user_profile_id: Optional[int] = None
    company: str
    title: str
    location: Optional[str] = None
    start_date: str
    end_date: Optional[str] = None
    is_current: bool = False
    description: Optional[str] = None
    bullets: list[str] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserProject(BaseModel):
    """User project database record."""
    id: Optional[int] = None
    user_profile_id: Optional[int] = None
    title: str
    project_url: Optional[str] = None
    repo_url: Optional[str] = None
    description: Optional[str] = None
    tech_stack: list[str] = []
    bullets: list[str] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserEducation(BaseModel):
    """User education database record."""
    id: Optional[int] = None
    user_profile_id: Optional[int] = None
    institution: str
    degree: str
    field_of_study: Optional[str] = None
    location: Optional[str] = None
    start_date: str
    end_date: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
