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
            
            # Get basic stats
            status_result = service.get_stats()
            if not status_result.success:
                return jsonify({"success": False, "error": "Failed to get stats"})
            
            stats = status_result.data
            
            # Get recent scrape runs for last run info
            runs_result = service.list_scrape_runs(limit=1)
            last_run = None
            if runs_result.success and runs_result.data.get('runs'):
                last_run = runs_result.data['runs'][0]['started_at']
            
            # Calculate success rate from recent runs
            recent_runs = service.list_scrape_runs(limit=10)
            success_rate = 0
            if recent_runs.success and recent_runs.data.get('runs'):
                runs = recent_runs.data['runs']
                completed_runs = [r for r in runs if r['status'] == 'completed']
                success_rate = (len(completed_runs) / len(runs)) * 100 if runs else 0
            
            # TODO: Implement jobs_today calculation when we have date filtering
            jobs_today = 0
            
            quick_stats = {
                "last_run": last_run,
                "jobs_today": jobs_today,
                "total_jobs": stats.get('internships', 0),
                "success_rate": round(success_rate, 1)
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
