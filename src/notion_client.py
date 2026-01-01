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

import sqlite3
import os
from datetime import datetime
from .config import settings
from .logger_setup import get_logger
import json

logger = get_logger("sqlite_client", settings.LOG_LEVEL)

class DatabaseClient:
    def __init__(self, db_path=None):
        """Initialize SQLite database connection"""
        self.db_path = db_path or getattr(settings, 'DATABASE_PATH', 'data/internship_sync_new.db')
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
    
    def close(self):
        """Close database connection (for cleanup)"""
        # SQLite connections are closed automatically with context managers
        pass

import sqlite3
import os
from datetime import datetime
from .config import settings
from .logger_setup import get_logger
import json

logger = get_logger("sqlite_client", settings.LOG_LEVEL)

class DatabaseClient:
    def __init__(self, db_path=None):
        """Initialize SQLite database connection"""
        self.db_path = db_path or getattr(settings, 'DATABASE_PATH', 'internship_sync_new.db')
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
    
    def close(self):
        """Close database connection (for cleanup)"""
        # SQLite connections are closed automatically with context managers
        pass
# Old Notion client code has been removed in favor of SQLite
# This file now contains only the DatabaseClient class    def find_page_by_property(self, db_id, prop_name, prop_value, max_pages=50):
        """Search for pages in database by property value"""
        try:
            # Use the correct databases.query method
            filter_obj = {
                "property": prop_name,
                "rich_text": {
                    "contains": prop_value
                }
            }
            
            response = self.client.databases.query(
                database_id=db_id,
                filter=filter_obj,
                page_size=min(max_pages, 100)
            )
            
            results = response.get("results", [])
            logger.debug(f"Found {len(results)} pages matching '{prop_value}' in property '{prop_name}'")
            return results
            
        except Exception as e:
            logger.error(f"Error querying Notion database {db_id}: {e}")
            return []

    def create_company(self, company_name, website=None, industry=None, country=None, description=None):
        """Create a new company page in the companies database"""
        try:
            # Get database schema to use correct property names
            schema = self.get_database_schema(settings.DB_COMPANIES)
            title_prop = schema.get("title_property", "Name")
            
            # Build properties object
            properties = {
                title_prop: {
                    "title": [
                        {
                            "text": {
                                "content": company_name
                            }
                        }
                    ]
                }
            }
            
            # Add optional properties if they exist in the database
            db_properties = schema.get("properties", {})
            
            if website and "Website" in db_properties:
                properties["Website"] = {"url": website}
            
            if industry and "Industry" in db_properties:
                properties["Industry"] = {"select": {"name": industry}}
            
            if country and "Country" in db_properties:
                properties["Country"] = {
                    "rich_text": [
                        {
                            "text": {
                                "content": country
                            }
                        }
                    ]
                }
            
            if description and "Description" in db_properties:
                # Limit description to avoid API limits
                desc_text = description[:1900] if len(description) > 1900 else description
                properties["Description"] = {
                    "rich_text": [
                        {
                            "text": {
                                "content": desc_text
                            }
                        }
                    ]
                }
            
            # Create the page
            page = self.client.pages.create(
                parent={
                    "database_id": settings.DB_COMPANIES
                },
                properties=properties
            )
            
            logger.info(f"Created company: {company_name}")
            return page
            
        except Exception as e:
            logger.error(f"Failed to create company {company_name}: {e}")
            return None

    def create_offer(self, job):
        """Create a new job offer page in the offers database"""
        try:
            # Get database schema
            schema = self.get_database_schema(settings.DB_OFFERS)
            title_prop = schema.get("title_property", "Offer Title")
            
            properties = {
                title_prop: {
                    "title": [
                        {
                            "text": {
                                "content": job["title"]
                            }
                        }
                    ]
                }
            }
            
            # Add other properties based on what exists in the database
            db_properties = schema.get("properties", {})
            
            if job.get("url") and "Offer Link" in db_properties:
                properties["Offer Link"] = {"url": job["url"]}
            elif job.get("url") and "Link" in db_properties:
                properties["Link"] = {"url": job["url"]}
            elif job.get("url") and "URL" in db_properties:
                properties["URL"] = {"url": job["url"]}
                
            if job.get("description") and "Description" in db_properties:
                desc_text = job["description"][:1900] if len(job["description"]) > 1900 else job["description"]
                properties["Description"] = {
                    "rich_text": [
                        {
                            "text": {
                                "content": desc_text
                            }
                        }
                    ]
                }
            
            if "Status" in db_properties:
                properties["Status"] = {"select": {"name": "Open"}}
            
            if "Created On" in db_properties:
                properties["Created On"] = {
                    "date": {
                        "start": time.strftime("%Y-%m-%d")
                    }
                }
            
            if job.get("location") and "Location" in db_properties:
                properties["Location"] = {
                    "rich_text": [
                        {
                            "text": {
                                "content": job["location"]
                            }
                        }
                    ]
                }
            
            page = self.client.pages.create(
                parent={
                    "database_id": settings.DB_OFFERS
                },
                properties=properties
            )
            
            logger.info(f"Created offer: {job['title']} at {job['company']}")
            return page
            
        except Exception as e:
            logger.error(f"Failed to create offer {job['title']}: {e}")
            return None

    def ensure_company_and_offer(self, job):
        """High-level method to ensure company exists and create offer"""
        try:
            # Get company database schema to use correct property name
            schema = self.get_database_schema(settings.DB_COMPANIES)

            print("\n\n\n\n\n" ,schema ,"\n\n\n\n\n" );
            title_prop = schema.get("title_property", "Name")
            
            # Check if company exists
            company_results = self.find_page_by_property(
                settings.DB_COMPANIES, 
                title_prop, 
                job["company"]
            )
            
            company_page = None
            if company_results:
                company_page = company_results[0]
                logger.info(f"Company exists: {job['company']}")
            else:
                # Create company
                company_page = self.create_company(job["company"])
                if not company_page:
                    logger.error("Failed to create company, skipping offer creation")
                    return None
            
            # Check if offer already exists
            offer_schema = self.get_database_schema(settings.DB_OFFERS)
            
            # Try different possible property names for the link
            link_properties = ["Offer Link", "Link", "URL"]
            offer_exists = False
            
            for link_prop in link_properties:
                if link_prop in offer_schema.get("properties", {}):
                    existing_offers = self.find_page_by_property(
                        settings.DB_OFFERS, 
                        link_prop, 
                        job.get("url", "")
                    )
                    if existing_offers:
                        logger.info(f"Offer already exists: {job['url']}")
                        offer_exists = True
                        break
            
            if not offer_exists and job.get("url"):
                # Create the offer
                offer_page = self.create_offer(job)
                return offer_page
            
            return company_page
            
        except Exception as e:
            logger.exception(f"Failed to process job {job.get('title', 'Unknown')}: {e}")
            return None