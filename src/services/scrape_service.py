"""
Scrape Service

Manages scraping operations with real-time logging and status tracking.

Author: El Moujahid Marouane
Version: 1.0
"""

import threading
import queue
import time
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable

from .base import ServiceResult
from .settings_service import SettingsService
from ..database_client import DatabaseClient
from ..logger_setup import get_logger
from ..normalizer import normalize_jobs
from ..company_enricher import extract_emails_with_context

# Import scrape_jobs directly from jobspy
from jobspy import scrape_jobs

logger = get_logger("services.scrape")


class ScrapeLogHandler:
    """Captures log messages for real-time streaming."""
    
    def __init__(self, max_logs: int = 500):
        self.logs: List[Dict[str, Any]] = []
        self.max_logs = max_logs
        self.lock = threading.Lock()
    
    def add(self, level: str, message: str):
        """Add a log entry."""
        with self.lock:
            entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'level': level,
                'message': message,
            }
            self.logs.append(entry)
            
            # Trim old logs
            if len(self.logs) > self.max_logs:
                self.logs = self.logs[-self.max_logs:]
    
    def get_logs(self, since_index: int = 0) -> List[Dict[str, Any]]:
        """Get logs since a given index."""
        with self.lock:
            return self.logs[since_index:]
    
    def clear(self):
        """Clear all logs."""
        with self.lock:
            self.logs = []


