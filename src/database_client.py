#!/usr/bin/env python3
"""
SQLite Database Client (v2.0)

Improved database module for the internship tracking pipeline.
Features:
- All JobSpy fields captured
- Salary decomposition (min, max, currency, interval)
- Scrape run auditing
- Proper foreign keys with CASCADE
- CHECK constraints for data validation
- Optimized indexes

Tables:
- scrape_runs: Audit log of scraping operations
- companies: Company information with JobSpy metadata
- internships: Job postings with full JobSpy fields
- job_tags: Tagging system
- internship_tags: Junction table for tags
- contacts: Contact management
- applications: Application tracking
- documents: Document storage
- offers_received: Offer tracking
- saved_searches: Reusable search queries

Author: El Moujahid Marouane
Version: 2.0
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import Optional, Dict, Any, List

try:
    from .config import settings
    from .logger_setup import get_logger
except ImportError:
    from config import settings
    from logger_setup import get_logger
import json

logger = get_logger("sqlite_client", settings.LOG_LEVEL)

class DatabaseClient:
    """
    SQLite database client for internship tracking.
    
    Provides CRUD operations for all entities with full
    JobSpy field support and scrape run auditing.
    """
    
    def __init__(self, db_path: str = None):
        """Initialize database connection and create schema."""
        self.db_path = db_path or getattr(settings, 'DATABASE_PATH', 'data/internship_sync_new.db')
        self._ensure_database_exists()
        self._create_tables()
        self._run_migrations()
        
    def _ensure_database_exists(self):
        """Create database directory and verify connection."""
        try:
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir)
                
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('PRAGMA foreign_keys = ON')
                conn.execute('SELECT 1')
                
            logger.info(f"Database initialized: {self.db_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _run_migrations(self):
        """Run database migrations for schema updates."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if user_status column exists in internships
            cursor.execute("PRAGMA table_info(internships)")
            internship_columns = [col[1] for col in cursor.fetchall()]
            
            if 'user_status' not in internship_columns:
                logger.info("Running migration: Adding user_status columns to internships")
                cursor.execute("""
                    ALTER TABLE internships ADD COLUMN user_status TEXT DEFAULT 'new'
                """)
                cursor.execute("""
                    ALTER TABLE internships ADD COLUMN user_notes TEXT
                """)
                cursor.execute("""
                    ALTER TABLE internships ADD COLUMN user_rating INTEGER
                """)
                conn.commit()
                logger.info("Migration completed: user_status columns added")
            
            # Check if is_enriched column exists in companies
            cursor.execute("PRAGMA table_info(companies)")
            company_columns = [col[1] for col in cursor.fetchall()]
            
            if 'is_enriched' not in company_columns:
                logger.info("Running migration: Adding is_enriched column to companies")
                cursor.execute("""
                    ALTER TABLE companies ADD COLUMN is_enriched BOOLEAN DEFAULT FALSE
                """)
                cursor.execute("""
                    ALTER TABLE companies ADD COLUMN enriched_at TIMESTAMP
                """)
                conn.commit()
                logger.info("Migration completed: is_enriched column added")
            
    def _create_tables(self):
        """Create all tables with improved schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Companies table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scrape_runs (
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
                CREATE TABLE IF NOT EXISTS companies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    name_normalized TEXT,
                    website TEXT,
                    company_url TEXT,
                    company_url_direct TEXT,
                    logo_url TEXT,
                    industry TEXT,
                    country TEXT,
                    city TEXT,
                    addresses TEXT,
                    num_employees TEXT,
                    revenue TEXT,
                    description TEXT,
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
                    company_id INTEGER,
                    
                    status TEXT DEFAULT 'draft'
                        CHECK (status IN ('draft', 'applied', 'viewed', 'screening', 
                               'interview_scheduled', 'interviewed', 'offer_received',
                               'offer_accepted', 'offer_declined', 'rejected', 'withdrawn')),
                    application_method TEXT
                        CHECK (application_method IS NULL OR application_method IN 
                               ('company_portal', 'linkedin', 'email', 'referral', 'career_fair', 'other')),
                    
                    applied_date DATE,
                    response_date DATE,
                    interview_date TIMESTAMP,
                    follow_up_date DATE,
                    next_action_date DATE,
                    
                    cover_letter_path TEXT,
                    resume_path TEXT,
                    portfolio_url TEXT,
                    
                    salary_expectation_min REAL,
                    salary_expectation_max REAL,
                    salary_currency TEXT DEFAULT 'USD',
                    
                    rejection_reason TEXT,
                    interview_notes TEXT,
                    notes TEXT,
                    rating INTEGER CHECK (rating IS NULL OR (rating >= 1 AND rating <= 5)),
                    
                    is_favorite BOOLEAN DEFAULT FALSE,
                    requires_follow_up BOOLEAN DEFAULT FALSE,
                    
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (internship_id) REFERENCES internships (id) ON DELETE SET NULL,
                    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE SET NULL
                )
            """)
            
            # ================================================================
            # DOCUMENTS
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    application_id INTEGER,
                    document_type TEXT NOT NULL DEFAULT 'other'
                        CHECK (document_type IN ('resume', 'cover_letter', 'portfolio', 
                               'transcript', 'certificate', 'other')),
                    file_path TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_size INTEGER,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT,
                    FOREIGN KEY (application_id) REFERENCES applications (id)
                )
            """)
            
            # ================================================================
            # OFFERS_RECEIVED
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS offers_received (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    application_id INTEGER,
                    company_id INTEGER,
                    position_title TEXT NOT NULL,
                    
                    salary_offered REAL,
                    salary_currency TEXT DEFAULT 'USD',
                    salary_interval TEXT DEFAULT 'yearly',
                    signing_bonus REAL,
                    relocation_bonus REAL,
                    
                    benefits TEXT,
                    stock_options TEXT,
                    vacation_days INTEGER,
                    
                    contract_type TEXT DEFAULT 'internship'
                        CHECK (contract_type IN ('internship', 'fulltime', 'parttime', 'contract')),
                    duration TEXT,
                    location TEXT,
                    is_remote BOOLEAN DEFAULT FALSE,
                    
                    start_date DATE,
                    response_deadline DATE,
                    
                    status TEXT DEFAULT 'pending'
                        CHECK (status IN ('pending', 'accepted', 'declined', 'negotiating', 'expired')),
                    decision_reason TEXT,
                    
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
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    def find_company_by_name(self, company_name):
        """Find company by name"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM companies WHERE name = ? COLLATE NOCASE", (company_name,))
            result = cursor.fetchone()
            return dict(result) if result else None
    
    def create_company(self, data: Dict[str, Any]) -> Optional[int]:
        """Create company from JobSpy data."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                name = data.get('company') or data.get('name', 'Unknown')
                
                cursor.execute("""
                    INSERT INTO companies (name, website, industry, country, description)
                    VALUES (?, ?, ?, ?, ?)
                """, (company_name, website, industry, country, description))
                
                company_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"Created company: {company_name} (ID: {company_id})")
                return company_id
                
        except sqlite3.IntegrityError:
            existing = self.find_company_by_name(
                data.get('company') or data.get('name', 'Unknown')
            )
            return existing['id'] if existing else None
        except Exception as e:
            logger.error(f"Failed to create company: {e}")
            return None
    
    def list_companies(self, search: str = None, industry: str = None,
                      country: str = None, limit: int = 50, offset: int = 0) -> List[Dict]:
        """List companies with optional filters."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM companies"
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
                query += " WHERE " + " AND ".join(clauses)
            
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            return [dict(r) for r in cursor.fetchall()]
    
    # ========================================================================
    # INTERNSHIP METHODS
    # ========================================================================
    
    def find_internship_by_url(self, url: str) -> Optional[Dict]:
        """Find internship by job URL."""
        if not url:
            return None
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM internships WHERE job_url = ?", (url,))
            result = cursor.fetchone()
            return dict(result) if result else None
    
    def create_internship(self, data: Dict[str, Any], company_id: int = None,
                         scrape_run_id: int = None) -> Optional[int]:
        """Create internship from normalized JobSpy data."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Determine site value - validate against CHECK constraint
                site = (data.get('site') or 'other').lower()
                valid_sites = ['linkedin', 'indeed', 'glassdoor', 'zip_recruiter', 'google', 'other']
                if site not in valid_sites:
                    site = 'other'
                
                # Determine job_type - validate against CHECK constraint
                job_type = (data.get('job_type') or 'internship').lower()
                valid_types = ['fulltime', 'parttime', 'contract', 'internship', 'temporary', 'other']
                if job_type not in valid_types:
                    job_type = 'internship'
                
                # Salary interval validation
                interval = (data.get('interval') or 'unknown').lower()
                valid_intervals = ['yearly', 'monthly', 'weekly', 'daily', 'hourly', 'unknown']
                if interval not in valid_intervals:
                    interval = 'unknown'
                
                cursor.execute("""
                    INSERT INTO internships (
                        company_id, scrape_run_id, title, description, location,
                        city, state, country, job_url, job_url_direct,
                        site, job_type, job_level, job_function,
                        salary_min, salary_max, salary_currency, salary_interval, salary_source,
                        is_remote, date_posted, application_deadline,
                        duration, benefits, requirements, skills, experience_level,
                        emails, status, raw_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            logger.warning(f"Internship already exists: {data.get('job_url')}")
            existing = self.find_internship_by_url(data.get('job_url'))
            return existing['id'] if existing else None
        except Exception as e:
            logger.error(f"Failed to create internship: {e}")
            return None
    
    def ensure_company_and_internship(self, job_data: Dict[str, Any], 
                                      scrape_run_id: int = None) -> Optional[int]:
        """Process job: ensure company exists and create internship."""
        try:
            company_name = job_data.get('company', 'Unknown')
            
            # Find or create company
            company = self.find_company_by_name(company_name)
            if company:
                company_id = company['id']
            else:
                company_id = self.create_company(job_data)
                if not company_id:
                    logger.error(f"Failed to create company: {company_name}")
                    return None
            
            # Check for duplicate
            job_url = job_data.get('job_url') or job_data.get('url')
            if job_url:
                existing = self.find_internship_by_url(job_url)
                if existing:
                    logger.debug(f"Internship exists: {job_url}")
                    return existing['id']
            
            # Create internship
            return self.create_internship(job_data, company_id, scrape_run_id)
            
        except Exception as e:
            logger.exception(f"Failed to process job: {e}")
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
        """Cleanup (connections auto-close with context managers)."""
        pass
