"""
Internship Service

Handles CRUD operations for internships.

Author: El Moujahid Marouane
Version: 1.0
"""

from typing import Optional

from .base import ServiceResult
from ..database_client import DatabaseClient
from ..logger_setup import get_logger

logger = get_logger("services.internship")


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
        page: int = 1,
        per_page: int = 25
    ) -> ServiceResult:
        """List internships with filters and pagination."""
        offset = (page - 1) * per_page
        
        items = self.db.list_internships(
            search=search,
            site=site,
            is_remote=is_remote,
            status=status,
            limit=per_page,
            offset=offset
        )
        
        # Get total count
        total = self._get_total_count('internships')
        
        return ServiceResult(success=True, data={
            'items': items,
            'page': page,
            'per_page': per_page,
            'total': total
        })
    
    def _get_total_count(self, table: str) -> Optional[int]:
        """Get total count for a table."""
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(f'SELECT COUNT(*) as c FROM {table}')
                return cur.fetchone()['c']
        except Exception:
            return None
