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
        self.bp.add_url_rule('/api/stats/quick', 'api_quick_stats', self.get_quick_stats)
    
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
    
    def get_quick_stats(self):
        """Get quick statistics for the scrape page dashboard."""
        try:
            service = DatabaseService()
            result = service.get_quick_stats()
            
            if not result.success:
                return jsonify({"success": False, "error": result.error or "Failed to get stats"})
            
            stats = result.data
            
            # Format response for frontend
            quick_stats = {
                "last_run": stats['last_run']['started_at'] if stats.get('last_run') else None,
                "last_run_status": stats['last_run']['status'] if stats.get('last_run') else None,
                "jobs_today": stats.get('jobs_today', 0),
                "total_jobs": stats.get('total_jobs', 0),
                "success_rate": stats.get('success_rate_today', 0),
                "total_scrapes_today": stats.get('total_scrapes_today', 0)
            }
            
            return jsonify({
                "success": True,
                "data": quick_stats
            })
            
        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e)
            })
