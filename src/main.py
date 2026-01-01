#!/usr/bin/env python3
"""
Internship Sync - Main Pipeline Module (v2.0)

Main entry point for the internship synchronization pipeline.
Orchestrates:

1. Scrape run auditing (start/complete)
2. Job fetching from JobSpy (LinkedIn, Indeed)
3. Normalization and filtering
4. Deduplication by job URL
5. Database persistence

Features:
- Scrape run tracking with statistics
- Full JobSpy field capture
- Dry-run mode for testing
- Comprehensive logging

Usage:
    python -m src.main
    
Environment Variables:
    DATABASE_PATH: SQLite database path
    DRY_RUN: Set to 'true' for testing
    
Author: El Moujahid Marouane
Version: 2.0
"""

from .logger_setup import get_logger
from .config import settings
from .jobspy_client import fetch_jobs
from .normalizer import normalize_job, normalize_jobs
from .database_client import DatabaseClient
import json

logger = get_logger("main", settings.LOG_LEVEL)


class Pipeline:
    """
    Job scraping and synchronization pipeline.
    
    Manages fetching, normalizing, filtering, and persisting
    internship listings with scrape run auditing.
    """

    def __init__(self):
        """Initialize pipeline state."""
        self.db = None
        self.scrape_run_id = None
        self.stats = {
            "total_found": 0,
            "new_jobs": 0,
            "duplicates": 0,
            "errors": 0
        }

    def init_db(self):
        """Initialize DatabaseClient."""
        try:
            self.db = DatabaseClient()
            logger.info("Database initialized")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    def start_scrape_run(self):
        """Start a new scrape run for auditing."""
        if settings.DRY_RUN:
            logger.info("[DRY RUN] Skipping scrape run creation")
            return
        
        try:
            search_terms = getattr(settings, 'SEARCH_TERMS', [])
            locations = getattr(settings, 'LOCATIONS', [])
            sites = getattr(settings, 'SITE_NAMES', [])
            
            self.scrape_run_id = self.db.start_scrape_run(
                search_terms=search_terms,
                locations=locations,
                sites=sites
            )
            logger.info(f"Started scrape run: {self.scrape_run_id}")
        except Exception as e:
            logger.warning(f"Failed to start scrape run: {e}")

    def complete_scrape_run(self, error_message: str = None):
        """Complete scrape run with statistics."""
        if settings.DRY_RUN or not self.scrape_run_id:
            return
        
        try:
            self.db.complete_scrape_run(
                run_id=self.scrape_run_id,
                total_found=self.stats["total_found"],
                new_jobs=self.stats["new_jobs"],
                duplicates=self.stats["duplicates"],
                errors=self.stats["errors"],
                error_message=error_message
            )
        except Exception as e:
            logger.warning(f"Failed to complete scrape run: {e}")

    def fetch_raw_jobs(self):
        """Fetch raw jobs from JobSpy."""
        raw_jobs = fetch_jobs()
        count = len(raw_jobs) if raw_jobs else 0
        logger.info(f"Raw jobs fetched: {count}")
        self.stats["total_found"] = count
        return raw_jobs

    def normalize_and_filter(self, raw_jobs):
        """Normalize jobs and filter internships only."""
        if not raw_jobs:
            logger.warning("No jobs to process")
            return []

        normalized = normalize_jobs(raw_jobs)
        interns = [j for j in normalized if j.get("is_intern")]
        logger.info(f"Filtered internships: {len(interns)}")
        return interns

    def process_job(self, job):
        """Process single job: check duplicate, persist to DB."""
        logger.info(f"Processing: {job.get('company')} - {job.get('title')}")

        if settings.DRY_RUN:
            logger.info(f"[DRY RUN] Would create: {job.get('job_url')}")
            return True

        # Check for duplicate
        job_url = job.get("job_url") or job.get("url")
        if job_url:
            existing = self.db.find_internship_by_url(job_url)
            if existing:
                logger.debug(f"Duplicate: {job_url}")
                self.stats["duplicates"] += 1
                return False

        # Process job
        result = self.db.ensure_company_and_internship(job, self.scrape_run_id)
        if result:
            self.stats["new_jobs"] += 1
            return True
        else:
            self.stats["errors"] += 1
            return False

    def append_job_csv(self, job, csv_path=None, fields=None):
        """Append job to CSV file."""
        import csv
        import os

        csv_path = csv_path or os.path.join("data", "internships.csv")
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)

        default_fields = ["company", "title", "job_url", "location", "site", "is_intern"]
        fields = fields or default_fields

        write_header = not os.path.exists(csv_path)

        try:
            with open(csv_path, "a", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=fields)
                if write_header:
                    writer.writeheader()
                row = {k: ("" if job.get(k) is None else str(job.get(k))) for k in fields}
                writer.writerow(row)
            return True
        except Exception as e:
            logger.error(f"CSV write failed: {e}")
            return False

    def show_stats(self):
        """Log database statistics."""
        try:
            stats = self.db.get_stats()
            logger.info("Database statistics:")
            for table, count in stats.items():
                if isinstance(count, dict):
                    logger.info(f"  {table}:")
                    for k, v in count.items():
                        logger.info(f"    {k}: {v}")
                else:
                    logger.info(f"  {table}: {count}")
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")

    def run(self):
        """Run the full pipeline."""
        logger.info("Starting pipeline")
        error_message = None

        try:
            self.init_db()
        except Exception:
            return

        self.start_scrape_run()

        try:
            raw_jobs = self.fetch_raw_jobs()
            interns = self.normalize_and_filter(raw_jobs)

            if not interns:
                logger.info("No internships to process")
                return

            for job in interns:
                try:
                    self.process_job(job)
                except Exception as e:
                    logger.exception(f"Job processing failed: {e}")
                    self.stats["errors"] += 1

            self.show_stats()
            logger.info(
                f"Pipeline complete: {self.stats['new_jobs']} new, "
                f"{self.stats['duplicates']} duplicates, "
                f"{self.stats['errors']} errors"
            )

        except Exception as e:
            error_message = str(e)
            logger.exception("Pipeline failed")
        finally:
            self.complete_scrape_run(error_message)


if __name__ == "__main__":
    Pipeline().run()
