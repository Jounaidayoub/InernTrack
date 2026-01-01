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
    
    def get_unenriched_companies(self) -> ServiceResult:
        """
        Get companies that haven't been enriched yet.
        
        Uses the is_enriched column to determine enrichment status.
        Companies with is_enriched = FALSE or NULL are returned.
        
        Returns:
            ServiceResult with list of unenriched company IDs and names
        """
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                
                # Get companies where is_enriched is FALSE or NULL
                cur.execute('''
                    SELECT c.id, c.name, c.website, c.linkedin_url,
                           CASE WHEN c.description IS NULL OR c.description = '' THEN 0 ELSE 1 END as has_description,
                           (SELECT COUNT(*) FROM contacts WHERE company_id = c.id) as contact_count,
                           c.is_enriched
                    FROM companies c
                    WHERE c.is_enriched IS NULL OR c.is_enriched = 0
                    ORDER BY c.name
                ''')
                
                companies = []
                for row in cur.fetchall():
                    companies.append({
                        'id': row['id'],
                        'name': row['name'],
                        'has_website': bool(row['website']),
                        'has_linkedin': bool(row['linkedin_url']),
                        'has_description': bool(row['has_description']),
                        'contact_count': row['contact_count'],
                        'is_enriched': bool(row['is_enriched']) if row['is_enriched'] is not None else False
                    })
                
                return ServiceResult(success=True, data={
                    'companies': companies,
                    'total': len(companies)
                })
        except Exception as e:
            logger.error(f"Failed to get unenriched companies: {e}")
            return ServiceResult(success=False, error=str(e), status_code=500)
    
    def batch_enrich_companies(self, company_ids: list = None, limit: int = 10) -> ServiceResult:
        """
        Batch enrich multiple companies.
        
        If no company_ids provided, enriches unenriched companies up to limit.
        
        Args:
            company_ids: Optional list of specific company IDs to enrich
            limit: Max number of companies to enrich (default 10)
            
        Returns:
            ServiceResult with enrichment results for each company
        """
        results = []
        errors = []
        
        # Get companies to enrich
        if company_ids:
            ids_to_enrich = company_ids[:limit]
        else:
            unenriched = self.get_unenriched_companies()
            if not unenriched.success:
                return unenriched
            ids_to_enrich = [c['id'] for c in unenriched.data['companies'][:limit]]
        
        if not ids_to_enrich:
            return ServiceResult(success=True, data={
                'message': 'No companies need enrichment',
                'enriched': 0,
                'results': []
            })
        
        # Enrich each company
        for company_id in ids_to_enrich:
            try:
                result = self.enrich_company(company_id)
                if result.success:
                    results.append({
                        'company_id': company_id,
                        'success': True,
                        'target_complete': result.data.get('target_complete', False),
                        'fields_updated': result.data.get('fields_updated', [])
                    })
                else:
                    errors.append({
                        'company_id': company_id,
                        'success': False,
                        'error': result.error
                    })
            except Exception as e:
                errors.append({
                    'company_id': company_id,
                    'success': False,
                    'error': str(e)
                })
        
        return ServiceResult(success=True, data={
            'enriched': len(results),
            'failed': len(errors),
            'total_attempted': len(ids_to_enrich),
            'results': results,
            'errors': errors
        })
    
    def reset_enrichment_status(self, company_id: int) -> ServiceResult:
        """
        Reset the enrichment status of a company to allow re-enrichment.
        
        Args:
            company_id: Company ID to reset
            
        Returns:
            ServiceResult indicating success or failure
        """
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute('''
                    UPDATE companies 
                    SET is_enriched = 0, enriched_at = NULL, updated_at = ?
                    WHERE id = ?
                ''', (datetime.utcnow().isoformat(), company_id))
                conn.commit()
                
                if cur.rowcount == 0:
                    return ServiceResult(success=False, error='Company not found', status_code=404)
                
                return ServiceResult(success=True, data={'company_id': company_id, 'is_enriched': False})
        except Exception as e:
            logger.error(f"Failed to reset enrichment status for company {company_id}: {e}")
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
