"""
Database Service

Handles database status and statistics.

Author: El Moujahid Marouane
Version: 1.0
"""

import os

from .base import ServiceResult
from ..database_client import DatabaseClient
from ..logger_setup import get_logger

logger = get_logger("services.database")


class DatabaseService:
    """Service for database status and statistics."""
    
    def __init__(self, db: DatabaseClient = None):
        self.db = db or DatabaseClient()
    
    def get_stats(self) -> ServiceResult:
        """Get database statistics."""
        stats = self.db.get_stats()
        return ServiceResult(success=True, data=stats)
    
    def get_full_status(self) -> ServiceResult:
        """Get comprehensive database status."""
        stats = self.db.get_stats()
        
        try:
            db_file = self.db.db_path
            file_size = os.path.getsize(db_file)
        except Exception:
            db_file = getattr(self.db, 'db_path', 'unknown')
            file_size = None
        
        page_count = None
        page_size = None
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute('PRAGMA page_count')
                page_count = cur.fetchone()[0]
                cur.execute('PRAGMA page_size')
                page_size = cur.fetchone()[0]
        except Exception:
            pass
        
        est_bytes = page_count * page_size if page_count and page_size else None
        
        return ServiceResult(success=True, data={
            'stats': stats,
            'db_file': db_file,
            'file_size': file_size,
            'page_count': page_count,
            'page_size': page_size,
            'estimated_bytes': est_bytes
        })
    
    def list_scrape_runs(self, limit: int = 20) -> ServiceResult:
        """List recent scrape runs."""
        runs = self.db.list_scrape_runs(limit=limit)
        return ServiceResult(success=True, data={'items': runs})
