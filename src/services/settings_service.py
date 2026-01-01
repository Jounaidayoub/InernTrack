"""
Settings Service

Manages scraping settings stored in database with .env defaults.
Provides CRUD operations for configuration management.

Author: El Moujahid Marouane
Version: 1.0
"""

import json
from datetime import datetime
from typing import Optional, Dict, Any, List

from .base import ServiceResult
from ..database_client import DatabaseClient
from ..config import settings as env_settings
from ..logger_setup import get_logger

logger = get_logger("services.settings")

# Default settings schema with types and validation
SETTINGS_SCHEMA = {
    # Search Settings
    'search_terms': {
        'type': 'list',
        'label': 'Search Terms',
        'description': 'Job titles or keywords to search for (comma-separated)',
        'default': lambda: env_settings.SEARCH_TERMS,
        'placeholder': 'Software Engineer Intern, Data Science Intern',
    },
    'locations': {
        'type': 'list',
        'label': 'Locations',
        'description': 'Geographic locations to search in (comma-separated)',
        'default': lambda: env_settings.LOCATIONS,
        'placeholder': 'Morocco, Remote, France',
    },
    'site_names': {
        'type': 'multiselect',
        'label': 'Job Sites',
        'description': 'Job boards to scrape from',
        'default': lambda: env_settings.SITE_NAMES,
        'options': ['linkedin', 'indeed', 'glassdoor', 'zip_recruiter', 'google'],
    },
    
    # Filters
    'job_type': {
        'type': 'select',
        'label': 'Job Type',
        'description': 'Type of employment to search for',
        'default': lambda: env_settings.JOB_TYPE,
        'options': ['internship', 'fulltime', 'parttime', 'contract'],
    },
    'experience_levels': {
        'type': 'multiselect',
        'label': 'Experience Levels',
        'description': 'Required experience levels',
        'default': lambda: env_settings.EXPERIENCE_LEVELS,
        'options': ['internship', 'entry_level', 'associate', 'mid_senior', 'director', 'executive'],
    },
    'is_remote': {
        'type': 'select',
        'label': 'Remote Work',
        'description': 'Filter by remote work availability',
        'default': lambda: 'true' if env_settings.IS_REMOTE is True else ('false' if env_settings.IS_REMOTE is False else 'any'),
        'options': ['any', 'true', 'false'],
    },
    'country_indeed': {
        'type': 'text',
        'label': 'Indeed Country',
        'description': 'Country code for Indeed searches',
        'default': lambda: env_settings.COUNTRY_INDEED,
        'placeholder': 'Morocco',
    },
    
    # Scraping Options
    'results_wanted': {
        'type': 'number',
        'label': 'Results Per Search',
        'description': 'Maximum results to fetch per search query',
        'default': lambda: env_settings.RESULTS_WANTED,
        'min': 1,
        'max': 500,
    },
    'hours_old': {
        'type': 'number',
        'label': 'Hours Old',
        'description': 'Only fetch jobs posted within this many hours (leave empty for all)',
        'default': lambda: env_settings.HOURS_OLD,
        'min': 1,
        'max': 720,
        'nullable': True,
    },
    'linkedin_fetch_description': {
        'type': 'boolean',
        'label': 'Fetch LinkedIn Descriptions',
        'description': 'Fetch full job descriptions from LinkedIn (slower)',
        'default': lambda: env_settings.LINKEDIN_FETCH_DESCRIPTION,
    },
    'description_format': {
        'type': 'select',
        'label': 'Description Format',
        'description': 'Output format for job descriptions',
        'default': lambda: env_settings.DESCRIPTION_FORMAT,
        'options': ['markdown', 'html'],
    },
    
    # Advanced
    'easy_apply': {
        'type': 'boolean',
        'label': 'Easy Apply Only',
        'description': 'Only fetch jobs with easy application options',
        'default': lambda: env_settings.EASY_APPLY,
    },
    'proxy': {
        'type': 'text',
        'label': 'Proxy URL',
        'description': 'HTTP proxy for scraping (optional)',
        'default': lambda: env_settings.PROXY or '',
        'placeholder': 'http://proxy:port',
        'nullable': True,
    },
    'verbose': {
        'type': 'select',
        'label': 'Verbosity Level',
        'description': 'Scraper logging verbosity',
        'default': lambda: str(env_settings.VERBOSE),
        'options': ['0', '1', '2', '3'],
    },
    'dry_run': {
        'type': 'boolean',
        'label': 'Dry Run Mode',
        'description': 'Test mode - no data will be saved',
        'default': lambda: env_settings.DRY_RUN,
    },
}


