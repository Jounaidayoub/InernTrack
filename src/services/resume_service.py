"""
Resume Generator Service

Handles AI-powered resume generation using LLM.

Author: InternTrack
Version: 1.0
"""

import json
import logging
from typing import Dict, Any, Optional

from .base import ServiceResult
from src.database_client import DatabaseClient
from src.llm_client import LLMClient
from src.models.resume import GeneratedResume

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are an expert resume tailoring assistant. Your task is to create a tailored resume based on a job description and candidate profile.

INSTRUCTIONS:
1. Analyze the job description to identify key requirements, skills, and keywords
2. Select the most relevant experiences and projects from the candidate's profile
3. Rewrite bullet points to highlight skills and achievements that match the job requirements
4. Use action verbs and quantify achievements where possible
5. Ensure the resume is concise and impactful

OUTPUT FORMAT:
Return ONLY valid JSON with this exact structure (no markdown, no code blocks, no explanation):
{
  "header": {
    "name": "Full Name",
    "email": "email@example.com",
    "phone": "123-456-7890",
    "location": "City, State",
    "linkedin_url": "linkedin.com/in/profile",
    "github_url": "github.com/username"
  },
  "education": [
    {
      "institution": "University Name",
      "degree": "Degree Type",
      "field_of_study": "Field",
      "location": "City, State",
      "start_date": "2020",
      "end_date": "2024"
    }
  ],
  "experience": [
    {
      "company": "Company Name",
      "title": "Job Title",
      "location": "City, State",
      "start_date": "Jan 2023",
      "end_date": "Present",
      "bullets": [
        "Achievement or responsibility with metrics",
        "Another achievement tailored to job requirements"
      ]
    }
  ],
  "projects": [
    {
      "title": "Project Name",
      "tech_stack": ["Tech1", "Tech2"],
      "bullets": [
        "What you built and its impact",
        "Technical details relevant to job"
      ]
    }
  ],
  "skills": ["Skill1", "Skill2", "Skill3"]
}

IMPORTANT RULES:
- Select 2-3 most relevant experiences (not all)
- Select 2-3 most relevant projects (not all)
- Tailor bullet points to match job keywords and requirements
- Keep skills list focused on technologies mentioned in job description
- Each bullet should start with a strong action verb
- Include metrics and numbers where available
- Return ONLY the JSON object, no other text before or after"""


class ResumeService:
    """Service for AI-powered resume generation."""

    def __init__(self):
        self.db = DatabaseClient()
        self._llm = None

    @property
    def llm(self) -> LLMClient:
        """Lazy load LLM client (only when needed)."""
        if self._llm is None:
            self._llm = LLMClient()
        return self._llm

    def generate_resume(self, internship_id: int) -> ServiceResult:
        """
        Generate a tailored resume for a specific internship.

        Args:
            internship_id: ID of the internship to tailor resume for

        Returns:
            ServiceResult with generated resume JSON on success
        """
        try:
            # Get internship details
            internship = self.db.get_internship(internship_id)
            if not internship:
                return ServiceResult(
                    success=False,
                    error="Internship not found",
                    status_code=404
                )

            # Get master profile with all data
            master_profile = self.db.get_master_profile_data()
            if not master_profile or not master_profile.get('profile'):
                return ServiceResult(
                    success=False,
                    error="User profile not found. Please create your profile first.",
                    status_code=400
                )

            # Check if profile has minimum data
            if not master_profile.get('experiences') and not master_profile.get('projects'):
                return ServiceResult(
                    success=False,
                    error="Please add at least one experience or project to your profile.",
                    status_code=400
                )

            # Build user prompt with job and profile data
            user_prompt = self._build_prompt(internship, master_profile)

            # Generate resume via LLM
            logger.info(f"Generating resume for internship {internship_id}")
            response = self.llm.generate_json(SYSTEM_PROMPT, user_prompt)

            # Clean response (remove markdown code blocks if present)
            response = self._clean_json_response(response)

            # Validate with Pydantic
            try:
                resume = GeneratedResume.model_validate_json(response)
            except Exception as validation_error:
                logger.error(f"LLM returned invalid structure: {validation_error}")
                logger.debug(f"Raw response: {response[:500]}...")
                return ServiceResult(
                    success=False,
                    error=f"AI generated invalid resume format. Please try again.",
                    status_code=500
                )

            resume_json = resume.model_dump_json()

            # Save to database
            profile_id = master_profile['profile']['id']
            resume_id = self.db.save_generated_resume(
                internship_id=internship_id,
                profile_id=profile_id,
                content_json=resume_json
            )

            logger.info(f"Resume generated and saved with ID: {resume_id}")

            return ServiceResult(
                success=True,
                data={
                    'resume_id': resume_id,
                    'resume': resume.model_dump()
                }
            )

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from LLM: {e}")
            return ServiceResult(
                success=False,
                error="AI returned invalid JSON. Please try again.",
                status_code=500
            )
        except ValueError as e:
            # LLM API key not configured
            logger.error(f"LLM configuration error: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                status_code=500
            )
        except Exception as e:
            logger.exception(f"Resume generation failed: {e}")
            return ServiceResult(
                success=False,
                error=f"Failed to generate resume: {str(e)}",
                status_code=500
            )

    def _build_prompt(self, internship: Dict, master_profile: Dict) -> str:
        """
        Build the user prompt with job description and profile data.

        Args:
            internship: Internship record from database
            master_profile: Complete user profile with experiences, projects, education

        Returns:
            Formatted prompt string
        """
        # Job information
        job_info = f"""
