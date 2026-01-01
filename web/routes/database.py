"""
Database Controller

Handles database status and scrape runs API routes.

Author: El Moujahid Marouane
Version: 1.0
"""

from flask import request, jsonify

from .base import BaseController
from src.services import DatabaseService


class DatabaseController(BaseController):
    """Controller for database-related API routes."""
    
    def register_routes(self):
        """Register database routes."""
        self.bp.add_url_rule('/api/scrape_runs', 'api_scrape_runs', self.list_scrape_runs)
        self.bp.add_url_rule('/api/db_status', 'api_db_status', self.get_db_status)
    
    def list_scrape_runs(self):
        """List recent scrape runs."""
        limit = int(request.args.get('limit', 20))
        
        service = DatabaseService()
        result = service.list_scrape_runs(limit=limit)
        return jsonify(result.data)
    
    def get_db_status(self):
        """Get database status and statistics."""
        service = DatabaseService()
        result = service.get_full_status()
        return jsonify(result.data)
