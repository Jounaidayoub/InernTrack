"""
Export Controller

Handles data export routes.

Author: El Moujahid Marouane
Version: 1.0
"""

import csv
import io

from flask import current_app

from .base import BaseController
from src.services import ExportService


class ExportController(BaseController):
    """Controller for export routes."""
    
    def register_routes(self):
        """Register export routes."""
        self.bp.add_url_rule('/export/internships.csv', 'export_internships', self.export_internships_csv)
    
    def export_internships_csv(self):
        """Export internships as CSV."""
        service = ExportService()
        result = service.get_internships_for_export()
        items = result.data
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header with schema fields
        writer.writerow([
            'company_name', 'title', 'job_url', 'location', 'site',
            'is_remote', 'status', 'date_posted', 'date_scraped'
        ])
        
        for it in items:
            writer.writerow([
                it.get('company_name'),
                it.get('title'),
                it.get('job_url'),
                it.get('location'),
                it.get('site'),
                it.get('is_remote'),
                it.get('status'),
                it.get('date_posted'),
                it.get('date_scraped')
            ])
        
        output.seek(0)
        return current_app.response_class(
            output.read(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=internships.csv'}
        )