=== JOB DESCRIPTION ===
Title: {internship.get('title', 'Unknown')}
Company: {internship.get('company_name', 'Unknown')}
Location: {internship.get('location', 'Not specified')}

Description:
{internship.get('description', 'No description available')}
"""

        if internship.get('requirements'):
            job_info += f"""
Requirements:
{internship.get('requirements')}
"""

        if internship.get('skills'):
            skills = internship.get('skills')
            if isinstance(skills, str):
                try:
                    skills = json.loads(skills)
                except:
                    pass
            if isinstance(skills, list):
                job_info += f"\nRequired Skills: {', '.join(skills)}\n"

        # User profile information
        profile = master_profile['profile']
        profile_info = f"""
=== CANDIDATE PROFILE ===
Name: {profile.get('full_name', '')}
Email: {profile.get('email', '')}
Phone: {profile.get('phone', '') or 'Not provided'}
Location: {profile.get('location', '') or 'Not provided'}
LinkedIn: {profile.get('linkedin_url', '') or 'Not provided'}
GitHub: {profile.get('github_url', '') or 'Not provided'}
Skills: {', '.join(profile.get('skills', [])) or 'Not provided'}
"""

        # Work experience
        experiences_info = "\n=== WORK EXPERIENCE ===\n"
        experiences = master_profile.get('experiences', [])
        if experiences:
            for exp in experiences:
                end_date = exp.get('end_date') or ('Present' if exp.get('is_current') else 'N/A')
                experiences_info += f"""
Company: {exp.get('company')}
Title: {exp.get('title')}
Location: {exp.get('location', 'N/A')}
Dates: {exp.get('start_date')} - {end_date}
Description: {exp.get('description', 'N/A')}
Bullet Points:
"""
                for bullet in exp.get('bullets', []):
                    experiences_info += f"  - {bullet}\n"
        else:
            experiences_info += "No work experience provided.\n"

        # Projects
        projects_info = "\n=== PROJECTS ===\n"
        projects = master_profile.get('projects', [])
        if projects:
            for proj in projects:
                tech_stack = proj.get('tech_stack', [])
                if isinstance(tech_stack, str):
                    try:
                        tech_stack = json.loads(tech_stack)
                    except:
                        tech_stack = [tech_stack]

                projects_info += f"""
