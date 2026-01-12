#!/usr/bin/env python3
"""
Configuration Management Module

This module handles all configuration settings for the internship sync pipeline.
It loads environment variables from .env files and provides a centralized
Settings class for accessing configuration throughout the application.

Configuration Categories:

1. Database Settings:
   - DATABASE_PATH: SQLite database location

2. Job Scraping Settings:
   - SEARCH_TERMS: Job search keywords (comma-separated)
   - LOCATIONS: Geographic search locations (comma-separated)
   - SITE_NAMES: Job boards to scrape from
   - RESULTS_WANTED: Maximum results per search
   - HOURS_OLD: Filter for recently posted jobs
   - JOB_TYPE: Type of employment (internship, fulltime, etc.)
   - EXPERIENCE_LEVELS: Required experience levels
   - IS_REMOTE: Remote work preference
   - COUNTRY_INDEED: Country code for Indeed searches

3. Advanced Scraping Options:
   - EASY_APPLY: Filter for easy application jobs
   - MIN_SALARY/MAX_SALARY: Salary range filters
   - LINKEDIN_FETCH_DESCRIPTION: Fetch full job descriptions
   - DESCRIPTION_FORMAT: Output format for descriptions
   - PROXY: Proxy server configuration

4. Application Behavior:
   - DRY_RUN: Boolean flag for testing mode
   - LOG_LEVEL: Logging verbosity level
   - VERBOSE: Scraper verbosity level

The settings are loaded automatically when the module is imported,
making configuration available as `settings.PROPERTY_NAME`.

Example:
    from src.config import settings
    
    print(f"Dry run mode: {settings.DRY_RUN}")
    print(f"Search terms: {settings.SEARCH_TERMS}")
    
    # Get scraping configuration
    scrape_config = settings.get_scrape_config()

Author: El Moujahid Marouane
Version: 2.0
"""

import os
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup module logger
logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when there's an error in configuration"""
    pass


