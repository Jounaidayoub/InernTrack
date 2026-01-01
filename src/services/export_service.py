"""
Export Service

Handles data export operations.

Author: El Moujahid Marouane
Version: 1.0
"""

from .base import ServiceResult
from ..database_client import DatabaseClient
from ..logger_setup import get_logger

logger = get_logger("services.export")


class ExportService:
    """Service for data export operations."""
    
    def __init__(self, db: DatabaseClient = None):
        self.db = db or DatabaseClient()
    
    def get_internships_for_export(self, limit: int = 10000) -> ServiceResult:
        """Get internships data for CSV export."""
        items = self.db.list_internships(limit=limit, offset=0)
        return ServiceResult(success=True, data=items)
