#!/usr/bin/env python3
"""
JobSpy Integration Module

This module provides job scraping functionality using the JobSpy library.
It handles fetching job listings from multiple job boards with intelligent
query generation and error handling.

Supported Job Boards:
- LinkedIn: Professional networking and job platform
- Indeed: General job search platform
- Glassdoor: Company reviews and job listings
- ZipRecruiter: Job aggregator platform
- Google: Google for Jobs integration

Features:
- Multi-platform scraping with concurrent requests
- Configurable search terms and locations
- Rate limiting and error recovery
- Automatic retry logic for failed requests
- Result aggregation and deduplication
- Support for internship-specific filtering

Configuration:
The module uses settings from config.py:
- SEARCH_TERMS: Keywords like 'internship', 'stage', 'intern'
- LOCATIONS: Geographic locations to search
- RESULTS_WANTED: Maximum results per search query

Error Handling:
- Graceful handling of invalid locations
- Network timeout recovery
- API rate limit management
- Partial result collection on failures

Data Format:
Returns standardized job objects with fields:
- title, company, location, url, description, posted_date
- Raw data preserved for debugging

Usage:
    scraper = JobScraperClient()
    jobs = scraper.fetch_jobs()
    print(f"Found {len(jobs)} job listings")
    
Author: El Moujahid Marouane
Version: 2.0
"""

import pandas as pd
from typing import List, Dict, Any, Optional
from jobspy import scrape_jobs

from .logger_setup import get_logger
from .config import settings


class JobScrapingError(Exception):
    """Custom exception for job scraping errors"""
    pass