class Settings:
    """
    Centralized configuration management class.
    
    This class loads all configuration from environment variables and provides
    validated, typed access to settings throughout the application.
    """
    
    # ============================================================================
    # DATABASE CONFIGURATION
    # ============================================================================
    
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "data/internship_sync_new.db")
    
    @classmethod
    def ensure_database_directory(cls) -> Path:
        """
        Ensure the database directory exists.
        
        Returns:
            Path: Path object for the database directory
        """
        db_path = Path(cls.DATABASE_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return db_path
    
    # ============================================================================
    # JOB SCRAPING CONFIGURATION
    # ============================================================================
    
    SEARCH_TERMS: List[str] = [
        term.strip() 
        for term in os.getenv("SEARCH_TERMS", "Software Engineer Intern").split(",")
        if term.strip()  # Filter out empty strings
    ]
    
    LOCATIONS: List[str] = [
        loc.strip() 
        for loc in os.getenv("LOCATIONS", "Morocco").split(",")
        if loc.strip()
    ]
    
    SITE_NAMES: List[str] = [
        site.strip().lower() 
        for site in os.getenv("SITE_NAMES", "linkedin,indeed").split(",")
        if site.strip()
    ]
    
    RESULTS_WANTED: int = int(os.getenv("RESULTS_WANTED", "100"))
    
    HOURS_OLD: Optional[int] = (
        int(os.getenv("HOURS_OLD")) 
        if os.getenv("HOURS_OLD") and os.getenv("HOURS_OLD").strip() 
        else None
    )
    
    # ============================================================================
    # JOB FILTERS
    # ============================================================================
    
    JOB_TYPE: str = os.getenv("JOB_TYPE", "internship").lower()
    
    EXPERIENCE_LEVELS: List[str] = [
        level.strip().lower() 
        for level in os.getenv("EXPERIENCE_LEVELS", "internship,entry_level").split(",")
        if level.strip()
    ]
    
    IS_REMOTE: Optional[bool] = {
        "true": True,
        "false": False,
        "none": None,
        "": None
    }.get(os.getenv("IS_REMOTE", "none").lower().strip())
    
    COUNTRY_INDEED: str = os.getenv("COUNTRY_INDEED", "Morocco")
    
    # ============================================================================
    # ADVANCED SCRAPING OPTIONS
    # ============================================================================
    
    
    EASY_APPLY: bool = os.getenv("EASY_APPLY", "false").lower().strip() == "true"
    
    LINKEDIN_FETCH_DESCRIPTION: bool = (
        os.getenv("LINKEDIN_FETCH_DESCRIPTION", "false").lower().strip() == "true"
    )
    
    DESCRIPTION_FORMAT: str = os.getenv("DESCRIPTION_FORMAT", "markdown").lower()
    
    PROXY: Optional[str] = (
        os.getenv("PROXY").strip() 
        if os.getenv("PROXY") and os.getenv("PROXY").strip() 
        else None
    )
    
    # ============================================================================
    # APPLICATION BEHAVIOR
    # ============================================================================
    
    DRY_RUN: bool = os.getenv("DRY_RUN", "false").lower().strip() == "true"
    
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    
    VERBOSE: int = int(os.getenv("VERBOSE", "2"))

    # ============================================================================
    # LLM CONFIGURATION (Resume Generator)
    # ============================================================================

    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    LLM_API_KEY: Optional[str] = os.getenv("LLM_API_KEY")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o")
    
    # ============================================================================
    # VALIDATION
    # ============================================================================
    
    @classmethod
    def validate(cls) -> None:
        """
        Validate configuration settings.
        
        Raises:
            ConfigurationError: If any required settings are invalid
        """
        errors = []
        
        # Validate required lists are not empty
        if not cls.SEARCH_TERMS:
            errors.append("SEARCH_TERMS cannot be empty")
        
        if not cls.LOCATIONS:
            errors.append("LOCATIONS cannot be empty")
        
        if not cls.SITE_NAMES:
            errors.append("SITE_NAMES cannot be empty")
        
        # Validate site names
        valid_sites = {"indeed", "linkedin", "zip_recruiter", "glassdoor", "google"}
        invalid_sites = set(cls.SITE_NAMES) - valid_sites
        if invalid_sites:
            errors.append(
                f"Invalid SITE_NAMES: {invalid_sites}. "
                f"Valid options: {valid_sites}"
            )
        
        # Validate job type
        valid_job_types = {"fulltime", "parttime", "internship", "contract"}
        if cls.JOB_TYPE not in valid_job_types:
            errors.append(
                f"Invalid JOB_TYPE: '{cls.JOB_TYPE}'. "
                f"Valid options: {valid_job_types}"
            )
        
        # Validate experience levels
        valid_experience = {
            "internship", "entry_level", "associate", 
            "mid_senior", "director", "executive"
        }
        invalid_experience = set(cls.EXPERIENCE_LEVELS) - valid_experience
        if invalid_experience:
            errors.append(
                f"Invalid EXPERIENCE_LEVELS: {invalid_experience}. "
                f"Valid options: {valid_experience}"
            )
        
        # Validate numeric values
        if cls.RESULTS_WANTED <= 0:
            errors.append("RESULTS_WANTED must be greater than 0")
        
        if cls.HOURS_OLD is not None and cls.HOURS_OLD <= 0:
            errors.append("HOURS_OLD must be greater than 0 or None")
        
        # Validate log level
        valid_log_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if cls.LOG_LEVEL not in valid_log_levels:
            errors.append(
                f"Invalid LOG_LEVEL: '{cls.LOG_LEVEL}'. "
                f"Valid options: {valid_log_levels}"
            )
        
        # Validate verbose level
        if cls.VERBOSE not in [0, 1, 2, 3]:
            errors.append("VERBOSE must be 0, 1, 2, or 3")
        
        # Validate description format
        valid_formats = {"markdown", "html"}
        if cls.DESCRIPTION_FORMAT not in valid_formats:
            errors.append(
                f"Invalid DESCRIPTION_FORMAT: '{cls.DESCRIPTION_FORMAT}'. "
                f"Valid options: {valid_formats}"
            )
        
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ConfigurationError(error_msg)
    
    # ============================================================================
    # HELPER METHODS
    # ============================================================================
    
    @classmethod
    def get_scrape_config(cls) -> Dict[str, Any]:
        """
        Get configuration dictionary for scrape_jobs function.
        
        NOTE: search_term and location must be passed separately when calling scrape_jobs.
        This method returns the base configuration that's common across all searches.
        
        Returns:
            Dict[str, Any]: Configuration dictionary with all scraping parameters
        """
        config = {
            "site_name": cls.SITE_NAMES,  # Correct parameter name
            "results_wanted": cls.RESULTS_WANTED,
            "job_type": cls.JOB_TYPE,
            "experience_level": cls.EXPERIENCE_LEVELS,  # Added this
            "country_indeed": cls.COUNTRY_INDEED,
            "linkedin_fetch_description": cls.LINKEDIN_FETCH_DESCRIPTION,
            "description_format": cls.DESCRIPTION_FORMAT,
            "verbose": cls.VERBOSE,
        }
        
        # Only include is_remote if explicitly set to True or False (not None)
        if cls.IS_REMOTE is not None:
            config["is_remote"] = cls.IS_REMOTE
        
        # Add optional parameters only if set
        if cls.HOURS_OLD is not None:
            config["hours_old"] = cls.HOURS_OLD
        
        if cls.PROXY is not None:
            config["proxy"] = cls.PROXY
        
        if cls.EASY_APPLY:
            config["easy_apply"] = cls.EASY_APPLY
        
        return config


    @classmethod
    def get_search_combinations_count(cls) -> int:
        """
        Calculate total number of search combinations.
        
        Returns:
            int: Number of search term × location combinations
        """
        return len(cls.SEARCH_TERMS) * len(cls.LOCATIONS)
    
    @classmethod
    def print_config(cls, detailed: bool = False) -> None:
        """
        Print current configuration for debugging.
        
        Args:
            detailed: If True, print all settings including advanced options
        """
        print("=" * 70)
        print("INTERNSHIP SCRAPER CONFIGURATION")
        print("=" * 70)
        
        # Core settings
        print("\n CORE SETTINGS:")
        print(f"  Database Path:       {cls.DATABASE_PATH}")
        print(f"  Dry Run Mode:        {cls.DRY_RUN}")
        print(f"  Log Level:           {cls.LOG_LEVEL}")
        
        # Search configuration
        print("\n🔍 SEARCH CONFIGURATION:")
        print(f"  Search Terms:        {', '.join(cls.SEARCH_TERMS)}")
        print(f"  Locations:           {', '.join(cls.LOCATIONS)}")
        print(f"  Total Combinations:  {cls.get_search_combinations_count()}")
        print(f"  Results per Search:  {cls.RESULTS_WANTED}")
        print(f"  Sites:               {', '.join(cls.SITE_NAMES)}")
        
        # Job filters
        print("\n JOB FILTERS:")
        print(f"  Job Type:            {cls.JOB_TYPE}")
        print(f"  Experience Levels:   {', '.join(cls.EXPERIENCE_LEVELS)}")
        print(f"  Remote:              {cls.IS_REMOTE if cls.IS_REMOTE is not None else 'Any'}")
        print(f"  Hours Old:           {cls.HOURS_OLD if cls.HOURS_OLD else 'All time'}")
        print(f"  Country (Indeed):    {cls.COUNTRY_INDEED}")
        
        if detailed:
            print("\n  ADVANCED OPTIONS:")
            print(f"  Min Salary:          {cls.MIN_SALARY if cls.MIN_SALARY else 'None'}")
            print(f"  Max Salary:          {cls.MAX_SALARY if cls.MAX_SALARY else 'None'}")
            print(f"  Easy Apply Only:     {cls.EASY_APPLY}")
            print(f"  Fetch Full Desc:     {cls.LINKEDIN_FETCH_DESCRIPTION}")
            print(f"  Description Format:  {cls.DESCRIPTION_FORMAT}")
            print(f"  Proxy:               {cls.PROXY if cls.PROXY else 'None'}")
            print(f"  Verbose Level:       {cls.VERBOSE}")
        
        print("\n" + "=" * 70 + "\n")
    
    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """
        Convert settings to dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary containing all settings
        """
        return {
            "database_path": cls.DATABASE_PATH,
            "search_terms": cls.SEARCH_TERMS,
            "locations": cls.LOCATIONS,
            "site_names": cls.SITE_NAMES,
            "results_wanted": cls.RESULTS_WANTED,
            "hours_old": cls.HOURS_OLD,
            "job_type": cls.JOB_TYPE,
            "experience_levels": cls.EXPERIENCE_LEVELS,
            "is_remote": cls.IS_REMOTE,
            "country_indeed": cls.COUNTRY_INDEED,
            "min_salary": cls.MIN_SALARY,
            "max_salary": cls.MAX_SALARY,
            "easy_apply": cls.EASY_APPLY,
            "linkedin_fetch_description": cls.LINKEDIN_FETCH_DESCRIPTION,
            "description_format": cls.DESCRIPTION_FORMAT,
            "proxy": cls.PROXY,
            "dry_run": cls.DRY_RUN,
            "log_level": cls.LOG_LEVEL,
            "verbose": cls.VERBOSE,
        }


# ============================================================================
# MODULE INITIALIZATION
# ============================================================================

# Create settings instance
settings = Settings()

# Validate configuration on import
try:
    settings.validate()
    logger.debug("Configuration validated successfully")
except ConfigurationError as e:
    logger.error(f"Configuration error: {e}")
    raise

# Ensure database directory exists
settings.ensure_database_directory()


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_logging_config() -> Dict[str, Any]:
    """
    Get logging configuration dictionary.
    
    Returns:
        Dict[str, Any]: Logging configuration for use with logging.basicConfig
    """
    return {
        "level": getattr(logging, settings.LOG_LEVEL),
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "datefmt": "%Y-%m-%d %H:%M:%S"
    }


def setup_logging() -> None:
    """Configure logging based on settings."""
    logging.basicConfig(**get_logging_config())
    
    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


# ============================================================================
# MAIN ENTRY POINT (for testing)
# ============================================================================

if __name__ == "__main__":
    """Test configuration loading and validation."""
    
    setup_logging()
    
    print("\n🧪 Testing Configuration Module\n")
    
    try:
        # Print configuration
        settings.print_config(detailed=True)
        
        # Test scrape config generation
        scrape_config = settings.get_scrape_config()
        print(" Scrape configuration generated successfully")
        print(f"   Config keys: {list(scrape_config.keys())}")
        
        # Test combinations count
        combinations = settings.get_search_combinations_count()
        print(f"\n Will execute {combinations} search combinations")
        print(f"   Expected total results: ~{combinations * settings.RESULTS_WANTED}")
        
        # Test dictionary conversion
        config_dict = settings.to_dict()
        print(f"\n Configuration dictionary created with {len(config_dict)} keys")
        
        print("\n All configuration tests passed!\n")
        
    except ConfigurationError as e:
        print(f"\n❌ Configuration error: {e}\n")
        exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}\n")
        raise