class SettingsService:
    """Service for managing scraping settings."""
    
    def __init__(self, db: DatabaseClient = None):
        self.db = db or DatabaseClient()
        self._ensure_settings_table()
    
    def _ensure_settings_table(self):
        """Create settings table if it doesn't exist."""
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
    
    def get_settings(self) -> ServiceResult:
        """
        Get all settings with schema info.
        
        Returns current values from database, falling back to .env defaults.
        """
        try:
            # Get saved settings from database
            saved = {}
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute('SELECT key, value FROM settings')
                for row in cur.fetchall():
                    saved[row['key']] = row['value']
            
            # Build settings with schema
            settings_data = {}
            for key, schema in SETTINGS_SCHEMA.items():
                # Get value: saved > default
                if key in saved:
                    raw_value = saved[key]
                    # Parse based on type
                    if schema['type'] in ['list', 'multiselect']:
                        value = json.loads(raw_value) if raw_value else []
                    elif schema['type'] == 'boolean':
                        value = raw_value.lower() == 'true' if raw_value else False
                    elif schema['type'] == 'number':
                        value = int(raw_value) if raw_value and raw_value != 'null' else None
                    else:
                        value = raw_value
                else:
                    # Use default from .env
                    default_fn = schema['default']
                    value = default_fn() if callable(default_fn) else default_fn
                
                # Build clean schema without lambda functions
                clean_schema = {
                    'type': schema['type'],
                    'label': schema.get('label', key),
                    'description': schema.get('description', ''),
                }
                # Add optional fields if present
                if 'options' in schema:
                    clean_schema['options'] = schema['options']
                if 'placeholder' in schema:
                    clean_schema['placeholder'] = schema['placeholder']
                if 'min' in schema:
                    clean_schema['min'] = schema['min']
                if 'max' in schema:
                    clean_schema['max'] = schema['max']
                
                settings_data[key] = {
                    'value': value,
                    'schema': clean_schema,
                }
            
            return ServiceResult(success=True, data={
                'settings': settings_data,
            })
        
        except Exception as e:
            logger.error(f"Failed to get settings: {e}")
            return ServiceResult(success=False, error=str(e), status_code=500)
    
    def update_settings(self, updates: Dict[str, Any]) -> ServiceResult:
        """
        Update multiple settings.
        
        Args:
            updates: Dict of key-value pairs to update
            
        Returns:
            ServiceResult indicating success/failure
        """
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                
                updated_keys = []
                for key, value in updates.items():
                    if key not in SETTINGS_SCHEMA:
                        continue
                    
                    schema = SETTINGS_SCHEMA[key]
                    
                    # Serialize value based on type
                    if schema['type'] in ['list', 'multiselect']:
                        if isinstance(value, str):
                            value = [v.strip() for v in value.split(',') if v.strip()]
                        serialized = json.dumps(value)
                    elif schema['type'] == 'boolean':
                        serialized = 'true' if value else 'false'
                    elif schema['type'] == 'number':
                        serialized = str(value) if value is not None else 'null'
                    else:
                        serialized = str(value) if value is not None else ''
                    
                    # Upsert
                    cur.execute('''
                        INSERT INTO settings (key, value, updated_at)
                        VALUES (?, ?, ?)
                        ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = ?
                    ''', (key, serialized, datetime.utcnow().isoformat(),
                          serialized, datetime.utcnow().isoformat()))
                    
                    updated_keys.append(key)
                
                conn.commit()
            
            logger.info(f"Updated settings: {updated_keys}")
            return ServiceResult(success=True, data={'updated': updated_keys})
        
        except Exception as e:
            logger.error(f"Failed to update settings: {e}")
            return ServiceResult(success=False, error=str(e), status_code=500)
    
    def reset_to_defaults(self) -> ServiceResult:
        """Reset all settings to .env defaults."""
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute('DELETE FROM settings')
                conn.commit()
            
            logger.info("Reset all settings to defaults")
            return ServiceResult(success=True, data={'message': 'Settings reset to defaults'})
        
        except Exception as e:
            logger.error(f"Failed to reset settings: {e}")
            return ServiceResult(success=False, error=str(e), status_code=500)
    
    def get_effective_config(self) -> Dict[str, Any]:
        """
        Get effective configuration for scraping.
        
        Returns a config dict compatible with the scraper.
        """
        result = self.get_settings()
        if not result.success:
            # Fall back to env defaults
            return env_settings.get_scrape_config()
        
        settings_data = result.data['settings']
        
        # Build config
        config = {
            'search_terms': settings_data['search_terms']['value'],
            'locations': settings_data['locations']['value'],
            'site_name': settings_data['site_names']['value'],
            'job_type': settings_data['job_type']['value'],
            'experience_level': settings_data['experience_levels']['value'],
            'results_wanted': settings_data['results_wanted']['value'] or 100,
            'country_indeed': settings_data['country_indeed']['value'],
            'linkedin_fetch_description': settings_data['linkedin_fetch_description']['value'],
            'description_format': settings_data['description_format']['value'],
            'verbose': int(settings_data['verbose']['value']),
            'dry_run': settings_data['dry_run']['value'],
        }
        
        # Handle is_remote
        is_remote = settings_data['is_remote']['value']
        if is_remote == 'true':
            config['is_remote'] = True
        elif is_remote == 'false':
            config['is_remote'] = False
        # else: don't include (any)
        
        # Optional fields
        hours_old = settings_data['hours_old']['value']
        if hours_old:
            config['hours_old'] = hours_old
        
        proxy = settings_data['proxy']['value']
        if proxy:
            config['proxy'] = proxy
        
        if settings_data['easy_apply']['value']:
            config['easy_apply'] = True
        
        return config
