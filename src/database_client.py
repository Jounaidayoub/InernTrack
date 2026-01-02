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

logger = get_logger("database_client", settings.LOG_LEVEL)


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
            cursor.execute("PRAGMA foreign_keys = ON")
            
            # ================================================================
            # SCRAPE_RUNS - Audit log for scraping operations
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scrape_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    status TEXT NOT NULL DEFAULT 'running' 
                        CHECK (status IN ('running', 'completed', 'failed', 'cancelled')),
                    search_terms TEXT,
                    locations TEXT,
                    sites TEXT,
                    total_found INTEGER DEFAULT 0,
                    new_jobs INTEGER DEFAULT 0,
                    duplicates INTEGER DEFAULT 0,
                    errors INTEGER DEFAULT 0,
                    error_message TEXT,
                    config_snapshot TEXT
                )
            """)
            
            # ================================================================
            # COMPANIES - Enhanced with JobSpy fields
            # ================================================================
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
                    glassdoor_url TEXT,
                    is_verified BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(name, country)
                )
            """)
            
            # ================================================================
            # INTERNSHIPS - Completely redesigned with all JobSpy fields
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS internships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id INTEGER,
                    scrape_run_id INTEGER,
                    
                    -- Core fields
                    title TEXT NOT NULL,
                    description TEXT,
                    
                    -- Location
                    location TEXT,
                    city TEXT,
                    state TEXT,
                    country TEXT,
                    
                    -- URLs
                    job_url TEXT UNIQUE,
                    job_url_direct TEXT,
                    
                    -- Source & Type
                    site TEXT DEFAULT 'other' 
                        CHECK (site IN ('linkedin', 'indeed', 'glassdoor', 'zip_recruiter', 'google', 'other')),
                    job_type TEXT DEFAULT 'internship'
                        CHECK (job_type IN ('fulltime', 'parttime', 'contract', 'internship', 'temporary', 'other')),
                    job_level TEXT,
                    job_function TEXT,
                    
                    -- Salary (decomposed)
                    salary_min REAL,
                    salary_max REAL,
                    salary_currency TEXT DEFAULT 'USD',
                    salary_interval TEXT DEFAULT 'yearly'
                        CHECK (salary_interval IN ('yearly', 'monthly', 'weekly', 'daily', 'hourly', 'unknown')),
                    salary_source TEXT,
                    
                    -- Remote work
                    is_remote BOOLEAN DEFAULT FALSE,
                    
                    -- Dates
                    date_posted DATE,
                    date_scraped TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    application_deadline DATE,
                    start_date DATE,
                    
                    -- Additional info
                    duration TEXT,
                    benefits TEXT,
                    requirements TEXT,
                    skills TEXT,
                    experience_level TEXT,
                    education_level TEXT,
                    
                    -- Contact
                    emails TEXT,
                    apply_instructions TEXT,
                    
                    -- Job Status (from source)
                    status TEXT DEFAULT 'open'
                        CHECK (status IN ('open', 'closed', 'filled', 'expired', 'unknown')),
                    is_active BOOLEAN DEFAULT TRUE,
                    
                    -- User Status (user's tracking status)
                    user_status TEXT DEFAULT 'new'
                        CHECK (user_status IN ('new', 'interesting', 'applied', 'waiting', 'interviewing', 'rejected', 'offer', 'ignored')),
                    user_notes TEXT,
                    user_rating INTEGER CHECK (user_rating IS NULL OR (user_rating >= 1 AND user_rating <= 5)),
                    
                    -- Debug
                    raw_data TEXT,
                    
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE SET NULL,
                    FOREIGN KEY (scrape_run_id) REFERENCES scrape_runs (id) ON DELETE SET NULL
                )
            """)
            
            # ================================================================
            # JOB_TAGS - Tagging system
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS job_tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    color TEXT DEFAULT '#9CAF88',
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS internship_tags (
                    internship_id INTEGER NOT NULL,
                    tag_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (internship_id, tag_id),
                    FOREIGN KEY (internship_id) REFERENCES internships (id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES job_tags (id) ON DELETE CASCADE
                )
            """)
            
            # ================================================================
            # CONTACTS
            # ================================================================
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
                    is_primary BOOLEAN DEFAULT FALSE,
                    last_contacted DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
                )
            """)
            
            # ================================================================
            # APPLICATIONS - Enhanced with tracking
            # ================================================================
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
                    mime_type TEXT,
                    version INTEGER DEFAULT 1,
                    is_default BOOLEAN DEFAULT FALSE,
                    notes TEXT,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (application_id) REFERENCES applications (id) ON DELETE CASCADE
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
                    notes TEXT,
                    
                    FOREIGN KEY (application_id) REFERENCES applications (id) ON DELETE SET NULL,
                    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE SET NULL
                )
            """)
            
            # ================================================================
            # SAVED_SEARCHES
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS saved_searches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    search_terms TEXT,
                    locations TEXT,
                    sites TEXT,
                    job_types TEXT,
                    is_remote BOOLEAN,
                    salary_min REAL,
                    salary_max REAL,
                    experience_levels TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    last_run TIMESTAMP,
                    run_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            self._create_indexes(cursor)
            
            conn.commit()
            logger.info("Database tables created successfully")
    
    def _create_indexes(self, cursor):
        """Create indexes for query optimization."""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_companies_name ON companies (name)",
            "CREATE INDEX IF NOT EXISTS idx_companies_normalized ON companies (name_normalized)",
            "CREATE INDEX IF NOT EXISTS idx_companies_country ON companies (country)",
            "CREATE INDEX IF NOT EXISTS idx_internships_company ON internships (company_id)",
            "CREATE INDEX IF NOT EXISTS idx_internships_job_url ON internships (job_url)",
            "CREATE INDEX IF NOT EXISTS idx_internships_site ON internships (site)",
            "CREATE INDEX IF NOT EXISTS idx_internships_status ON internships (status)",
            "CREATE INDEX IF NOT EXISTS idx_internships_remote ON internships (is_remote)",
            "CREATE INDEX IF NOT EXISTS idx_internships_date_posted ON internships (date_posted)",
            "CREATE INDEX IF NOT EXISTS idx_internships_date_scraped ON internships (date_scraped)",
            "CREATE INDEX IF NOT EXISTS idx_applications_status ON applications (status)",
            "CREATE INDEX IF NOT EXISTS idx_applications_internship ON applications (internship_id)",
            "CREATE INDEX IF NOT EXISTS idx_scrape_runs_status ON scrape_runs (status)",
            "CREATE INDEX IF NOT EXISTS idx_contacts_company ON contacts (company_id)",
        ]
        for idx in indexes:
            try:
                cursor.execute(idx)
            except sqlite3.OperationalError:
                pass
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    # ========================================================================
    # SCRAPE RUN METHODS
    # ========================================================================
    
    def start_scrape_run(self, search_terms: List[str] = None, 
                        locations: List[str] = None, 
                        sites: List[str] = None) -> int:
        """Start a new scrape run and return its ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO scrape_runs (search_terms, locations, sites, status)
                VALUES (?, ?, ?, 'running')
            """, (
                json.dumps(search_terms or []),
                json.dumps(locations or []),
                json.dumps(sites or [])
            ))
            conn.commit()
            run_id = cursor.lastrowid
            logger.info(f"Started scrape run {run_id}")
            return run_id
    
    def complete_scrape_run(self, run_id: int, total_found: int = 0, 
                           new_jobs: int = 0, duplicates: int = 0, 
                           errors: int = 0, error_message: str = None):
        """Mark scrape run as completed with statistics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            status = 'failed' if error_message else 'completed'
            cursor.execute("""
                UPDATE scrape_runs SET
                    completed_at = CURRENT_TIMESTAMP,
                    status = ?,
                    total_found = ?,
                    new_jobs = ?,
                    duplicates = ?,
                    errors = ?,
                    error_message = ?
                WHERE id = ?
            """, (status, total_found, new_jobs, duplicates, errors, error_message, run_id))
            conn.commit()
            logger.info(f"Completed scrape run {run_id}: {new_jobs} new, {duplicates} dupes")
    
    def list_scrape_runs(self, limit: int = 20) -> List[Dict]:
        """List recent scrape runs."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM scrape_runs ORDER BY started_at DESC LIMIT ?
            """, (limit,))
            return [dict(r) for r in cursor.fetchall()]
    
    def get_quick_stats(self) -> Dict[str, Any]:
        """Get quick stats: last run state, total scrapes today, success rate today, total jobs."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get last run info
            cursor.execute("""
                SELECT id, status, started_at, completed_at, new_jobs, total_found
                FROM scrape_runs 
                ORDER BY started_at DESC 
                LIMIT 1
            """)
            last_run_row = cursor.fetchone()
            last_run = dict(last_run_row) if last_run_row else None
            
            # Get total scrapes today
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM scrape_runs 
                WHERE date(started_at) = date('now')
            """)
            total_scrapes_today = cursor.fetchone()['count']
            
            # Get success rate today (completed vs total)
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed
                FROM scrape_runs 
                WHERE date(started_at) = date('now')
            """)
            rate_row = cursor.fetchone()
            total_today = rate_row['total'] or 0
            completed_today = rate_row['completed'] or 0
            success_rate = round((completed_today / total_today) * 100, 1) if total_today > 0 else 0.0
            
            # Get total jobs in database
            cursor.execute("SELECT COUNT(*) as count FROM internships")
            total_jobs = cursor.fetchone()['count']
            
            # Get jobs added today
            cursor.execute("""
                SELECT count(*) as count 
                FROM internships
                WHERE date(created_at) = date('now')
            """)
            jobs_today = cursor.fetchone()['count']
            
            return {
                'last_run': last_run,
                'total_scrapes_today': total_scrapes_today,
                'success_rate_today': success_rate,
                'total_jobs': total_jobs,
                'jobs_today': jobs_today
            }
    


    # ========================================================================
    # COMPANY METHODS
    # ========================================================================
    
    def find_company_by_name(self, name: str, country: str = None) -> Optional[Dict]:
        """Find company by name (case-insensitive)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            normalized = name.lower().strip()
            
            if country:
                cursor.execute("""
                    SELECT * FROM companies 
                    WHERE name_normalized = ? AND country = ?
                """, (normalized, country))
            else:
                cursor.execute("""
                    SELECT * FROM companies WHERE name_normalized = ?
                """, (normalized,))
            
            result = cursor.fetchone()
            return dict(result) if result else None
    
    def create_company(self, data: Dict[str, Any]) -> Optional[int]:
        """Create company from JobSpy data."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                name = data.get('company') or data.get('name', 'Unknown')
                
                cursor.execute("""
                    INSERT INTO companies (
                        name, name_normalized, website, company_url, company_url_direct,
                        logo_url, industry, country, city, addresses, num_employees,
                        revenue, description
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    name,
                    name.lower().strip(),
                    data.get('company_url'),
                    data.get('company_url'),
                    data.get('company_url_direct'),
                    data.get('logo_photo_url'),
                    data.get('company_industry'),
                    data.get('country'),
                    data.get('city'),
                    json.dumps(data.get('company_addresses')) if data.get('company_addresses') else None,
                    data.get('company_num_employees'),
                    data.get('company_revenue'),
                    data.get('company_description')
                ))
                
                conn.commit()
                company_id = cursor.lastrowid
                logger.info(f"Created company: {name} (ID: {company_id})")
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
                    scrape_run_id,
                    data.get('title', 'Unknown Position'),
                    data.get('description', ''),
                    data.get('location', ''),
                    data.get('city'),
                    data.get('state'),
                    data.get('country'),
                    data.get('job_url'),
                    data.get('job_url_direct'),
                    site,
                    job_type,
                    data.get('job_level'),
                    data.get('job_function'),
                    data.get('min_amount'),
                    data.get('max_amount'),
                    data.get('currency', 'USD'),
                    interval,
                    data.get('salary_source'),
                    data.get('is_remote', False),
                    data.get('date_posted'),
                    data.get('application_deadline'),
                    data.get('duration'),
                    data.get('benefits'),
                    data.get('requirements'),
                    json.dumps(data.get('skills')) if data.get('skills') else None,
                    data.get('experience_level'),
                    json.dumps(data.get('emails')) if data.get('emails') else None,
                    'open',
                    json.dumps(data.get('raw', data), default=str)
                ))
                
                conn.commit()
                internship_id = cursor.lastrowid
                logger.info(f"Created internship: {data.get('title')} (ID: {internship_id})")
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
    
    def list_internships(
        self, 
        search: str = None, 
        site: str = None,
        is_remote: bool = None, 
        status: str = None,
        user_status: str = None,
        user_statuses: List[str] = None,
        company_ids: List[int] = None,
        locations: List[str] = None,
        sort_by: str = 'date_scraped',
        sort_order: str = 'desc',
        limit: int = 50, 
        offset: int = 0
    ) -> List[Dict]:
        """
        List internships with advanced filters and sorting.
        
        Args:
            search: Search in title, company name, location
            site: Filter by job site source
            is_remote: Filter by remote status
            status: Filter by job status (open, closed, etc.)
            user_status: Filter by single user status
            user_statuses: Filter by multiple user statuses (OR)
            company_ids: Filter by multiple company IDs (OR)
            locations: Filter by multiple locations (OR, partial match)
            sort_by: Column to sort by (date_scraped, date_posted, title, company_name, user_status)
            sort_order: Sort order (asc, desc)
            limit: Max results
            offset: Pagination offset
            
        Returns:
            List of internship dictionaries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT i.*, c.name as company_name, c.logo_url as company_logo
                FROM internships i
                LEFT JOIN companies c ON i.company_id = c.id
            """
            params = []
            clauses = []
            
            # Text search
            if search:
                clauses.append("(i.title LIKE ? OR c.name LIKE ? OR i.location LIKE ?)")
                q = f"%{search}%"
                params.extend([q, q, q])
            
            # Site filter
            if site:
                clauses.append("i.site = ?")
                params.append(site)
            
            # Remote filter
            if is_remote is not None:
                clauses.append("i.is_remote = ?")
                params.append(is_remote)
            
            # Job status filter
            if status:
                clauses.append("i.status = ?")
                params.append(status)
            
            # User status filter (single)
            if user_status:
                clauses.append("i.user_status = ?")
                params.append(user_status)
            
            # User status filter (multiple - OR)
            if user_statuses and len(user_statuses) > 0:
                placeholders = ','.join(['?' for _ in user_statuses])
                clauses.append(f"i.user_status IN ({placeholders})")
                params.extend(user_statuses)
            
            # Company filter (multiple - OR)
            if company_ids and len(company_ids) > 0:
                placeholders = ','.join(['?' for _ in company_ids])
                clauses.append(f"i.company_id IN ({placeholders})")
                params.extend(company_ids)
            
            # Location filter (multiple - OR with LIKE)
            if locations and len(locations) > 0:
                location_clauses = []
                for loc in locations:
                    location_clauses.append("i.location LIKE ?")
                    params.append(f"%{loc}%")
                clauses.append(f"({' OR '.join(location_clauses)})")
            
            if clauses:
                query += " WHERE " + " AND ".join(clauses)
            
            # Sorting
            valid_sort_columns = {
                'date_scraped': 'i.date_scraped',
                'date_posted': 'i.date_posted',
                'title': 'i.title',
                'company_name': 'c.name',
                'user_status': 'i.user_status',
                'location': 'i.location',
                'status': 'i.status'
            }
            sort_col = valid_sort_columns.get(sort_by, 'i.date_scraped')
            sort_dir = 'ASC' if sort_order.lower() == 'asc' else 'DESC'
            
            query += f" ORDER BY {sort_col} {sort_dir} LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            return [dict(r) for r in cursor.fetchall()]
    
    def count_internships(
        self,
        search: str = None,
        site: str = None,
        is_remote: bool = None,
        status: str = None,
        user_status: str = None,
        user_statuses: List[str] = None,
        company_ids: List[int] = None,
        locations: List[str] = None
    ) -> int:
        """Count internships with same filters as list_internships."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT COUNT(*) as count
                FROM internships i
                LEFT JOIN companies c ON i.company_id = c.id
            """
            params = []
            clauses = []
            
            if search:
                clauses.append("(i.title LIKE ? OR c.name LIKE ? OR i.location LIKE ?)")
                q = f"%{search}%"
                params.extend([q, q, q])
            
            if site:
                clauses.append("i.site = ?")
                params.append(site)
            
            if is_remote is not None:
                clauses.append("i.is_remote = ?")
                params.append(is_remote)
            
            if status:
                clauses.append("i.status = ?")
                params.append(status)
            
            if user_status:
                clauses.append("i.user_status = ?")
                params.append(user_status)
            
            if user_statuses and len(user_statuses) > 0:
                placeholders = ','.join(['?' for _ in user_statuses])
                clauses.append(f"i.user_status IN ({placeholders})")
                params.extend(user_statuses)
            
            if company_ids and len(company_ids) > 0:
                placeholders = ','.join(['?' for _ in company_ids])
                clauses.append(f"i.company_id IN ({placeholders})")
                params.extend(company_ids)
            
            if locations and len(locations) > 0:
                location_clauses = []
                for loc in locations:
                    location_clauses.append("i.location LIKE ?")
                    params.append(f"%{loc}%")
                clauses.append(f"({' OR '.join(location_clauses)})")
            
            if clauses:
                query += " WHERE " + " AND ".join(clauses)
            
            cursor.execute(query, params)
            return cursor.fetchone()['count']
    
    def update_internship_user_status(
        self, 
        internship_id: int, 
        user_status: str, 
        user_notes: str = None,
        user_rating: int = None
    ) -> bool:
        """Update user status, notes, and rating for an internship."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            updates = ["user_status = ?", "updated_at = CURRENT_TIMESTAMP"]
            params = [user_status]
            
            if user_notes is not None:
                updates.append("user_notes = ?")
                params.append(user_notes)
            
            if user_rating is not None:
                updates.append("user_rating = ?")
                params.append(user_rating)
            
            params.append(internship_id)
            
            cursor.execute(f"""
                UPDATE internships SET {', '.join(updates)}
                WHERE id = ?
            """, params)
            conn.commit()
            return cursor.rowcount > 0
    
    def get_filter_options(self) -> Dict[str, List]:
        """Get distinct values for filter dropdowns."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get unique locations
            cursor.execute("""
                SELECT DISTINCT location FROM internships 
                WHERE location IS NOT NULL AND location != ''
                ORDER BY location
            """)
            locations = [r['location'] for r in cursor.fetchall()]
            
            # Get companies with internship count
            cursor.execute("""
                SELECT c.id, c.name, COUNT(i.id) as count
                FROM companies c
                INNER JOIN internships i ON i.company_id = c.id
                GROUP BY c.id, c.name
                ORDER BY count DESC, c.name
            """)
            companies = [{'id': r['id'], 'name': r['name'], 'count': r['count']} for r in cursor.fetchall()]
            
            # Get user status counts
            cursor.execute("""
                SELECT user_status, COUNT(*) as count
                FROM internships
                GROUP BY user_status
                ORDER BY count DESC
            """)
            user_statuses = [{'status': r['user_status'] or 'new', 'count': r['count']} for r in cursor.fetchall()]
            
            # Get site counts
            cursor.execute("""
                SELECT site, COUNT(*) as count
                FROM internships
                GROUP BY site
                ORDER BY count DESC
            """)
            sites = [{'site': r['site'], 'count': r['count']} for r in cursor.fetchall()]
            
            return {
                'locations': locations,
                'companies': companies,
                'user_statuses': user_statuses,
                'sites': sites
            }
    
    def get_internship(self, internship_id: int) -> Optional[Dict]:
        """Get internship by ID with company info."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT i.*, c.name as company_name, c.logo_url as company_logo,
                       c.website as company_website
                FROM internships i
                LEFT JOIN companies c ON i.company_id = c.id
                WHERE i.id = ?
            """, (internship_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # ========================================================================
    # APPLICATION METHODS
    # ========================================================================
    
    def create_application(self, internship_id: int, data: Dict[str, Any] = None) -> Optional[int]:
        """Create a new application."""
        data = data or {}
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get company_id from internship
            cursor.execute("SELECT company_id FROM internships WHERE id = ?", (internship_id,))
            row = cursor.fetchone()
            company_id = row['company_id'] if row else None
            
            cursor.execute("""
                INSERT INTO applications (
                    internship_id, company_id, status, application_method,
                    applied_date, notes
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                internship_id,
                company_id,
                data.get('status', 'draft'),
                data.get('application_method'),
                data.get('applied_date'),
                data.get('notes')
            ))
            
            conn.commit()
            return cursor.lastrowid
    
    def update_application_status(self, application_id: int, status: str, 
                                 notes: str = None) -> bool:
        """Update application status."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE applications SET 
                    status = ?, notes = COALESCE(?, notes),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, notes, application_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def list_applications(self, status: str = None, limit: int = 50) -> List[Dict]:
        """List applications with internship and company info."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT a.*, i.title as job_title, c.name as company_name
                FROM applications a
                LEFT JOIN internships i ON a.internship_id = i.id
                LEFT JOIN companies c ON a.company_id = c.id
            """
            params = []
            
            if status:
                query += " WHERE a.status = ?"
                params.append(status)
            
            query += " ORDER BY a.updated_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            return [dict(r) for r in cursor.fetchall()]
    
    # ========================================================================
    # STATISTICS
    # ========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            tables = ['companies', 'internships', 'applications', 'contacts',
                     'documents', 'offers_received', 'scrape_runs', 'job_tags', 'saved_searches']
            
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                    stats[table] = cursor.fetchone()['count']
                except:
                    stats[table] = 0
            
            # Additional stats (wrapped in try/except for empty tables)
            try:
                cursor.execute("SELECT COUNT(*) FROM internships WHERE is_remote = 1")
                stats['remote_jobs'] = cursor.fetchone()[0]
            except:
                stats['remote_jobs'] = 0
            
            try:
                cursor.execute("SELECT COUNT(DISTINCT site) FROM internships")
                stats['sources'] = cursor.fetchone()[0]
            except:
                stats['sources'] = 0
            
            try:
                cursor.execute("""
                    SELECT site, COUNT(*) as count FROM internships 
                    GROUP BY site ORDER BY count DESC
                """)
                stats['jobs_by_site'] = {r['site']: r['count'] for r in cursor.fetchall()}
            except:
                stats['jobs_by_site'] = {}
            
            return stats
    
    def close(self):
        """Cleanup (connections auto-close with context managers)."""
        pass