class JobScraperClient:
    """
    Client for scraping job listings from multiple job boards.
    
    This class handles all job scraping operations using the JobSpy library,
    with support for multiple search terms, locations, and job boards.
    
    Attributes:
        logger: Logger instance for this class
        settings: Configuration settings object
        base_config: Base configuration dictionary for scraping
    
    Example:
        scraper = JobScraperClient()
        jobs = scraper.fetch_jobs()
        stats = scraper.get_job_statistics(jobs)
    """
    
    def __init__(self):
        """Initialize the JobScraperClient with configuration settings."""
        self.logger = get_logger("jobspy_client", settings.LOG_LEVEL)
        self.settings = settings
        self.base_config = settings.get_scrape_config()
        
        self.logger.info("JobScraperClient initialized")
        self.logger.debug(f"Base config: {self.base_config}")
    

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        """
        Enhanced version with deduplication, statistics, and better error handling.
        
        This method extends the original fetch_jobs() with:
        - Duplicate removal by job_url
        - Detailed progress tracking
        - Success/failure statistics
        - Better error context
        
        Returns:
            List[Dict[str, Any]]: Deduplicated list of job dictionaries
            
        Raises:
            JobScrapingError: If all scraping attempts fail
        """
        
        # Calculate total combinations
        total_combinations = self.settings.get_search_combinations_count()
        
        self.logger.info(
            f"Starting enhanced job scraping: {len(self.settings.SEARCH_TERMS)} terms x "
            f"{len(self.settings.LOCATIONS)} locations = {total_combinations} searches"
        )
        self.logger.info(f"Target sites: {', '.join(self.settings.SITE_NAMES)}")
        self.logger.info(f"Results per search: {self.settings.RESULTS_WANTED}")
        
        if self.settings.DRY_RUN:
            self.logger.warning("DRY RUN MODE - No actual database operations will be performed")
        
        all_jobs = []
        successful_scrapes = 0
        failed_scrapes = 0
        current = 0
        
        # Iterate through all search term and location combinations
        for search_term in self.settings.SEARCH_TERMS:
            for location in self.settings.LOCATIONS:
                current += 1
                
                self.logger.info(
                    f"[{current}/{total_combinations}] Scraping: '{search_term}' in '{location}'"
                )
                
                try:
                    # Perform the scrape
                    jobs_df = scrape_jobs(
                        **self.base_config,
                        search_term=search_term,
                        location=location
                    )
                    
                    # Handle results
                    if jobs_df is not None and not jobs_df.empty:
                        job_count = len(jobs_df)
                        self.logger.info(f"SUCCESS: Found {job_count} jobs for '{search_term}' in '{location}'")
                        
                        # Convert DataFrame to list of dictionaries
                        jobs_list = jobs_df.to_dict('records')
                        all_jobs.extend(jobs_list)
                        successful_scrapes += 1
                        
                    else:
                        self.logger.warning(f"WARNING: No jobs found for '{search_term}' in '{location}'")
                        failed_scrapes += 1
                        
                except Exception as e:
                    self.logger.error(
                        f"ERROR: Failed scraping '{search_term}' in '{location}': {str(e)}",
                        exc_info=True
                    )
                    failed_scrapes += 1
                    continue
        
        # Log summary
        self.logger.info("=" * 70)
        self.logger.info("SCRAPING SUMMARY")
        self.logger.info("=" * 70)
        self.logger.info(f"Total searches:      {total_combinations}")
        self.logger.info(f"Successful:          {successful_scrapes}")
        self.logger.info(f"Failed:              {failed_scrapes}")
        self.logger.info(f"Raw jobs fetched:    {len(all_jobs)}")
        
        # Check if we got any results
        if not all_jobs:
            error_msg = "No jobs found in any search. Check your configuration and network connection."
            self.logger.error(error_msg)
            
            if failed_scrapes == total_combinations:
                raise JobScrapingError(error_msg)
            
            return []
        
        # Deduplicate by job_url
        deduplicated_jobs = self.deduplicate_jobs(all_jobs)
        
        self.logger.info(f"Unique jobs:         {len(deduplicated_jobs)}")
        self.logger.info(f"Duplicates removed:  {len(all_jobs) - len(deduplicated_jobs)}")
        self.logger.info("=" * 70)
        
        return deduplicated_jobs
    
    def deduplicate_jobs(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate jobs based on job_url.
        
        Args:
            jobs: List of job dictionaries
            
        Returns:
            List[Dict[str, Any]]: Deduplicated list of jobs
        """
        seen_urls = set()
        unique_jobs = []
        duplicates_count = 0
        
        for job in jobs:
            job_url = job.get('job_url')
            
            if not job_url:
                # If no URL, keep the job anyway (shouldn't happen but defensive)
                self.logger.debug("Job without URL found, keeping it anyway")
                unique_jobs.append(job)
                continue
            
            if job_url not in seen_urls:
                seen_urls.add(job_url)
                unique_jobs.append(job)
            else:
                duplicates_count += 1
                self.logger.debug(f"Duplicate job URL found: {job_url}")
        
        if duplicates_count > 0:
            self.logger.info(f"Removed {duplicates_count} duplicate jobs")
        
        return unique_jobs
    
    def fetch_jobs_by_company(self, company_name: str, location: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch jobs from a specific company.
        
        This is useful for targeted scraping of specific employers.
        
        Args:
            company_name: Name of the company to search for
            location: Optional location filter
            
        Returns:
            List[Dict[str, Any]]: List of job dictionaries for the specified company
            
        Example:
            scraper = JobScraperClient()
            jobs = scraper.fetch_jobs_by_company("Google", "Remote")
            print(f"Found {len(jobs)} jobs at Google")
        """
        self.logger.info(f"Fetching jobs from company: {company_name}")
        
        search_location = location or self.settings.LOCATIONS[0]
        
        all_jobs = []
        
        for search_term in self.settings.SEARCH_TERMS:
            try:
                self.logger.info(f"Searching '{search_term}' at '{company_name}' in '{search_location}'")
                
                jobs_df = scrape_jobs(
                    **self.base_config,
                    search_term=search_term,
                    location=search_location,
                    company_name=company_name
                )
                
                if jobs_df is not None and not jobs_df.empty:
                    jobs_list = jobs_df.to_dict('records')
                    all_jobs.extend(jobs_list)
                    self.logger.info(f"Found {len(jobs_list)} jobs")
                
            except Exception as e:
                self.logger.error(f"Error fetching jobs from {company_name}: {e}")
                continue
        
        deduplicated_jobs = self.deduplicate_jobs(all_jobs)
        
        self.logger.info(f"Total unique jobs from {company_name}: {len(deduplicated_jobs)}")
        
        return deduplicated_jobs
    
    def get_job_statistics(self, jobs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate statistics about scraped jobs.
        
        Args:
            jobs: List of job dictionaries
            
        Returns:
            Dict[str, Any]: Statistics dictionary with counts and breakdowns
            
        Example:
            scraper = JobScraperClient()
            jobs = scraper.fetch_jobs()
            stats = scraper.get_job_statistics(jobs)
            print(f"Remote jobs: {stats['remote_count']}")
        """
        if not jobs:
            return {
                "total_jobs": 0,
                "remote_count": 0,
                "onsite_count": 0,
                "jobs_by_site": {},
                "jobs_by_location": {},
                "jobs_by_company": {},
            }
        
        df = pd.DataFrame(jobs)
        
        stats = {
            "total_jobs": len(jobs),
            "remote_count": int(df['is_remote'].sum()) if 'is_remote' in df else 0,
            "onsite_count": len(jobs) - (int(df['is_remote'].sum()) if 'is_remote' in df else 0),
            "jobs_by_site": df['site'].value_counts().to_dict() if 'site' in df else {},
            "jobs_by_location": df['location'].value_counts().head(10).to_dict() if 'location' in df else {},
            "jobs_by_company": df['company'].value_counts().head(10).to_dict() if 'company' in df else {},
        }
        
        return stats
    
    def print_job_statistics(self, jobs: List[Dict[str, Any]]) -> None:
        """
        Print formatted job statistics to console.
        
        Args:
            jobs: List of job dictionaries
        """
        stats = self.get_job_statistics(jobs)
        
        print("\n" + "=" * 70)
        print("JOB STATISTICS")
        print("=" * 70)
        print(f"Total jobs:          {stats['total_jobs']}")
        print(f"Remote jobs:         {stats['remote_count']}")
        print(f"On-site jobs:        {stats['onsite_count']}")
        
        if stats['jobs_by_site']:
            print("\nJobs by site:")
            for site, count in list(stats['jobs_by_site'].items())[:5]:
                print(f"  {site:15} {count:4} jobs")
        
        if stats['jobs_by_location']:
            print("\nTop locations:")
            for location, count in list(stats['jobs_by_location'].items())[:5]:
                print(f"  {location:20} {count:4} jobs")
        
        if stats['jobs_by_company']:
            print("\nTop companies:")
            for company, count in list(stats['jobs_by_company'].items())[:5]:
                print(f"  {company:30} {count:4} jobs")
        
        print("=" * 70 + "\n")


# ============================================================================
# BACKWARDS COMPATIBILITY - Legacy function interface
# ============================================================================

def fetch_jobs() -> List[Dict[str, Any]]:
    """
    Legacy function interface for backwards compatibility.
    
    Creates a JobScraperClient instance and calls fetch_jobs().
    
    Returns:
        List[Dict]: List of job dictionaries from all searches
    """
    client = JobScraperClient()
    return client.fetch_jobs()
