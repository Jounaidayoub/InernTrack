"""
Contacts Controller

Handles contact-related API routes.

Author: El Moujahid Marouane
Version: 1.0
"""

from flask import request, jsonify

from .base import BaseController
from src.services import ContactService


class ContactsController(BaseController):
    """Controller for contact API routes."""
    
    def register_routes(self):
        """Register contact routes."""
        self.bp.add_url_rule(
            '/api/company/<int:company_id>/contacts', 
            'api_company_contacts', 
            self.get_contacts
        )
        self.bp.add_url_rule(
            '/api/company/<int:company_id>/contacts', 
            'api_add_contact', 
            self.add_contact, 
            methods=['POST']
        )
        self.bp.add_url_rule(
            '/api/contact/<int:contact_id>', 
            'api_delete_contact', 
            self.delete_contact, 
            methods=['DELETE']
        )
        self.bp.add_url_rule(
            '/api/extract-emails', 
            'api_extract_emails', 
            self.extract_emails, 
            methods=['POST']
        )
    
    def get_contacts(self, company_id: int):
        """Get contacts for a company."""
        service = ContactService()
        result = service.get_contacts_for_company(company_id)
        return jsonify(result.data)
    
    def add_contact(self, company_id: int):
        """Add a contact to a company."""
        if not request.is_json:
            return self.error_response('JSON required', 400)
        
        service = ContactService()
        result = service.add_contact(company_id, request.json)
        return self.service_to_response(result)
    
    def delete_contact(self, contact_id: int):
        """Delete a contact."""
        service = ContactService()
        result = service.delete_contact(contact_id)
        
        if result.success:
            return jsonify({'success': True})
        else:
            return self.error_response(result.error, result.status_code)
    
    def extract_emails(self):
        """Extract emails from provided text."""
        if not request.is_json:
            return self.error_response('JSON required', 400)
        
        text = request.json.get('text', '')
        service = ContactService()
        result = service.extract_emails_from_text(text)
        return jsonify(result.data)
