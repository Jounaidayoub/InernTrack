#!/usr/bin/env python3
"""
SQLite Database Integration Module

This module provides database operations for the internship sync pipeline.
It replaces the Notion integration with a local SQLite database for:

- Company management
- Contact tracking
- Internship opportunities
- Application tracking
- Document management
- Received offers

The module implements proper database schema, relationships, and CRUD operations
with transaction support and error handling.

Key Features:
- Automatic database and table creation
- Duplicate detection and prevention
- Comprehensive error logging
- Transaction support for data integrity
- Relationship management between tables

Author: El Moujahid Marouane
Version: 1.0
"""

# TODO: immigrate to pg server 
import sqlite3
import os
from datetime import datetime
try:
    from .config import settings
    from .logger_setup import get_logger
except ImportError:
    # Handle case when run directly (not as package)
    from config import settings
    from logger_setup import get_logger
import json

logger = get_logger("sqlite_client", settings.LOG_LEVEL)

class DatabaseClient:
    def __init__(self, db_path=None):
        """Initialize SQLite database connection"""
        self.db_path = db_path or getattr(settings, 'DATABASE_PATH', 'data/internship_sync.db')
        self._ensure_database_exists()
        self._create_tables()
        
    def _ensure_database_exists(self):
        """Ensure database file exists and is accessible"""
        try:
            # Create directory if it doesn't exist
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir)
                
            # Test connection
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('SELECT 1')
                
            logger.info(f"Database initialized: {self.db_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
            logger.error(f"Failed to initialize database: {e}")
            raise
            
    def _create_tables(self):
        """Create all required tables with proper schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Companies table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS companies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    website TEXT,
                    industry TEXT,
                    country TEXT,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Contacts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id INTEGER,
                    name TEXT NOT NULL,
                    email TEXT,
                    phone TEXT,
                    position TEXT,
                    linkedin_url TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies (id)
                )
            """)
            
            # Internships table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS internships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id INTEGER,
                    title TEXT NOT NULL,
                    description TEXT,
                    location TEXT,
                    url TEXT UNIQUE,
                    status TEXT DEFAULT 'Open',
                    requirements TEXT,
                    salary_range TEXT,
                    duration TEXT,
                    start_date TEXT,
                    application_deadline TEXT,
                    is_remote BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies (id)
                )
            """)
            
            # Applications table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    internship_id INTEGER,
                    status TEXT DEFAULT 'Applied',
                    applied_date DATE,
                    response_date DATE,
                    interview_date TIMESTAMP,
                    notes TEXT,
                    cover_letter_path TEXT,
                    resume_path TEXT,
                    follow_up_date DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (internship_id) REFERENCES internships (id)
                )
            """)
            
            # Documents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    application_id INTEGER,
                    document_type TEXT,
                    file_path TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_size INTEGER,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT,
                    FOREIGN KEY (application_id) REFERENCES applications (id)
                )
            """)
            
            # Offers received table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS offers_received (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    application_id INTEGER,
                    company_id INTEGER,
                    position_title TEXT NOT NULL,
                    salary_offered TEXT,
                    benefits TEXT,
                    start_date DATE,
                    response_deadline DATE,
                    status TEXT DEFAULT 'Pending',
                    contract_type TEXT,
                    location TEXT,
                    notes TEXT,
                    received_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    responded_date TIMESTAMP,
                    FOREIGN KEY (application_id) REFERENCES applications (id),
                    FOREIGN KEY (company_id) REFERENCES companies (id)
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_companies_name ON companies (name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_internships_company ON internships (company_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_internships_url ON internships (url)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_applications_internship ON applications (internship_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_contacts_company ON contacts (company_id)")
            
            conn.commit()
            logger.info("Database tables created successfully")
    
    def get_connection(self):
        """Get database connection with row factory for dict-like access"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def find_company_by_name(self, company_name):
        """Find company by name"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM companies WHERE name = ? COLLATE NOCASE", (company_name,))
            result = cursor.fetchone()
            return dict(result) if result else None
    
    def create_company(self, company_name, website=None, industry=None, country=None, description=None):
        """Create a new company record"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO companies (name, website, industry, country, description)
                    VALUES (?, ?, ?, ?, ?)
                """, (company_name, website, industry, country, description))
                
                company_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"Created company: {company_name} (ID: {company_id})")
                return company_id
                
        except sqlite3.IntegrityError as e:
            logger.warning(f"Company {company_name} already exists: {e}")
            # Return existing company
            existing = self.find_company_by_name(company_name)
            return existing['id'] if existing else None
        except Exception as e:
            logger.error(f"Failed to create company {company_name}: {e}")
            return None
    
    def find_internship_by_url(self, url):
        """Find internship by URL"""
        if not url:
            return None
            
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM internships WHERE url = ?", (url,))
            result = cursor.fetchone()
            return dict(result) if result else None
    
    def create_internship(self, job_data, company_id):
        """Create a new internship record"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO internships 
                    (company_id, title, description, location, url, status, is_remote)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    company_id,
                    job_data.get('title', 'Unknown Position'),
                    job_data.get('description', ''),
                    job_data.get('location', ''),
                    job_data.get('url'),
                    'Open',
                    'remote' in job_data.get('location', '').lower()
                ))
                
                internship_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"Created internship: {job_data.get('title')} (ID: {internship_id})")
                return internship_id
                
        except sqlite3.IntegrityError as e:
            logger.warning(f"Internship with URL {job_data.get('url')} already exists: {e}")
            existing = self.find_internship_by_url(job_data.get('url'))
            return existing['id'] if existing else None
        except Exception as e:
            logger.error(f"Failed to create internship {job_data.get('title')}: {e}")
            return None
    
    def ensure_company_and_internship(self, job_data):
        """Ensure company exists and create internship"""
        try:
            # Check if company exists
            company = self.find_company_by_name(job_data['company'])
            
            if company:
                company_id = company['id']
                logger.info(f"Company exists: {job_data['company']} (ID: {company_id})")
            else:
                # Create company
                company_id = self.create_company(job_data['company'])
                if not company_id:
                    logger.error("Failed to create company, skipping internship creation")
                    return None
            
            # Check if internship already exists
            if job_data.get('url'):
                existing_internship = self.find_internship_by_url(job_data['url'])
                if existing_internship:
                    logger.info(f"Internship already exists: {job_data['url']}")
                    return existing_internship['id']
            
            # Create internship
            internship_id = self.create_internship(job_data, company_id)
            return internship_id
            
        except Exception as e:
            logger.exception(f"Failed to process job {job_data.get('title', 'Unknown')}: {e}")
            return None
    
    def get_stats(self):
        """Get database statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            tables = ['companies', 'contacts', 'internships', 'applications', 'documents', 'offers_received']
            
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                stats[table] = cursor.fetchone()['count']
            
            return stats

    def list_internships(self, search: str | None = None, limit: int = 25, offset: int = 0):
        """Return a list of internships joined with company name.
        Parameters:
        - search: optional text to search in title, company or location
        - limit, offset: pagination

        Returns: list of dict rows
        """
    
        with self.get_connection() as conn:
            cursor = conn.cursor()
            base = (
                "SELECT internships.id, internships.title, internships.description, "
                "internships.location, internships.url, internships.status, internships.created_at, companies.name as company "
                "FROM internships LEFT JOIN companies ON internships.company_id = companies.id"
            )
            params = []
            if search:
                base += " WHERE (internships.title LIKE ? OR companies.name LIKE ? OR internships.location LIKE ?)"
                q = f"%{search}%"
                params.extend([q, q, q])

            # base += " ORDER BY internships.created_at DESC LIMIT ? OFFSET ?"
            # params.extend([limit, offset])

            cursor.execute(base, params)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def list_companies(self, search: str | None = None, industry: str | None = None,
                       country: str | None = None, limit: int = 50, offset: int = 0):
        """Return a paginated list of companies with optional filters."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            base = ("SELECT id, name, website, industry, country, description, created_at "
                    "FROM companies")
            params = []
            clauses = []
            if search:
                clauses.append("(name LIKE ? OR description LIKE ?)")
                q = f"%{search}%"
                params.extend([q, q])
            if industry:
                clauses.append("industry = ?")
                params.append(industry)
            if country:
                clauses.append("country = ?")
                params.append(country)

            if clauses:
                base += " WHERE " + " AND ".join(clauses)

            base += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(base, params)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
    
    def close(self):
        """Close database connection (for cleanup)"""
        # SQLite connections are closed automatically with context managers
        pass