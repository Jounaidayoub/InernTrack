"""
Internship Service

Handles CRUD operations for internships.

Author: El Moujahid Marouane
Version: 2.0
"""

from typing import Optional, List

from .base import ServiceResult
from ..database_client import DatabaseClient
from ..logger_setup import get_logger

logger = get_logger("services.internship")


# User status options for reference
USER_STATUS_OPTIONS = [
    {'value': 'new', 'label': 'New', 'color': 'gray'},
    {'value': 'interesting', 'label': 'Interesting', 'color': 'blue'},
    {'value': 'applied', 'label': 'Applied', 'color': 'green'},
    {'value': 'waiting', 'label': 'Waiting', 'color': 'yellow'},
    {'value': 'interviewing', 'label': 'Interviewing', 'color': 'purple'},
    {'value': 'rejected', 'label': 'Rejected', 'color': 'red'},
    {'value': 'offer', 'label': 'Offer', 'color': 'emerald'},
    {'value': 'ignored', 'label': 'Ignored', 'color': 'slate'},
]


class InternshipService:
    """Service for internship-related operations."""
    
    def __init__(self, db: DatabaseClient = None):
        self.db = db or DatabaseClient()
    
    def get_internship(self, intern_id: int) -> ServiceResult:
        """Get a single internship by ID."""
        internship = self.db.get_internship(intern_id)
        if not internship:
            return ServiceResult(success=False, error='Internship not found', status_code=404)
        return ServiceResult(success=True, data=internship)
    
    def list_internships(
        self,
        search: str = None,
        site: str = None,
        is_remote: bool = None,
        status: str = None,
        user_status: str = None,
        user_statuses: List[str] = None,
        company_ids: List[int] = None,
        locations: List[str] = None,
        sort_by: str = 'date_scraped',
        sort_order: str = 'desc',
        page: int = 1,
        per_page: int = 25
    ) -> ServiceResult:
        """List internships with advanced filters, sorting and pagination."""
        offset = (page - 1) * per_page
        
        items = self.db.list_internships(
            search=search,
            site=site,
            is_remote=is_remote,
            status=status,
            user_status=user_status,
            user_statuses=user_statuses,
            company_ids=company_ids,
            locations=locations,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=per_page,
            offset=offset
        )
        
        # Get total count with same filters
        total = self.db.count_internships(
            search=search,
            site=site,
            is_remote=is_remote,
            status=status,
            user_status=user_status,
            user_statuses=user_statuses,
            company_ids=company_ids,
            locations=locations
        )
        
        return ServiceResult(success=True, data={
            'items': items,
            'page': page,
            'per_page': per_page,
            'total': total
        })
    
    def update_user_status(
        self, 
        intern_id: int, 
        user_status: str,
        user_notes: str = None,
        user_rating: int = None
    ) -> ServiceResult:
        """Update user status, notes, and rating for an internship."""
        # Validate user_status
        valid_statuses = [s['value'] for s in USER_STATUS_OPTIONS]
        if user_status not in valid_statuses:
            return ServiceResult(
                success=False, 
                error=f'Invalid user_status. Must be one of: {", ".join(valid_statuses)}',
                status_code=400
            )
        
        # Validate rating if provided
        if user_rating is not None and (user_rating < 1 or user_rating > 5):
            return ServiceResult(
                success=False,
                error='Rating must be between 1 and 5',
                status_code=400
            )
        
        success = self.db.update_internship_user_status(
            intern_id, 
            user_status, 
            user_notes, 
            user_rating
        )
        
        if not success:
            return ServiceResult(success=False, error='Internship not found', status_code=404)
        
        return ServiceResult(success=True, data={
            'internship_id': intern_id,
            'user_status': user_status
        })
    
    def get_filter_options(self) -> ServiceResult:
        """Get available filter options for dropdowns."""
        options = self.db.get_filter_options()
        options['user_status_options'] = USER_STATUS_OPTIONS
        return ServiceResult(success=True, data=options)
