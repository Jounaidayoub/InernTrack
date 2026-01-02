"""
Settings Controller

Handles settings page and API routes.

Author: El Moujahid Marouane
Version: 1.0
"""

from flask import request, jsonify, render_template

from .base import BaseController
from src.services import SettingsService, ScrapeService


class SettingsController(BaseController):
    """Controller for settings routes."""
    
    def register_routes(self):
        """Register settings routes."""
        # Page routes
        self.bp.add_url_rule('/settings', 'settings_page', self.settings_page)
        
        # API routes
        self.bp.add_url_rule('/api/settings', 'api_get_settings', self.get_settings)
        self.bp.add_url_rule('/api/settings', 'api_update_settings', self.update_settings, methods=['PUT', 'POST'])
        self.bp.add_url_rule('/api/settings/reset', 'api_reset_settings', self.reset_settings, methods=['POST'])
        
        # Scrape routes
        self.bp.add_url_rule('/api/scrape/start', 'api_start_scrape', self.start_scrape, methods=['POST'])
        self.bp.add_url_rule('/api/scrape/stop', 'api_stop_scrape', self.stop_scrape, methods=['POST'])
        self.bp.add_url_rule('/api/scrape/status', 'api_scrape_status', self.get_scrape_status)
        self.bp.add_url_rule('/api/scrape/logs', 'api_scrape_logs', self.get_scrape_logs)
        self.bp.add_url_rule('/api/scrape/history', 'api_scrape_history', self.get_scrape_history)
    
    def settings_page(self):
        """Render settings page."""
        service = SettingsService()
        result = service.get_settings()
        
        settings_data = result.data if result.success else {'settings': {}, 'schema': {}}
        
        return render_template('settings.html', 
                             settings=settings_data['settings'],
                             schema=settings_data.get('schema', {}))
    
    def get_settings(self):
        """Get all settings."""
        service = SettingsService()
        result = service.get_settings()
        return self.service_to_response(result)
    
    def update_settings(self):
        """Update settings."""
        if not request.is_json:
            return self.error_response('JSON required', 400)
        
        updates = request.json
        
        service = SettingsService()
        result = service.update_settings(updates)
        
        if result.success:
            return jsonify({
                'success': True,
                'updated': result.data.get('updated', [])
            })
        else:
            return self.error_response(result.error, result.status_code)
    
    def reset_settings(self):
        """Reset settings to defaults."""
        service = SettingsService()
        result = service.reset_to_defaults()
        
        if result.success:
            return jsonify({'success': True, 'message': 'Settings reset to defaults'})
        else:
            return self.error_response(result.error, result.status_code)
    
    def start_scrape(self):
        """Start a scrape run."""
        service = ScrapeService()
        result = service.start_scrape()
        
        if result.success:
            return jsonify({
                'success': True,
                'message': 'Scrape started',
                'status': result.data.get('status', {})
            })
        else:
            return self.error_response(result.error, result.status_code)
    
    def stop_scrape(self):
        """Stop the current scrape."""
        service = ScrapeService()
        result = service.stop_scrape()
        
        if result.success:
            return jsonify({'success': True, 'message': 'Stop requested'})
        else:
            return self.error_response(result.error, result.status_code)
    
    def get_scrape_status(self):
        """Get scrape status."""
        service = ScrapeService()
        result = service.get_status()
        return self.service_to_response(result)
    
    def get_scrape_logs(self):
        """Get scrape logs."""
        since_index = int(request.args.get('since', 0))
        
        service = ScrapeService()
        result = service.get_logs(since_index)
        return self.service_to_response(result)
    
    def get_scrape_history(self):
        """Get scrape history."""
        limit = int(request.args.get('limit', 20))
        
        service = ScrapeService()
        result = service.get_scrape_history(limit)
        return self.service_to_response(result)
