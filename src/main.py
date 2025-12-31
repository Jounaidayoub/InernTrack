#!/usr/bin/env python3
"""
Internship Sync - Main Pipeline Module

This is the main entry point for the internship synchronization pipeline.
It orchestrates the complete workflow:

1. Fetches job listings from multiple sources using JobSpy
2. Normalizes and filters internship-specific positions
3. Removes duplicate entries
4. Syncs data to Notion databases (companies and offers)

The pipeline supports:
- Multi-site scraping (LinkedIn, Indeed, Glassdoor)
- Intelligent internship filtering using keyword detection
- Dry-run mode for testing without actual Notion updates
- Comprehensive logging and error handling

Usage:
    python -m src.main
    
Environment Variables:
    NOTION_TOKEN: Required Notion integration token
    DB_COMPANIES_ID: Companies database ID in Notion
    DB_OFFERS_ID: Job offers database ID in Notion
    DRY_RUN: Set to 'true' to test without uploading
    
Author: El Moujahid Marouane
Version: 1.0
"""

from .logger_setup import get_logger
from .config import settings
from .jobspy_client import fetch_jobs
from .normalizer import normalize_job
from .database_client import DatabaseClient
import json

logger = get_logger("main", settings.LOG_LEVEL)





class Pipeline:

    def __init__(self):
        """Initialize pipeline state."""
        self.db = None
        self.success_count = 0

    def init_db(self):
        """Initialize the `DatabaseClient` instance."""
        try:
            self.db = DatabaseClient()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def fetch_raw_jobs(self):
        """Fetch raw jobs from configured sources via JobSpy."""
        raw_jobs = fetch_jobs()
        logger.info("Raw jobs fetched: %d", len(raw_jobs) if raw_jobs is not None else 0)
        return raw_jobs

    def normalize_and_filter(self, raw_jobs):
        """Normalize jobs and filter only internship positions."""
        if not raw_jobs:
            logger.warning("No jobs fetched, exiting")
            return []

        normalized = [normalize_job(rj) for rj in raw_jobs if rj]
        interns = [j for j in normalized if j.get("is_intern")]
        logger.info("Filtered internships: %d", len(interns))
        return interns

    def process_job(self, job):
        """Process a single job: log, optionally dry-run, and persist to DB."""
        logger.info("Processing: %s - %s", job.get("company"), job.get("title"))

        if settings.DRY_RUN:
            logger.info("[DRY RUN] Would create company and internship for: %s", job.get("url", "No URL"))
            return True

        # Use `default=str` so non-JSON types (e.g., date) serialize safely
        pretty = json.dumps(job, indent=2, ensure_ascii=False, sort_keys=True, default=str)
        logger.info("Job details:\n%s", pretty)

        result = self.db.ensure_company_and_internship(job)
        return bool(result)

    def append_job_csv(self, job, csv_path=None, fields=None):
        """Append a job record to a CSV file (creates file with header if missing)."""
        import csv
        import os

        csv_path = csv_path or os.path.join("data", "internships.csv")
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)

        default_fields = ["company", "title", "url", "location", "is_intern", "description"]
        fields = fields or default_fields

        write_header = not os.path.exists(csv_path)

        try:
            with open(csv_path, "a", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=fields)
                if write_header:
                    writer.writeheader()

                # Ensure all values are strings for CSV writing
                row = {k: ("" if job.get(k) is None else str(job.get(k))) for k in fields}
                writer.writerow(row)

            logger.info("Appended job to CSV: %s", csv_path)
            return True
        except Exception as e:
            logger.error(f"Failed to append job to CSV {csv_path}: {e}")
            return False

    def show_stats(self):
        """Log database statistics for all tables."""
        try:
            stats = self.db.get_stats()
            logger.info("Database statistics:")
            for table, count in stats.items():
                logger.info(f"  {table}: {count} records")
        except Exception as e:
            logger.error(f"Failed to get database statistics: {e}")

    def run(self):
        """Run the full pipeline end-to-end."""
        logger.info("Start pipeline")

        try:
            self.init_db()
        except Exception:
            return

        raw_jobs = self.fetch_raw_jobs()
        interns = self.normalize_and_filter(raw_jobs)

        if not interns:
            logger.info("No unique internship offers to process")
            return

        logger.debug(interns);

        for job in interns:
            try:
                ok = self.process_job(job)
                if ok:
                    self.success_count += 1
            except Exception:
                logger.exception("Failed to sync job")

        self.show_stats()
        logger.info("Pipeline completed. Successfully processed: %d/%d jobs", self.success_count, len(interns))


if __name__ == "__main__":
    Pipeline().run()