Title: {proj.get('title')}
Tech Stack: {', '.join(tech_stack) if tech_stack else 'N/A'}
Description: {proj.get('description', 'N/A')}
Bullet Points:
"""
                for bullet in proj.get('bullets', []):
                    projects_info += f"  - {bullet}\n"
        else:
            projects_info += "No projects provided.\n"

        # Education
        education_info = "\n=== EDUCATION ===\n"
        education = master_profile.get('education', [])
        if education:
            for edu in education:
                education_info += f"""
Institution: {edu.get('institution')}
Degree: {edu.get('degree')}
Field: {edu.get('field_of_study', 'N/A')}
Location: {edu.get('location', 'N/A')}
Dates: {edu.get('start_date')} - {edu.get('end_date', 'Present')}
"""
        else:
            education_info += "No education provided.\n"

        # Final prompt
        return job_info + profile_info + experiences_info + projects_info + education_info

    def _clean_json_response(self, response: str) -> str:
        """
        Remove markdown code blocks and extra whitespace from LLM response.

        Args:
            response: Raw LLM response

        Returns:
            Cleaned JSON string
        """
        response = response.strip()

        # Remove markdown code blocks
        if response.startswith("```json"):
            response = response[7:]
        elif response.startswith("```"):
            response = response[3:]

        if response.endswith("```"):
            response = response[:-3]

        return response.strip()

    def save_edited_resume(self, resume_id: int, edited_json: str) -> ServiceResult:
        """
        Save user edits to a generated resume.

        Args:
            resume_id: ID of the generated resume
            edited_json: Updated resume JSON string

        Returns:
            ServiceResult indicating success/failure
        """
        try:
            # Validate JSON structure with Pydantic
            GeneratedResume.model_validate_json(edited_json)

            success = self.db.update_generated_resume(resume_id, edited_json)
            if success:
                return ServiceResult(success=True, data={'saved': True})
            return ServiceResult(
                success=False,
                error="Resume not found",
                status_code=404
            )
        except json.JSONDecodeError as e:
            return ServiceResult(
                success=False,
                error=f"Invalid JSON format: {str(e)}",
                status_code=400
            )
        except Exception as e:
            logger.exception(f"Failed to save resume: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                status_code=500
            )

    def get_resume(self, resume_id: int) -> ServiceResult:
        """
        Get a generated resume by ID.

        Args:
            resume_id: ID of the generated resume

        Returns:
            ServiceResult with resume data
        """
        try:
            resume = self.db.get_generated_resume(resume_id)
            if resume:
                # Use edited version if available, otherwise use original
                json_str = resume.get('edited_json') or resume.get('content_json')
                resume_data = json.loads(json_str)
                return ServiceResult(
                    success=True,
                    data={
                        'resume_id': resume['id'],
                        'resume': resume_data,
                        'internship_id': resume['internship_id'],
                        'created_at': resume['created_at'],
                        'has_edits': resume.get('edited_json') is not None
                    }
                )
            return ServiceResult(
                success=False,
                error="Resume not found",
                status_code=404
            )
        except Exception as e:
            logger.exception(f"Failed to get resume: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                status_code=500
            )

    def get_resume_for_internship(self, internship_id: int) -> ServiceResult:
        """
        Get the most recent resume generated for an internship.

        Args:
            internship_id: ID of the internship

        Returns:
            ServiceResult with resume data or None if not found
        """
        try:
            resume = self.db.get_resume_for_internship(internship_id)
            if resume:
                json_str = resume.get('edited_json') or resume.get('content_json')
                resume_data = json.loads(json_str)
                return ServiceResult(
                    success=True,
                    data={
                        'resume_id': resume['id'],
                        'resume': resume_data,
                        'created_at': resume['created_at']
                    }
                )
            return ServiceResult(
                success=True,
                data=None  # No resume exists yet, but that's OK
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error=str(e),
                status_code=500
            )
