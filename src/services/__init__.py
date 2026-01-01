"""
Service Layer Package

Contains business logic for internship tracking operations.
Separates database operations and scraping logic from HTTP handling.

Services:
- InternshipService: CRUD operations for internships
- CompanyService: CRUD operations for companies + enrichment
- ContactService: Contact management
- DatabaseService: Database status and statistics
- ExportService: Data export operations

Author: El Moujahid Marouane
Version: 2.0
"""

from .base import ServiceResult
from .internship_service import InternshipService
from .company_service import CompanyService
from .contact_service import ContactService
from .database_service import DatabaseService
from .export_service import ExportService

__all__ = [
    'ServiceResult',
    'InternshipService',
    'CompanyService',
    'ContactService',
    'DatabaseService',
    'ExportService',
]
