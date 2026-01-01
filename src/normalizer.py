#!/usr/bin/env python3
"""
Data Normalization Module (v2.0)

Handles data cleaning and standardization for job listings
from JobSpy. Maps all JobSpy fields to the improved database schema.

Features:
- HTML cleaning for descriptions
- Full JobSpy field mapping
- Salary decomposition (min, max, currency, interval)
- Internship detection (multi-language)
- Data type normalization
- Raw data preservation for debugging

Author: El Moujahid Marouane
Version: 2.0
"""

from bs4 import BeautifulSoup
from datetime import datetime, date
import re
import json

try:
    from .logger_setup import get_logger
except ImportError:
    from logger_setup import get_logger

logger = get_logger("normalizer")


def clean_html(html_text: str) -> str:
    """
    Remove HTML tags and entities from text.
    
    Args:
        html_text: Raw HTML string
        
    Returns:
        Clean plain text
    """
    if not html_text:
        return ""
    if not isinstance(html_text, str):
        html_text = str(html_text)
    soup = BeautifulSoup(html_text, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def _safe_str(value, default: str = "") -> str:
    """Convert value to string safely."""
    if value is None:
        return default
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value).strip()


def _safe_float(value) -> float | None:
    """Convert value to float safely."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _safe_bool(value, default: bool = False) -> bool:
    """Convert value to boolean safely."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes')
    return bool(value)


def is_internship(title: str, description: str = "") -> bool:
    """
    Detect if job is an internship based on title/description.
    
    Supports:
    - English: intern, internship, internee
    - French: stagiaire, stage
    
    Args:
        title: Job title
        description: Job description
        
    Returns:
        True if appears to be an internship
    """
    text = f"{title} {description}".lower()
    pattern = r"\bintern(ship|ee)?\b|stagiaire|stage"
    return bool(re.search(pattern, text, re.I))


def normalize_job(raw_job: dict) -> dict:
    """
    Transform JobSpy output to normalized structure.
    
    Maps all JobSpy fields to database columns:
    - Core: title, company, description, location
    - URLs: job_url, job_url_direct
    - Location: city, state, country
    - Salary: min_amount, max_amount, currency, interval
    - Metadata: site, job_type, date_posted, is_remote
    - Company: company_url, logo_photo_url, industry, etc.
    
    Args:
        raw_job: Raw job dict from JobSpy
        
    Returns:
        Normalized job dict for database insertion
    """
    # Core fields
    title = _safe_str(raw_job.get("title") or raw_job.get("job_title"), "No title")
    company = _safe_str(raw_job.get("company") or raw_job.get("company_name"), "Unknown")
    description = clean_html(raw_job.get("description") or raw_job.get("snippet") or "")
    
    # Location
    location = _safe_str(raw_job.get("location"))
    city = _safe_str(raw_job.get("city"))
    state = _safe_str(raw_job.get("state"))
    country = _safe_str(raw_job.get("country"))
    
    # URLs
    job_url = raw_job.get("job_url") or raw_job.get("url") or raw_job.get("link")
    job_url_direct = raw_job.get("job_url_direct")
    
    # Source and type
    site = _safe_str(raw_job.get("site"), "other")
    job_type = _safe_str(raw_job.get("job_type"), "internship")
    
    # Salary decomposition
    salary_min = _safe_float(raw_job.get("min_amount"))
    salary_max = _safe_float(raw_job.get("max_amount"))
    salary_currency = _safe_str(raw_job.get("currency"), "USD")
    salary_interval = _safe_str(raw_job.get("interval"), "unknown")
    salary_source = _safe_str(raw_job.get("salary_source"))
    
    # Remote work
    is_remote = _safe_bool(raw_job.get("is_remote"))
    
    # Dates
    date_posted = raw_job.get("date_posted")
    if isinstance(date_posted, str):
        try:
            date_posted = datetime.fromisoformat(date_posted.replace('Z', '+00:00')).date()
        except:
            date_posted = None
    
    # Company metadata
    company_url = raw_job.get("company_url")
    company_url_direct = raw_job.get("company_url_direct")
    logo_photo_url = raw_job.get("logo_photo_url")
    company_industry = raw_job.get("company_industry")
    company_num_employees = raw_job.get("company_num_employees")
    company_revenue = raw_job.get("company_revenue")
    company_description = raw_job.get("company_description")
    company_addresses = raw_job.get("company_addresses")
    
    # Additional job fields
    job_level = _safe_str(raw_job.get("job_level"))
    job_function = _safe_str(raw_job.get("job_function"))
    emails = raw_job.get("emails")
    
    # Internship detection
    is_intern = is_internship(title, description)
    
    return {
        # Core job fields
        "title": title,
        "company": company,
        "description": description,
        "location": location,
        
        # Location breakdown
        "city": city,
        "state": state,
        "country": country,
        
        # URLs
        "job_url": job_url,
        "job_url_direct": job_url_direct,
        
        # Source and type
        "site": site,
        "job_type": job_type if job_type else ("internship" if is_intern else "fulltime"),
        "job_level": job_level,
        "job_function": job_function,
        
        # Salary
        "min_amount": salary_min,
        "max_amount": salary_max,
        "currency": salary_currency,
        "interval": salary_interval,
        "salary_source": salary_source,
        
        # Remote
        "is_remote": is_remote,
        
        # Dates
        "date_posted": date_posted,
        
        # Company metadata
        "company_url": company_url,
        "company_url_direct": company_url_direct,
        "logo_photo_url": logo_photo_url,
        "company_industry": company_industry,
        "company_num_employees": company_num_employees,
        "company_revenue": company_revenue,
        "company_description": company_description,
        "company_addresses": company_addresses,
        
        # Additional
        "emails": emails,
        
        # Detection flag
        "is_intern": is_intern,
        
        # Raw data for debugging
        "raw": raw_job
    }


def normalize_jobs(raw_jobs: list) -> list:
    """
    Normalize a list of raw jobs.
    
    Args:
        raw_jobs: List of raw job dicts from JobSpy
        
    Returns:
        List of normalized job dicts
    """
    normalized = []
    for job in raw_jobs:
        try:
            normalized.append(normalize_job(job))
        except Exception as e:
            logger.error(f"Failed to normalize job: {e}")
            continue
    return normalized
