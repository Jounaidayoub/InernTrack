"""
Contact Service

Handles CRUD operations for contacts and email extraction.

Author: El Moujahid Marouane
Version: 1.0
"""

from typing import Dict, Any

from .base import ServiceResult
from ..database_client import DatabaseClient
from ..company_enricher import extract_emails_with_context
from ..logger_setup import get_logger

logger = get_logger("services.contact")


class ContactService:
    """Service for contact-related operations."""
    
    def __init__(self, db: DatabaseClient = None):
        self.db = db or DatabaseClient()
    
    def get_contacts_for_company(self, company_id: int) -> ServiceResult:
        """Get all contacts for a company."""
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute('''
                SELECT id, name, email, phone, position, linkedin_url, 
                       notes, is_primary, last_contacted, created_at
                FROM contacts 
                WHERE company_id = ?
                ORDER BY is_primary DESC, created_at DESC
            ''', (company_id,))
            contacts = [dict(r) for r in cur.fetchall()]
        
        return ServiceResult(success=True, data={'contacts': contacts})
    
    def add_contact(self, company_id: int, contact_data: Dict[str, Any]) -> ServiceResult:
        """
        Add a contact to a company.
        
        Args:
            company_id: Company ID
            contact_data: Dict with email, name, phone, position, linkedin_url, notes, is_primary
            
        Returns:
            ServiceResult with contact_id
        """
        email = contact_data.get('email')
        if not email:
            return ServiceResult(success=False, error='Email required', status_code=400)
        
        name = contact_data.get('name')
        if not name:
            name = email.split('@')[0].replace('.', ' ').title()
        
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            
            # Check if contact exists
            cur.execute(
                'SELECT id FROM contacts WHERE company_id = ? AND email = ?',
                (company_id, email)
            )
            existing = cur.fetchone()
            if existing:
                return ServiceResult(
                    success=False, 
                    error='Contact already exists',
                    data={'contact_id': existing[0]},
                    status_code=409
                )
            
            # Insert
            cur.execute('''
                INSERT INTO contacts (company_id, name, email, phone, position, linkedin_url, notes, is_primary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                company_id,
                name,
                email,
                contact_data.get('phone'),
                contact_data.get('position'),
                contact_data.get('linkedin_url'),
                contact_data.get('notes'),
                contact_data.get('is_primary', False)
            ))
            conn.commit()
            contact_id = cur.lastrowid
        
        return ServiceResult(success=True, data={'contact_id': contact_id}, status_code=201)
    
    def delete_contact(self, contact_id: int) -> ServiceResult:
        """Delete a contact by ID."""
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute('DELETE FROM contacts WHERE id = ?', (contact_id,))
            conn.commit()
            if cur.rowcount == 0:
                return ServiceResult(success=False, error='Contact not found', status_code=404)
        
        return ServiceResult(success=True)
    
    def extract_emails_from_text(self, text: str) -> ServiceResult:
        """Extract emails from provided text."""
        contacts = extract_emails_with_context(text)
        return ServiceResult(success=True, data={
            'emails': [c['email'] for c in contacts],
            'contacts': contacts
        })