class ScrapeRunner:
    """
    Runs scraping in a background thread with logging.
    
    Only one scrape can run at a time.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.status = 'idle'  # idle, running, completed, failed
        self.progress = {
            'total_found': 0,
            'processed': 0,
            'new_jobs': 0,
            'duplicates': 0,
            'errors': 0,
        }
        self.scrape_run_id = None
        self.started_at = None
        self.completed_at = None
        self.error_message = None
        self.log_handler = ScrapeLogHandler()
        self._thread: Optional[threading.Thread] = None
        self._stop_requested = False
        self._initialized = True
    
    def is_running(self) -> bool:
        """Check if a scrape is currently running."""
        return self.status == 'running'
    
    def get_status(self) -> Dict[str, Any]:
        """Get current scrape status."""
        return {
            'status': self.status,
            'is_running': self.status == 'running',
            'progress': self.progress,
            'scrape_run_id': self.scrape_run_id,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'error_message': self.error_message,
            'log_count': len(self.log_handler.logs),
        }
    
    def get_logs(self, since_index: int = 0) -> List[Dict[str, Any]]:
        """Get logs since a given index."""
        return self.log_handler.get_logs(since_index)
    
    def log(self, level: str, message: str):
        """Add a log entry."""
        self.log_handler.add(level, message)
        # Also log to file
        getattr(logger, level.lower(), logger.info)(message)
    
    def start(self, config: Dict[str, Any] = None) -> bool:
        """
        Start a scrape run.
        
        Args:
            config: Optional config override
            
        Returns:
            True if started, False if already running
        """
        if self.is_running():
            return False
        
        # Reset state
        self.status = 'running'
        self.progress = {
            'total_found': 0,
            'processed': 0,
            'new_jobs': 0,
            'duplicates': 0,
            'errors': 0,
        }
        self.scrape_run_id = None
        self.started_at = datetime.utcnow().isoformat()
        self.completed_at = None
        self.error_message = None
        self._stop_requested = False
        self.log_handler.clear()
        
        # Start thread
        self._thread = threading.Thread(target=self._run, args=(config,), daemon=True)
        self._thread.start()
        
        return True
    
    def stop(self):
        """Request to stop the current scrape."""
        if self.is_running():
            self._stop_requested = True
            self.log('WARNING', 'Stop requested by user')
    
    def _run(self, config: Dict[str, Any] = None):
        """Run the scrape (in background thread)."""
        db = None
        
        try:
            self.log('INFO', '🚀 Starting scrape pipeline...')
            
            # Get config
            if config is None:
                settings_service = SettingsService()
                config = settings_service.get_effective_config()
            
            self.log('INFO', f"Search terms: {config.get('search_terms', [])}")
            self.log('INFO', f"Locations: {config.get('locations', [])}")
            self.log('INFO', f"Sites: {config.get('site_name', [])}")
            
            # Check dry run
            dry_run = config.get('dry_run', False)
            if dry_run:
                self.log('WARNING', '⚠️ DRY RUN MODE - No data will be saved')
            
            # Initialize database
            db = DatabaseClient()
            self.log('INFO', '✓ Database initialized')
            
            # Start scrape run
            if not dry_run:
                self.scrape_run_id = db.start_scrape_run(
                    search_terms=config.get('search_terms', []),
                    locations=config.get('locations', []),
                    sites=config.get('site_name', [])
                )
                self.log('INFO', f'✓ Scrape run started: #{self.scrape_run_id}')
            
            # Fetch jobs
            self.log('INFO', ' Fetching jobs from job boards...')
            
            # Extract search parameters
            search_terms = config.get('search_terms', ['Software Engineer Intern'])
            locations = config.get('locations', ['Morocco'])
            
            # Build scrape config for jobspy
            scrape_config = {
                'site_name': config.get('site_names', ['linkedin', 'indeed']),
                'results_wanted': config.get('results_wanted', 50),
                'country_indeed': config.get('country_indeed', 'Morocco'),
                'linkedin_fetch_description': config.get('linkedin_fetch_description', False),
                'description_format': config.get('description_format', 'markdown'),
                'verbose': config.get('verbose', 0),
            }
            
            # Add optional parameters
            if config.get('job_type'):
                scrape_config['job_type'] = config.get('job_type')
            if config.get('is_remote') is not None:
                scrape_config['is_remote'] = config.get('is_remote')
            if config.get('hours_old'):
                scrape_config['hours_old'] = config.get('hours_old')
            if config.get('experience_levels'):
                scrape_config['experience_level'] = config.get('experience_levels')
            if config.get('proxy'):
                scrape_config['proxy'] = config.get('proxy')
            if config.get('easy_apply'):
                scrape_config['easy_apply'] = config.get('easy_apply')
            
            raw_jobs = []
            
            for term in search_terms:
                if self._stop_requested:
                    break
                    
                for location in locations:
                    if self._stop_requested:
                        break
                    
                    self.log('INFO', f'  Searching: "{term}" in {location}...')
                    
                    try:
                        jobs_df = scrape_jobs(
                            search_term=term,
                            location=location,
                            **scrape_config
                        )
                        if jobs_df is not None and not jobs_df.empty:
                            jobs = jobs_df.to_dict('records')
                            raw_jobs.extend(jobs)
                            self.log('INFO', f'    Found {len(jobs)} jobs')
                        else:
                            self.log('INFO', f'    No jobs found')
                    except Exception as e:
                        self.log('ERROR', f'    Error: {str(e)[:100]}')
                        self.progress['errors'] += 1
            
            if self._stop_requested:
                self.log('WARNING', '⚠️ Scrape cancelled by user')
                self._complete('cancelled', 'Cancelled by user')
                return
            
            self.progress['total_found'] = len(raw_jobs)
            self.log('INFO', f'✓ Total raw jobs fetched: {len(raw_jobs)}')
            
            if not raw_jobs:
                self.log('WARNING', 'No jobs found to process')
                self._complete('completed')
                return
            
            # Normalize and filter
            self.log('INFO', '🔄 Normalizing and filtering...')
            normalized = normalize_jobs(raw_jobs)
            internships = [j for j in normalized if j.get('is_intern')]
            self.log('INFO', f'✓ Filtered to {len(internships)} internships')
            
            if not internships:
                self.log('WARNING', 'No internships found after filtering')
                self._complete('completed')
                return
            
            # Process jobs
            self.log('INFO', '💾 Processing jobs...')
            
            for i, job in enumerate(internships):
                if self._stop_requested:
                    break
                
                self.progress['processed'] = i + 1
                company = job.get('company', 'Unknown')
                title = job.get('title', 'Unknown')
                
                if dry_run:
                    self.log('DEBUG', f'  [DRY RUN] Would save: {company} - {title}')
                    self.progress['new_jobs'] += 1
                    continue
                
                # Check duplicate
                job_url = job.get('job_url') or job.get('url')
                if job_url:
                    existing = db.find_internship_by_url(job_url)
                    if existing:
                        self.progress['duplicates'] += 1
                        continue
                
                # Save job
                try:
                    result = db.ensure_company_and_internship(job, self.scrape_run_id)
                    if result:
                        self.progress['new_jobs'] += 1
                        self.log('INFO', f'  ✓ {company} - {title}')
                        
                        # Extract contacts
                        company_id = result.get('company_id')
                        if company_id:
                            self._extract_contacts(job, company_id, db)
                    else:
                        self.progress['errors'] += 1
                except Exception as e:
                    self.progress['errors'] += 1
                    self.log('ERROR', f'  ✗ {company} - {title}: {str(e)[:50]}')
            
            if self._stop_requested:
                self.log('WARNING', '⚠️ Scrape cancelled by user')
                self._complete('cancelled', 'Cancelled by user', db)
                return
            
            # Complete
            self.log('INFO', '─' * 40)
            self.log('INFO', f'✅ Scrape completed!')
            self.log('INFO', f'   New jobs: {self.progress["new_jobs"]}')
            self.log('INFO', f'   Duplicates: {self.progress["duplicates"]}')
            self.log('INFO', f'   Errors: {self.progress["errors"]}')
            
            self._complete('completed', db=db)
            
        except Exception as e:
            self.log('ERROR', f'❌ Pipeline failed: {str(e)}')
            logger.exception("Scrape pipeline error")
            self._complete('failed', str(e), db)
    
    def _extract_contacts(self, job: Dict, company_id: int, db: DatabaseClient):
        """Extract contacts from job description."""
        description = job.get('description', '')
        if not description:
            return
        
        contacts = extract_emails_with_context(description)
        if not contacts:
            return
        
        saved = 0
        for contact in contacts:
            try:
                with db.get_connection() as conn:
                    cur = conn.cursor()
                    cur.execute(
                        'SELECT id FROM contacts WHERE company_id = ? AND email = ?',
                        (company_id, contact['email'])
                    )
                    if cur.fetchone():
                        continue
                    
                    cur.execute('''
                        INSERT INTO contacts (company_id, name, email, position, notes)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        company_id,
                        contact['email'].split('@')[0].replace('.', ' ').title(),
                        contact['email'],
                        contact.get('type', 'unknown'),
                        f"Extracted from job posting"
                    ))
                    conn.commit()
                    saved += 1
            except:
                pass
        
        if saved > 0:
            self.log('DEBUG', f'    Extracted {saved} contacts')
    
    def _complete(self, status: str, error_message: str = None, db: DatabaseClient = None):
        """Complete the scrape run."""
        self.status = status
        self.completed_at = datetime.utcnow().isoformat()
        self.error_message = error_message
        
        # Update scrape run in database
        if db and self.scrape_run_id:
            try:
                db.complete_scrape_run(
                    run_id=self.scrape_run_id,
                    total_found=self.progress['total_found'],
                    new_jobs=self.progress['new_jobs'],
                    duplicates=self.progress['duplicates'],
                    errors=self.progress['errors'],
                    error_message=error_message
                )
            except Exception as e:
                self.log('ERROR', f'Failed to complete scrape run: {e}')


class ScrapeService:
    """Service for managing scrape operations."""
    
    def __init__(self):
        self.runner = ScrapeRunner()
        self.settings_service = SettingsService()
    
    def get_status(self) -> ServiceResult:
        """Get current scrape status."""
        return ServiceResult(success=True, data=self.runner.get_status())
    
    def get_logs(self, since_index: int = 0) -> ServiceResult:
        """Get scrape logs."""
        logs = self.runner.get_logs(since_index)
        total = len(self.runner.log_handler.logs)
        return ServiceResult(success=True, data={
            'logs': logs,
            'total': total,
            'next_index': total,  # Next index to query from
        })
    
    def start_scrape(self) -> ServiceResult:
        """Start a new scrape."""
        if self.runner.is_running():
            return ServiceResult(
                success=False,
                error='A scrape is already running',
                status_code=409
            )
        
        # Get effective config
        config = self.settings_service.get_effective_config()
        
        # Start scrape
        self.runner.start(config)
        
        return ServiceResult(success=True, data={
            'message': 'Scrape started',
            'status': self.runner.get_status(),
        })
    
    def stop_scrape(self) -> ServiceResult:
        """Stop the current scrape."""
        if not self.runner.is_running():
            return ServiceResult(
                success=False,
                error='No scrape is running',
                status_code=400
            )
        
        self.runner.stop()
        
        return ServiceResult(success=True, data={
            'message': 'Stop requested',
        })
    
    def get_scrape_history(self, limit: int = 20) -> ServiceResult:
        """Get recent scrape runs."""
        try:
            db = DatabaseClient()
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute('''
                    SELECT id, started_at, completed_at, status,
                           total_found, new_jobs, duplicates, errors,
                           search_terms, locations, sites, error_message
                    FROM scrape_runs
                    ORDER BY started_at DESC
                    LIMIT ?
                ''', (limit,))
                
                runs = [dict(row) for row in cur.fetchall()]
            
            return ServiceResult(success=True, data={'runs': runs})
        
        except Exception as e:
            logger.error(f"Failed to get scrape history: {e}")
            return ServiceResult(success=False, error=str(e), status_code=500)
