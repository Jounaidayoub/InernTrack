"""
Company Service

Handles CRUD operations for companies and enrichment.

Author: El Moujahid Marouane
Version: 1.0
"""

from datetime import datetime
from typing import Optional

from .base import ServiceResult
from ..database_client import DatabaseClient
from ..company_enricher import CompanyEnricher
from ..logger_setup import get_logger

logger = get_logger("services.company")


class CompanyService:
    """Service for company-related operations."""
    
    def __init__(self, db: DatabaseClient = None):
        self.db = db or DatabaseClient()
    
    def get_company(self, company_id: int) -> ServiceResult:
        """Get a single company by ID."""
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT * FROM companies WHERE id = ?', (company_id,))
            row = cur.fetchone()
            if not row:
                return ServiceResult(success=False, error='Company not found', status_code=404)
            return ServiceResult(success=True, data=dict(row))
    
    def get_company_detail(self, company_id: int) -> ServiceResult:
        """Get company with internships and contacts."""
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            
            # Get company
            cur.execute('SELECT * FROM companies WHERE id = ?', (company_id,))
            row = cur.fetchone()
            if not row:
                return ServiceResult(success=False, error='Company not found', status_code=404)
            company = dict(row)
            
            # Get internships
            cur.execute('''
                SELECT id, title, location, status, is_remote, date_posted
                FROM internships 
                WHERE company_id = ?
                ORDER BY date_scraped DESC
            ''', (company_id,))
            internships = [dict(r) for r in cur.fetchall()]
            
            # Get contacts
            cur.execute('''
                SELECT id, name, email, phone, position, linkedin_url, notes, is_primary, last_contacted
                FROM contacts 
                WHERE company_id = ?
                ORDER BY is_primary DESC, created_at DESC
            ''', (company_id,))
            contacts = [dict(r) for r in cur.fetchall()]
        
        return ServiceResult(success=True, data={
            'company': company,
            'internships': internships,
            'contacts': contacts
        })
    
    def list_companies(
        self,
        search: str = None,
        industry: str = None,
        country: str = None,
        page: int = 1,
        per_page: int = 25
    ) -> ServiceResult:
        """List companies with filters and pagination."""
        offset = (page - 1) * per_page
        
        items = self.db.list_companies(
            search=search,
            industry=industry,
            country=country,
            limit=per_page,
            offset=offset
        )
        
        # Get total count
        total = self._get_total_count('companies')
        
        return ServiceResult(success=True, data={
            'items': items,
            'page': page,
            'per_page': per_page,
            'total': total
        })
    
    def enrich_company(self, company_id: int, website_url: str = None) -> ServiceResult:
        """
        Enrich company data to fill: Description, Contacts, LinkedIn, Website.
        
        Uses lazy evaluation - stops as soon as all target fields are filled.
        Tries sources in order: existing website → resolve website → LinkedIn → Wikipedia → Google
        
        Args:
            company_id: Company ID
            website_url: Optional override for website URL (will update DB first)
            
        Returns:
            ServiceResult with enriched data
        """
        enricher = CompanyEnricher(db_client=self.db)
        
        try:
            # If website URL provided, update the company first
            if website_url:
                with self.db.get_connection() as conn:
                    cur = conn.cursor()
                    cur.execute(
                        'UPDATE companies SET website = ?, updated_at = ? WHERE id = ?',
                        (website_url, datetime.utcnow().isoformat(), company_id)
                    )
                    conn.commit()
            
            # Use the simplified enrich method (takes only company_id)
            enriched_data = enricher.enrich(company_id)
            
            return ServiceResult(success=True, data={
                'company_id': company_id,
                'enriched_data': enriched_data,
                'target_complete': enriched_data.get('target_complete', False),
                'sources': enriched_data.get('sources', []),
                'fields_updated': enriched_data.get('fields_updated', [])
            })
        except ValueError as e:
            return ServiceResult(success=False, error=str(e), status_code=404)
        except Exception as e:
            logger.error(f"Enrichment failed for company {company_id}: {e}")
            return ServiceResult(success=False, error=str(e), status_code=500)
    
    def _get_total_count(self, table: str) -> Optional[int]:
        """Get total count for a table."""
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(f'SELECT COUNT(*) as c FROM {table}')
                return cur.fetchone()['c']
        except Exception:
            return None
