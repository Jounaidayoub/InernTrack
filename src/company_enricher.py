#!/usr/bin/env python3
"""
Company Data Enricher (v2.0)

Comprehensive company enrichment using multiple free sources:
- Google Search for official website discovery
- Website scraping (/about, /contact pages)
- LinkedIn company data
- Wikipedia company info
- Email extraction from job descriptions and web pages

No external paid APIs required - completely free!

Architecture follows SOLID principles:
- Single Responsibility: Each source has its own enrichment method
- Open/Closed: Easy to add new enrichment sources
- Dependency Inversion: Uses abstract enrichment result structure

Author: El Moujahid Marouane
Version: 2.0
"""

import re
import requests
from urllib.parse import urljoin, urlparse, quote_plus
from typing import Optional, Dict, Any, List, Set
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from datetime import datetime

try:
    from .logger_setup import get_logger
    from .config import settings
except ImportError:
    from logger_setup import get_logger
    from config import settings

logger = get_logger("company_enricher")

# Request configuration
DEFAULT_TIMEOUT = 10
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class EnrichmentResult:
    """
    Standard result structure for company enrichment.
    
    Follows Interface Segregation - clear contract for all enrichment methods.
    """
    # Core company info
    website: Optional[str] = None
    description: Optional[str] = None
    
    # Social & professional links
    linkedin_url: Optional[str] = None
    glassdoor_url: Optional[str] = None
    twitter_url: Optional[str] = None
    facebook_url: Optional[str] = None
    
    # Contact information
    emails: List[str] = field(default_factory=list)
    contacts: List[Dict[str, str]] = field(default_factory=list)
    phone: Optional[str] = None
    
    # Additional URLs
    careers_url: Optional[str] = None
    about_url: Optional[str] = None
    contact_url: Optional[str] = None
    
    # Company metadata
    industry: Optional[str] = None
    founded: Optional[str] = None
    headquarters: Optional[str] = None
    num_employees: Optional[str] = None
    
    # Enrichment metadata
    sources: List[str] = field(default_factory=list)
    enriched_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def merge(self, other: 'EnrichmentResult') -> 'EnrichmentResult':
        """
        Merge another result into this one (non-destructive).
        Prefers existing values over new ones (first-found wins).
        """
        for attr in ['website', 'description', 'linkedin_url', 'glassdoor_url', 
                     'twitter_url', 'facebook_url', 'phone', 'careers_url',
                     'about_url', 'contact_url', 'industry', 'founded',
                     'headquarters', 'num_employees']:
            if not getattr(self, attr) and getattr(other, attr):
                setattr(self, attr, getattr(other, attr))
        
        # Merge lists (deduplicate)
        existing_emails = set(self.emails)
        for email in other.emails:
            if email not in existing_emails:
                self.emails.append(email)
                existing_emails.add(email)
        
        existing_contact_emails = {c['email'] for c in self.contacts}
        for contact in other.contacts:
            if contact['email'] not in existing_contact_emails:
                self.contacts.append(contact)
                existing_contact_emails.add(contact['email'])
        
        # Merge sources
        for source in other.sources:
            if source not in self.sources:
                self.sources.append(source)
        
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'website': self.website,
            'description': self.description,
            'linkedin_url': self.linkedin_url,
            'glassdoor_url': self.glassdoor_url,
            'twitter_url': self.twitter_url,
            'facebook_url': self.facebook_url,
            'emails': self.emails,
            'contacts': self.contacts,
            'phone': self.phone,
            'careers_url': self.careers_url,
            'about_url': self.about_url,
            'contact_url': self.contact_url,
            'industry': self.industry,
            'founded': self.founded,
            'headquarters': self.headquarters,
            'num_employees': self.num_employees,
            'sources': self.sources,
            'enriched_at': self.enriched_at,
        }
    
    @property
    def is_complete(self) -> bool:
        """Check if we have the essential fields filled."""
        return bool(self.website and self.description and self.linkedin_url)
    
    @property
    def completeness_score(self) -> float:
        """Calculate how complete the enrichment is (0.0 to 1.0)."""
        fields = [
            self.website, self.description, self.linkedin_url,
            len(self.emails) > 0, len(self.contacts) > 0
        ]
        return sum(1 for f in fields if f) / len(fields)


# =============================================================================
# EMAIL EXTRACTION
# =============================================================================

# Comprehensive email regex pattern
EMAIL_PATTERN = re.compile(
    r'''(?xi)
    \b
    (?!.*\.\.)                           # No consecutive dots
    [a-z0-9]                             # Must start with alphanumeric
    [a-z0-9._%+-]{0,63}                  # Local part
    @
    (?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+  # Domain parts
    [a-z]{2,}                            # TLD
    \b
    ''',
    re.IGNORECASE | re.VERBOSE
)

# Domains to exclude (generic, spam traps, etc.)
EXCLUDED_EMAIL_DOMAINS = {
    'example.com', 'example.org', 'test.com', 'localhost',
    'email.com', 'mail.com', 'yourcompany.com', 'company.com',
    'domain.com', 'website.com', 'sentry.io', 'wixpress.com',
    'schema.org', 'w3.org', 'googleapis.com', 'gstatic.com',
}

# Patterns that indicate fake/template emails
FAKE_EMAIL_PATTERNS = [
    r'your.*@', r'email@', r'name@', r'info@example',
    r'sample@', r'test@', r'noreply@', r'no-reply@',
    r'donotreply@', r'mailer-daemon@', r'postmaster@',
]


def extract_emails(text: str) -> List[str]:
    """
    Extract valid email addresses from text.
    
    Filters out:
    - Invalid domains (example.com, etc.)
    - Fake/template emails
    - Duplicate emails
    
    Args:
        text: Raw text to search
        
    Returns:
        List of unique, valid email addresses
    """
    if not text:
        return []
    
    # Find all potential emails
    matches = EMAIL_PATTERN.findall(text)
    
    valid_emails: Set[str] = set()
    
    for email in matches:
        email = email.lower().strip()
        
        # Extract domain
        try:
            domain = email.split('@')[1]
        except IndexError:
            continue
        
        # Skip excluded domains
        if domain in EXCLUDED_EMAIL_DOMAINS:
            continue
        
        # Skip fake/template patterns
        is_fake = any(re.search(pattern, email, re.I) for pattern in FAKE_EMAIL_PATTERNS)
        if is_fake:
            continue
        
        # Skip very long emails (likely not real)
        if len(email) > 100:
            continue
        
        valid_emails.add(email)
    
    return sorted(list(valid_emails))


def extract_emails_with_context(text: str) -> List[Dict[str, str]]:
    """
    Extract emails with surrounding context to identify type.
    
    Returns emails with metadata:
    - email: The email address
    - type: hr, recruiter, general, support, etc.
    - context: Surrounding text snippet
    
    Args:
        text: Raw text to search
        
    Returns:
        List of email dicts with context
    """
    if not text:
        return []
    
    results = []
    
    # Type indicators
    type_patterns = {
        'hr': r'(hr|human\s*resource|people\s*ops)',
        'recruiter': r'(recruit|talent|hiring|career)',
        'support': r'(support|help|customer)',
        'sales': r'(sales|business|partner)',
        'general': r'(info|contact|hello|general)',
    }
    
    for email in extract_emails(text):
        # Find surrounding context (100 chars before and after)
        pattern = re.compile(
            r'.{0,100}' + re.escape(email) + r'.{0,100}',
            re.IGNORECASE | re.DOTALL
        )
        match = pattern.search(text)
        context = match.group(0).strip() if match else ""
        
        # Determine type from email prefix and context
        email_type = 'unknown'
        email_lower = email.lower()
        context_lower = context.lower()
        
        for type_name, pattern in type_patterns.items():
            if re.search(pattern, email_lower) or re.search(pattern, context_lower):
                email_type = type_name
                break
        
        results.append({
            'email': email,
            'type': email_type,
            'context': context[:200]  # Limit context length
        })
    
    return results


# =============================================================================
# WEBSITE SCRAPING
# =============================================================================

def fetch_page(url: str, timeout: int = DEFAULT_TIMEOUT) -> Optional[str]:
    """
    Fetch a web page with error handling.
    
    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
        
    Returns:
        HTML content or None on failure
    """
    try:
        response = requests.get(
            url,
            headers=DEFAULT_HEADERS,
            timeout=timeout,
            allow_redirects=True
        )
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logger.debug(f"Failed to fetch {url}: {e}")
        return None


def extract_text_from_html(html: str) -> str:
    """
    Extract clean text from HTML.
    
    Args:
        html: Raw HTML content
        
    Returns:
        Clean text content
    """
    if not html:
        return ""
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Remove script and style elements
    for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
        tag.decompose()
    
    return soup.get_text(separator=' ', strip=True)


def find_about_page(base_url: str) -> Optional[str]:
    """
    Find the about/company page URL.
    
    Common patterns:
    - /about, /about-us, /company
    - /who-we-are, /our-story
    
    Args:
        base_url: Company website base URL
        
    Returns:
        About page URL or None
    """
    about_paths = [
        '/about', '/about-us', '/about-us/', '/aboutus',
        '/company', '/company/', '/our-company',
        '/who-we-are', '/our-story', '/our-mission',
        '/en/about', '/en/company',
    ]
    
    for path in about_paths:
        url = urljoin(base_url, path)
        html = fetch_page(url)
        if html and len(html) > 1000:  # Minimum content threshold
            return url
    
    return None


def find_contact_page(base_url: str) -> Optional[str]:
    """
    Find the contact page URL.
    
    Args:
        base_url: Company website base URL
        
    Returns:
        Contact page URL or None
    """
    contact_paths = [
        '/contact', '/contact-us', '/contact-us/', '/contactus',
        '/get-in-touch', '/reach-us', '/connect',
        '/en/contact', '/support/contact',
    ]
    
    for path in contact_paths:
        url = urljoin(base_url, path)
        html = fetch_page(url)
        if html and len(html) > 500:
            return url
    
    return None


def find_careers_page(base_url: str) -> Optional[str]:
    """
    Find the careers/jobs page URL.
    
    Args:
        base_url: Company website base URL
        
    Returns:
        Careers page URL or None
    """
    careers_paths = [
        '/careers', '/jobs', '/join-us', '/join',
        '/work-with-us', '/opportunities', '/hiring',
        '/en/careers', '/company/careers',
    ]
    
    for path in careers_paths:
        url = urljoin(base_url, path)
        html = fetch_page(url)
        if html and len(html) > 500:
            return url
    
    return None


# =============================================================================
# COMPANY ENRICHMENT
# =============================================================================

def extract_social_links(html: str, base_url: str) -> Dict[str, str]:
    """
    Extract social media links from HTML.
    
    Args:
        html: HTML content
        base_url: Base URL for resolving relative links
        
    Returns:
        Dict with social platform URLs
    """
    social = {}
    
    if not html:
        return social
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Social media patterns
    patterns = {
        'linkedin': r'linkedin\.com/company/([^/\s"\']+)',
        'twitter': r'twitter\.com/([^/\s"\']+)',
        'facebook': r'facebook\.com/([^/\s"\']+)',
        'instagram': r'instagram\.com/([^/\s"\']+)',
        'github': r'github\.com/([^/\s"\']+)',
        'glassdoor': r'glassdoor\.[a-z]+/[^/]*/([^/\s"\']+)',
    }
    
    html_str = str(soup)
    
    for platform, pattern in patterns.items():
        match = re.search(pattern, html_str, re.IGNORECASE)
        if match:
            if platform == 'linkedin':
                social['linkedin_url'] = f"https://linkedin.com/company/{match.group(1)}"
            elif platform == 'glassdoor':
                social['glassdoor_url'] = match.group(0)
            else:
                social[f'{platform}_url'] = f"https://{platform}.com/{match.group(1)}"
    
    return social


def extract_company_description(html: str) -> Optional[str]:
    """
    Extract company description from about page.
    
    Looks for:
    - Meta description
    - Main content paragraphs
    - Specific about sections
    
    Args:
        html: HTML content of about page
        
    Returns:
        Company description or None
    """
    if not html:
        return None
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Try meta description first
    meta = soup.find('meta', attrs={'name': 'description'})
    if meta and meta.get('content'):
        return meta['content'].strip()
    
    # Try OG description
    og_meta = soup.find('meta', attrs={'property': 'og:description'})
    if og_meta and og_meta.get('content'):
        return og_meta['content'].strip()
    
    # Look for about sections
    about_selectors = [
        'section.about', 'div.about', '#about',
        'section.company', 'div.company-description',
        'article', 'main p',
    ]
    
    for selector in about_selectors:
        element = soup.select_one(selector)
        if element:
            text = element.get_text(separator=' ', strip=True)
            if len(text) > 100:
                return text[:2000]  # Limit length
    
    # Fallback: get first substantial paragraphs
    paragraphs = soup.find_all('p')
    content = []
    for p in paragraphs[:10]:
        text = p.get_text(strip=True)
        if len(text) > 50:
            content.append(text)
        if len(' '.join(content)) > 1000:
            break
    
    if content:
        return ' '.join(content)[:2000]
    
    return None


def normalize_website_url(url: str) -> Optional[str]:
    """
    Normalize and validate a website URL.
    
    Args:
        url: Raw URL string
        
    Returns:
        Normalized URL or None
    """
    if not url:
        return None
    
    url = url.strip()
    
    # Add scheme if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    try:
        parsed = urlparse(url)
        if parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        pass
    
    return None


class CompanyEnricher:
    """
    Enriches company data from multiple free sources.
    
    Main entry point: enrich_company_from_name(name)
    
    Enrichment Pipeline:
    1. resolve_official_website - Find company's official website
    2. enrich_from_website - Scrape website for info
    3. enrich_from_linkedin - Get LinkedIn company data
    4. enrich_from_wikipedia - Get Wikipedia summary
    5. enrich_from_google_search - Fallback for missing data
    
    Features:
    - About page scraping for description
    - Contact page scraping for emails
    - Social media link discovery
    - Careers page detection
    
    Usage:
        enricher = CompanyEnricher()
        result = enricher.enrich_company_from_name("Google")
        print(result.description, result.linkedin_url, result.contacts)
    """
    
    def __init__(self, db_client=None):
        """
        Initialize the enricher.
        
        Args:
            db_client: Optional DatabaseClient for storing results
        """
        self.db = db_client
        self.logger = logger
    
    # =========================================================================
    # MAIN ENTRY POINT
    # =========================================================================
    
    def _is_target_complete(self, result: EnrichmentResult) -> bool:
        """
        Check if target fields are filled: Description, Contacts, LinkedIn, Website.
        
        Returns:
            True if all target fields have data
        """
        return bool(
            result.description and
            result.linkedin_url and
            result.website and
            len(result.contacts) > 0
        )
    
    def enrich(self, company_id: int) -> Dict[str, Any]:
        """
        Simplified enrichment method - takes only company ID.
        
        Uses a lazy evaluation strategy: stops as soon as all target fields are filled.
        Target fields: Description, Contacts, LinkedIn, Website
        
        Enrichment order (stops when complete):
        1. Try website scraping (if URL exists in DB)
        2. Try LinkedIn lookup
        3. Try Wikipedia
        4. Try Google search fallback
        
        Args:
            company_id: Database company ID
            
        Returns:
            Dict with enriched data and metadata
            
        Raises:
            ValueError: If company not found or no database connection
        """
        if not self.db:
            raise ValueError("Database client required for enrich(). Use enrich_company_from_name() for standalone enrichment.")
        
        # Get company from database
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT * FROM companies WHERE id = ?', (company_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Company {company_id} not found")
            company = dict(row)
        
        company_name = company.get('name', '')
        existing_website = company.get('website') or company.get('company_url')
        existing_linkedin = company.get('linkedin_url')
        existing_description = company.get('description')
        
        self.logger.info(f"Starting lazy enrichment for company {company_id}: {company_name}")
        
        result = EnrichmentResult()
        
        # Pre-fill with existing data
        if existing_website:
            result.website = existing_website
        if existing_linkedin:
            result.linkedin_url = existing_linkedin
        if existing_description:
            result.description = existing_description
        
        # Check if already complete
        if self._is_target_complete(result):
            self.logger.info(f"Company {company_id} already has all target fields")
            return self._save_and_return(company_id, result, company)
        
        # Step 1: Website scraping (fastest if URL exists)
        if existing_website:
            self.logger.debug(f"Step 1: Enriching from existing website: {existing_website}")
            website_data = self.enrich_from_website(existing_website)
            result.merge(website_data)
            
            if self._is_target_complete(result):
                self.logger.info("Target complete after website scraping")
                return self._save_and_return(company_id, result, company)
        
        # Step 2: Resolve website if not exists, then scrape
        if not result.website and company_name:
            self.logger.debug(f"Step 2: Resolving website for: {company_name}")
            resolved_website = self.resolve_official_website(company_name)
            if resolved_website:
                result.website = resolved_website
                result.sources.append('website_resolution')
                
                website_data = self.enrich_from_website(resolved_website)
                result.merge(website_data)
                
                if self._is_target_complete(result):
                    self.logger.info("Target complete after website resolution & scraping")
                    return self._save_and_return(company_id, result, company)
        
        # Step 3: LinkedIn lookup
        if not result.linkedin_url and company_name:
            self.logger.debug(f"Step 3: LinkedIn lookup for: {company_name}")
            linkedin_data = self.enrich_from_linkedin(company_name)
            result.merge(linkedin_data)
            
            if self._is_target_complete(result):
                self.logger.info("Target complete after LinkedIn lookup")
                return self._save_and_return(company_id, result, company)
        
        # Step 4: Wikipedia (good for descriptions)
        if not result.description and company_name:
            self.logger.debug(f"Step 4: Wikipedia lookup for: {company_name}")
            wiki_data = self.enrich_from_wikipedia(company_name)
            result.merge(wiki_data)
            
            if self._is_target_complete(result):
                self.logger.info("Target complete after Wikipedia")
                return self._save_and_return(company_id, result, company)
        
        # Step 5: Google search fallback (last resort)
        if not self._is_target_complete(result) and company_name:
            self.logger.debug(f"Step 5: Google search fallback for: {company_name}")
            google_data = self.enrich_from_google_search(company_name)
            result.merge(google_data)
        
        # Final save
        self.logger.info(
            f"Enrichment finished for {company_id}: "
            f"complete={self._is_target_complete(result)}, "
            f"sources={result.sources}"
        )
        return self._save_and_return(company_id, result, company)
    
    def _save_and_return(self, company_id: int, result: EnrichmentResult, company: Dict) -> Dict[str, Any]:
        """
        Save enrichment results to database and return data dict.
        
        Args:
            company_id: Company ID
            result: Enrichment result
            company: Original company data
            
        Returns:
            Dict with enriched data
        """
        # Build updates (only update empty fields)
        updates = {}
        
        if result.description and not company.get('description'):
            updates['description'] = result.description
        if result.website and not company.get('website'):
            updates['website'] = result.website
        if result.linkedin_url and not company.get('linkedin_url'):
            updates['linkedin_url'] = result.linkedin_url
        if result.glassdoor_url and not company.get('glassdoor_url'):
            updates['glassdoor_url'] = result.glassdoor_url
        if result.industry and not company.get('industry'):
            updates['industry'] = result.industry
        if result.num_employees and not company.get('num_employees'):
            updates['num_employees'] = result.num_employees
        
        # Mark as enriched (always set this after enrichment attempt)
        updates['is_enriched'] = True
        updates['enriched_at'] = datetime.utcnow().isoformat()
        updates['updated_at'] = datetime.utcnow().isoformat()
        
        # Apply updates to database
        set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [company_id]
        
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(f"UPDATE companies SET {set_clause} WHERE id = ?", values)
            conn.commit()
        
        self.logger.info(f"Updated company {company_id}: {list(updates.keys())}")
        
        # Save contacts
        for contact_data in result.contacts:
            self._save_contact(company_id, contact_data)
        
        # Return result with metadata
        data = result.to_dict()
        data['company_id'] = company_id
        data['target_complete'] = self._is_target_complete(result)
        data['fields_updated'] = list(updates.keys()) if updates else []
        
        return data
    
    def enrich_company_from_name(self, name: str) -> EnrichmentResult:
        """
        Main enrichment method - enriches company data from just its name.
        
        This is the primary entry point that orchestrates all enrichment sources
        to fill: Description, Contacts, LinkedIn, Website
        
        Pipeline:
        1. Resolve official website from company name
        2. Enrich from website (description, contacts, social links)
        3. Enrich from LinkedIn (description, employee count)
        4. Enrich from Wikipedia (description, industry, founded)
        5. Google search fallback for any missing essential fields
        
        Args:
            name: Company name (e.g., "Google", "Microsoft", "OpenAI")
            
        Returns:
            EnrichmentResult with all discovered data
        """
        self.logger.info(f"Starting enrichment for: {name}")
        result = EnrichmentResult()
        
        # Step 1: Resolve official website
        website = self.resolve_official_website(name)
        if website:
            result.website = website
            result.sources.append('website_resolution')
            self.logger.info(f"Resolved website: {website}")
        
        # Step 2: Enrich from website (if found)
        if result.website:
            website_data = self.enrich_from_website(result.website)
            result.merge(website_data)
        
        # Step 3: Enrich from LinkedIn
        linkedin_data = self.enrich_from_linkedin(name)
        result.merge(linkedin_data)
        
        # Step 4: Enrich from Wikipedia
        wiki_data = self.enrich_from_wikipedia(name)
        result.merge(wiki_data)
        
        # Step 5: Google search fallback for missing essential data
        if not result.is_complete:
            self.logger.info("Enrichment incomplete, using Google fallback")
            google_data = self.enrich_from_google_search(name)
            result.merge(google_data)
        
        self.logger.info(
            f"Enrichment complete for {name}: "
            f"score={result.completeness_score:.0%}, "
            f"sources={result.sources}"
        )
        
        return result
    
    # =========================================================================
    # WEBSITE RESOLUTION
    # =========================================================================
    
    def resolve_official_website(self, company_name: str) -> Optional[str]:
        """
        Resolve a company's official website from its name.
        
        Strategy:
        1. Try common domain patterns (company.com, companyinc.com)
        2. Search Google for "[company] official website"
        3. Search DuckDuckGo as fallback
        
        Args:
            company_name: Company name to resolve
            
        Returns:
            Official website URL or None
        """
        self.logger.debug(f"Resolving website for: {company_name}")
        
        # Clean company name for domain guessing
        clean_name = re.sub(r'[^a-zA-Z0-9]', '', company_name.lower())
        
        # Strategy 1: Try common domain patterns
        domain_patterns = [
            f"https://{clean_name}.com",
            f"https://www.{clean_name}.com",
            f"https://{clean_name}.io",
            f"https://{clean_name}.co",
            f"https://{clean_name}inc.com",
            f"https://{clean_name}hq.com",
            f"https://get{clean_name}.com",
        ]
        
        for url in domain_patterns:
            if self._verify_website(url, company_name):
                self.logger.debug(f"Found via domain pattern: {url}")
                return normalize_website_url(url)
        
        # Strategy 2: Google search
        google_url = self._search_google_for_website(company_name)
        if google_url:
            self.logger.debug(f"Found via Google: {google_url}")
            return google_url
        
        # Strategy 3: DuckDuckGo fallback
        ddg_url = self._search_duckduckgo_for_website(company_name)
        if ddg_url:
            self.logger.debug(f"Found via DuckDuckGo: {ddg_url}")
            return ddg_url
        
        return None
    
    def _verify_website(self, url: str, company_name: str) -> bool:
        """
        Verify that a URL is a valid company website.
        
        Checks:
        - URL is reachable
        - Page content relates to the company
        - Not a parked domain or error page
        """
        try:
            response = requests.get(
                url, 
                headers=DEFAULT_HEADERS, 
                timeout=5,
                allow_redirects=True
            )
            
            if response.status_code != 200:
                return False
            
            # Check if content seems legitimate (not parked)
            content = response.text.lower()
            
            # Parked domain indicators
            parked_indicators = [
                'domain for sale', 'buy this domain', 'parked free',
                'godaddy', 'namecheap parking', 'this domain'
            ]
            if any(ind in content for ind in parked_indicators):
                return False
            
            # Check if company name appears
            name_lower = company_name.lower()
            if name_lower in content or name_lower.replace(' ', '') in content:
                return True
            
            # Check title
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.title.string if soup.title else ''
            if name_lower in title.lower():
                return True
            
            return False
            
        except Exception:
            return False
    
    def _search_google_for_website(self, company_name: str) -> Optional[str]:
        """
        Search Google for a company's official website.
        
        Uses Google's "I'm Feeling Lucky" style approach via HTML parsing.
        """
        try:
            query = quote_plus(f"{company_name} official website")
            url = f"https://www.google.com/search?q={query}&num=5"
            
            response = requests.get(url, headers=DEFAULT_HEADERS, timeout=DEFAULT_TIMEOUT)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find search result links
            for a in soup.find_all('a', href=True):
                href = a['href']
                
                # Google wraps URLs in /url?q=
                if '/url?q=' in href:
                    actual_url = href.split('/url?q=')[1].split('&')[0]
                    
                    # Skip Google, Wikipedia, social media
                    skip_domains = [
                        'google.', 'youtube.', 'wikipedia.', 'facebook.',
                        'twitter.', 'linkedin.', 'instagram.', 'glassdoor.',
                        'indeed.', 'yelp.', 'crunchbase.'
                    ]
                    
                    if not any(d in actual_url.lower() for d in skip_domains):
                        return normalize_website_url(actual_url)
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Google search failed: {e}")
            return None
    
    def _search_duckduckgo_for_website(self, company_name: str) -> Optional[str]:
        """
        Search DuckDuckGo for a company's official website.
        
        DuckDuckGo is more scraping-friendly than Google.
        """
        try:
            query = quote_plus(f"{company_name} official site")
            url = f"https://html.duckduckgo.com/html/?q={query}"
            
            response = requests.get(url, headers=DEFAULT_HEADERS, timeout=DEFAULT_TIMEOUT)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find result links
            for result in soup.find_all('a', class_='result__a'):
                href = result.get('href', '')
                
                # Skip unwanted domains
                skip_domains = [
                    'wikipedia.', 'facebook.', 'twitter.', 'linkedin.',
                    'instagram.', 'glassdoor.', 'indeed.', 'yelp.'
                ]
                
                if href and not any(d in href.lower() for d in skip_domains):
                    return normalize_website_url(href)
            
            return None
            
        except Exception as e:
            self.logger.debug(f"DuckDuckGo search failed: {e}")
            return None
    
    # =========================================================================
    # GOOGLE SEARCH ENRICHMENT
    # =========================================================================
    
    def enrich_from_google_search(self, company_name: str) -> EnrichmentResult:
        """
        Enrich company data from Google search results.
        
        Extracts:
        - Knowledge panel info (description, website)
        - Social media links from search results
        - Company details from snippets
        
        Args:
            company_name: Company name to search
            
        Returns:
            EnrichmentResult with discovered data
        """
        result = EnrichmentResult()
        result.sources.append('google_search')
        
        try:
            query = quote_plus(f"{company_name} company")
            url = f"https://www.google.com/search?q={query}"
            
            response = requests.get(url, headers=DEFAULT_HEADERS, timeout=DEFAULT_TIMEOUT)
            if response.status_code != 200:
                return result
            
            soup = BeautifulSoup(response.text, 'html.parser')
            html_text = response.text.lower()
            
            # Extract LinkedIn URL
            linkedin_match = re.search(
                r'linkedin\.com/company/([a-zA-Z0-9\-_]+)',
                response.text,
                re.IGNORECASE
            )
            if linkedin_match:
                result.linkedin_url = f"https://linkedin.com/company/{linkedin_match.group(1)}"
            
            # Extract other social links
            social_patterns = {
                'twitter_url': r'twitter\.com/([a-zA-Z0-9_]+)',
                'facebook_url': r'facebook\.com/([a-zA-Z0-9.]+)',
            }
            
            for field, pattern in social_patterns.items():
                match = re.search(pattern, response.text, re.IGNORECASE)
                if match:
                    platform = field.replace('_url', '')
                    setattr(result, field, f"https://{platform}.com/{match.group(1)}")
            
            # Try to extract description from knowledge panel or snippets
            # Look for common description patterns
            desc_tags = soup.find_all(['span', 'div'], class_=re.compile(r'description|snippet|about', re.I))
            for tag in desc_tags[:3]:
                text = tag.get_text(strip=True)
                if len(text) > 100 and company_name.lower() in text.lower():
                    result.description = text[:1000]
                    break
            
        except Exception as e:
            self.logger.debug(f"Google enrichment failed: {e}")
        
        return result
    
    # =========================================================================
    # LINKEDIN ENRICHMENT
    # =========================================================================
    
    def enrich_from_linkedin(self, company_name: str) -> EnrichmentResult:
        """
        Enrich company data from LinkedIn.
        
        Extracts:
        - Company description
        - Employee count
        - Industry
        - LinkedIn URL
        
        Note: LinkedIn has aggressive anti-scraping, so this uses
        search engines to find the LinkedIn page and extracts
        available data from snippets.
        
        Args:
            company_name: Company name to search
            
        Returns:
            EnrichmentResult with LinkedIn data
        """
        result = EnrichmentResult()
        result.sources.append('linkedin')
        
        try:
            # Search for LinkedIn company page
            query = quote_plus(f"site:linkedin.com/company {company_name}")
            url = f"https://html.duckduckgo.com/html/?q={query}"
            
            response = requests.get(url, headers=DEFAULT_HEADERS, timeout=DEFAULT_TIMEOUT)
            if response.status_code != 200:
                return result
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find LinkedIn company URL
            for link in soup.find_all('a', class_='result__a'):
                href = link.get('href', '')
                if 'linkedin.com/company/' in href.lower():
                    # Extract clean LinkedIn URL
                    match = re.search(r'linkedin\.com/company/([a-zA-Z0-9\-_]+)', href, re.I)
                    if match:
                        result.linkedin_url = f"https://linkedin.com/company/{match.group(1)}"
                        break
            
            # Extract description from search snippet
            for result_div in soup.find_all('a', class_='result__snippet'):
                snippet = result_div.get_text(strip=True)
                if len(snippet) > 50:
                    # Clean up LinkedIn snippet format
                    # Often contains: "Company Name | LinkedIn · Description..."
                    if '·' in snippet:
                        desc_part = snippet.split('·')[-1].strip()
                        if len(desc_part) > 50:
                            result.description = desc_part[:1000]
                    elif len(snippet) > 100:
                        result.description = snippet[:1000]
                    break
            
            # Try to extract employee count from snippets
            for snippet in soup.find_all(class_='result__snippet'):
                text = snippet.get_text()
                emp_match = re.search(r'(\d[\d,]*)\s*(?:employees|staff|people)', text, re.I)
                if emp_match:
                    result.num_employees = emp_match.group(1).replace(',', '')
                    break
            
        except Exception as e:
            self.logger.debug(f"LinkedIn enrichment failed: {e}")
        
        return result
    
    # =========================================================================
    # WIKIPEDIA ENRICHMENT
    # =========================================================================
    
    def enrich_from_wikipedia(self, company_name: str) -> EnrichmentResult:
        """
        Enrich company data from Wikipedia.
        
        Uses Wikipedia's API for reliable data extraction.
        
        Extracts:
        - Company description (first paragraph)
        - Industry
        - Founded date
        - Headquarters location
        - Website (from infobox)
        
        Args:
            company_name: Company name to search
            
        Returns:
            EnrichmentResult with Wikipedia data
        """
        result = EnrichmentResult()
        result.sources.append('wikipedia')
        
        try:
            # Use Wikipedia API for search
            search_url = (
                f"https://en.wikipedia.org/w/api.php?"
                f"action=query&list=search&srsearch={quote_plus(company_name + ' company')}"
                f"&format=json&srlimit=3"
            )
            
            response = requests.get(search_url, headers=DEFAULT_HEADERS, timeout=DEFAULT_TIMEOUT)
            if response.status_code != 200:
                return result
            
            data = response.json()
            search_results = data.get('query', {}).get('search', [])
            
            if not search_results:
                return result
            
            # Find best matching result
            best_title = None
            company_lower = company_name.lower()
            
            for sr in search_results:
                title = sr.get('title', '').lower()
                if company_lower in title or title in company_lower:
                    best_title = sr.get('title')
                    break
            
            if not best_title:
                best_title = search_results[0].get('title')
            
            # Fetch the page content
            content_url = (
                f"https://en.wikipedia.org/w/api.php?"
                f"action=query&titles={quote_plus(best_title)}"
                f"&prop=extracts|pageprops&exintro=1&explaintext=1&format=json"
            )
            
            response = requests.get(content_url, headers=DEFAULT_HEADERS, timeout=DEFAULT_TIMEOUT)
            if response.status_code != 200:
                return result
            
            data = response.json()
            pages = data.get('query', {}).get('pages', {})
            
            for page_id, page_data in pages.items():
                if page_id == '-1':
                    continue
                
                # Extract description from intro
                extract = page_data.get('extract', '')
                if extract and len(extract) > 100:
                    # Take first 2-3 sentences
                    sentences = extract.split('. ')[:3]
                    result.description = '. '.join(sentences) + '.'
            
            # Also fetch HTML for infobox parsing
            html_url = (
                f"https://en.wikipedia.org/wiki/{quote_plus(best_title)}"
            )
            
            html_response = requests.get(html_url, headers=DEFAULT_HEADERS, timeout=DEFAULT_TIMEOUT)
            if html_response.status_code == 200:
                soup = BeautifulSoup(html_response.text, 'html.parser')
                
                # Parse infobox for structured data
                infobox = soup.find('table', class_='infobox')
                if infobox:
                    self._parse_wikipedia_infobox(infobox, result)
            
        except Exception as e:
            self.logger.debug(f"Wikipedia enrichment failed: {e}")
        
        return result
    
    def _parse_wikipedia_infobox(self, infobox, result: EnrichmentResult):
        """Parse Wikipedia infobox for company data."""
        for row in infobox.find_all('tr'):
            header = row.find('th')
            data = row.find('td')
            
            if not header or not data:
                continue
            
            header_text = header.get_text(strip=True).lower()
            data_text = data.get_text(strip=True)
            
            # Industry
            if 'industry' in header_text:
                result.industry = data_text[:200]
            
            # Founded
            elif 'founded' in header_text or 'established' in header_text:
                # Extract year
                year_match = re.search(r'\b(19|20)\d{2}\b', data_text)
                if year_match:
                    result.founded = year_match.group(0)
            
            # Headquarters
            elif 'headquarters' in header_text or 'location' in header_text:
                result.headquarters = data_text[:200]
            
            # Employees
            elif 'employee' in header_text:
                emp_match = re.search(r'[\d,]+', data_text)
                if emp_match:
                    result.num_employees = emp_match.group(0).replace(',', '')
            
            # Website
            elif 'website' in header_text:
                link = data.find('a', href=True)
                if link and 'href' in link.attrs:
                    href = link['href']
                    if href.startswith('http'):
                        result.website = normalize_website_url(href)
    
    # =========================================================================
    # WEBSITE ENRICHMENT (Original functionality)
    # =========================================================================
    
    def enrich_from_website(self, website_url: str) -> EnrichmentResult:
        """
        Enrich company data from their website.
        
        Scrapes:
        - Homepage for social links
        - About page for description
        - Contact page for emails
        - Careers page URL
        
        Args:
            website_url: Company website URL
            
        Returns:
            EnrichmentResult with website data
        """
        result = EnrichmentResult()
        result.sources.append('website')
        
        # Normalize URL
        base_url = normalize_website_url(website_url)
        if not base_url:
            self.logger.warning(f"Invalid website URL: {website_url}")
            return result
        
        result.website = base_url
        self.logger.info(f"Enriching company from: {base_url}")
        
        # Fetch homepage
        homepage_html = fetch_page(base_url)
        if homepage_html:
            # Extract social links from homepage
            social = extract_social_links(homepage_html, base_url)
            if social.get('linkedin_url'):
                result.linkedin_url = social['linkedin_url']
            if social.get('glassdoor_url'):
                result.glassdoor_url = social['glassdoor_url']
            if social.get('twitter_url'):
                result.twitter_url = social['twitter_url']
            if social.get('facebook_url'):
                result.facebook_url = social['facebook_url']
            
            # Extract emails from homepage
            homepage_emails = extract_emails_with_context(homepage_html)
            result.contacts.extend(homepage_emails)
        
        # Find and scrape about page
        about_url = find_about_page(base_url)
        if about_url:
            result.about_url = about_url
            about_html = fetch_page(about_url)
            if about_html:
                desc = extract_company_description(about_html)
                if desc:
                    result.description = desc
                
                # More social links might be on about page
                social = extract_social_links(about_html, base_url)
                if not result.linkedin_url and social.get('linkedin_url'):
                    result.linkedin_url = social['linkedin_url']
        
        # Find and scrape contact page
        contact_url = find_contact_page(base_url)
        if contact_url:
            result.contact_url = contact_url
            contact_html = fetch_page(contact_url)
            if contact_html:
                contact_emails = extract_emails_with_context(contact_html)
                result.contacts.extend(contact_emails)
                
                # Try to extract phone
                phone_match = re.search(
                    r'[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}',
                    contact_html
                )
                if phone_match:
                    result.phone = phone_match.group(0)
        
        # Find careers page
        careers_url = find_careers_page(base_url)
        if careers_url:
            result.careers_url = careers_url
        
        # Deduplicate contacts
        seen_emails = set()
        unique_contacts = []
        for contact in result.contacts:
            if contact['email'] not in seen_emails:
                seen_emails.add(contact['email'])
                unique_contacts.append(contact)
        result.contacts = unique_contacts
        result.emails = list(seen_emails)
        
        self.logger.info(f"Website enrichment complete: {len(result.emails)} emails found")
        return result
    
    def enrich_from_job_description(self, description: str, company_name: str = None) -> EnrichmentResult:
        """
        Extract contact information from job description.
        
        Args:
            description: Job description text
            company_name: Optional company name for filtering
            
        Returns:
            EnrichmentResult with extracted contacts
        """
        result = EnrichmentResult()
        result.sources.append('job_description')
        
        if not description:
            return result
        
        # Extract emails with context
        contacts = extract_emails_with_context(description)
        
        # Filter by company domain if we have the name
        if company_name:
            company_domain_hint = company_name.lower().replace(' ', '').replace(',', '')[:10]
            
            # Prioritize emails that might match company
            prioritized = []
            others = []
            
            for contact in contacts:
                domain = contact['email'].split('@')[1].split('.')[0].lower()
                if company_domain_hint in domain or domain in company_domain_hint:
                    contact['priority'] = 'high'
                    prioritized.append(contact)
                else:
                    contact['priority'] = 'low'
                    others.append(contact)
            
            contacts = prioritized + others
        
        result.contacts = contacts
        result.emails = [c['email'] for c in contacts]
        
        return result
    
    def enrich_company(self, company_id: int, website_url: str = None) -> Dict[str, Any]:
        """
        Full enrichment for a company, optionally saving to database.
        
        Args:
            company_id: Database company ID
            website_url: Company website (if known)
            
        Returns:
            Enriched company data dict
        """
        if not self.db:
            raise ValueError("Database client required for company enrichment")
        
        # Get current company data
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT * FROM companies WHERE id = ?', (company_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Company {company_id} not found")
            company = dict(row)
        
        # Use the main enrichment method
        company_name = company.get('name', '')
        
        # Try website-based enrichment first if URL provided
        if website_url or company.get('website') or company.get('company_url'):
            url = website_url or company.get('website') or company.get('company_url')
            enriched = self.enrich_from_website(url)
        else:
            # Use name-based enrichment
            enriched = self.enrich_company_from_name(company_name)
        
        # Update company in database
        updates = {}
        if enriched.description and not company.get('description'):
            updates['description'] = enriched.description
        if enriched.linkedin_url and not company.get('linkedin_url'):
            updates['linkedin_url'] = enriched.linkedin_url
        if enriched.glassdoor_url and not company.get('glassdoor_url'):
            updates['glassdoor_url'] = enriched.glassdoor_url
        if enriched.website and not company.get('website'):
            updates['website'] = enriched.website
        if enriched.industry and not company.get('industry'):
            updates['industry'] = enriched.industry
        if enriched.num_employees and not company.get('num_employees'):
            updates['num_employees'] = enriched.num_employees
        
        if updates:
            updates['updated_at'] = datetime.utcnow().isoformat()
            set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
            values = list(updates.values()) + [company_id]
            
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(f"UPDATE companies SET {set_clause} WHERE id = ?", values)
                conn.commit()
            
            self.logger.info(f"Updated company {company_id} with: {list(updates.keys())}")
        
        # Save contacts
        for contact_data in enriched.contacts:
            self._save_contact(company_id, contact_data)
        
        return enriched.to_dict()
    
    def enrich_company_by_name(self, company_id: int, company_name: str) -> Dict[str, Any]:
        """
        Enrich a company in the database using just its name.
        
        This is a convenience method that combines enrich_company_from_name
        with database persistence.
        
        Args:
            company_id: Database company ID to update
            company_name: Company name to search for
            
        Returns:
            Enriched data dict
        """
        if not self.db:
            raise ValueError("Database client required for company enrichment")
        
        # Run enrichment
        enriched = self.enrich_company_from_name(company_name)
        
        # Get current company data
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT * FROM companies WHERE id = ?', (company_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Company {company_id} not found")
            company = dict(row)
        
        # Build updates (only update empty fields)
        updates = {}
        field_mapping = {
            'description': 'description',
            'website': 'website',
            'linkedin_url': 'linkedin_url',
            'glassdoor_url': 'glassdoor_url',
            'industry': 'industry',
            'num_employees': 'num_employees',
        }
        
        for enriched_field, db_field in field_mapping.items():
            value = getattr(enriched, enriched_field, None)
            if value and not company.get(db_field):
                updates[db_field] = value
        
        # Apply updates
        if updates:
            updates['updated_at'] = datetime.utcnow().isoformat()
            set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
            values = list(updates.values()) + [company_id]
            
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(f"UPDATE companies SET {set_clause} WHERE id = ?", values)
                conn.commit()
            
            self.logger.info(f"Updated company {company_id} via name enrichment: {list(updates.keys())}")
        
        # Save contacts
        for contact_data in enriched.contacts:
            self._save_contact(company_id, contact_data)
        
        return enriched.to_dict()
    
    def _save_contact(self, company_id: int, contact_data: Dict[str, str]) -> Optional[int]:
        """
        Save a contact to the database.
        
        Args:
            company_id: Company ID
            contact_data: Contact dict with email, type, context
            
        Returns:
            Contact ID or None
        """
        if not self.db:
            return None
        
        email = contact_data.get('email')
        if not email:
            return None
        
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                
                # Check if contact exists
                cur.execute(
                    'SELECT id FROM contacts WHERE company_id = ? AND email = ?',
                    (company_id, email)
                )
                existing = cur.fetchone()
                
                if existing:
                    return existing[0]
                
                # Insert new contact
                cur.execute('''
                    INSERT INTO contacts (company_id, name, email, position, notes)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    company_id,
                    email.split('@')[0].replace('.', ' ').title(),  # Generate name from email
                    email,
                    contact_data.get('type', 'unknown'),
                    contact_data.get('context', '')[:500]
                ))
                conn.commit()
                
                self.logger.debug(f"Saved contact: {email}")
                return cur.lastrowid
                
        except Exception as e:
            self.logger.error(f"Failed to save contact {email}: {e}")
            return None


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def enrich_company_quick(website_url: str) -> Dict[str, Any]:
    """
    Quick enrichment from website without database.
    
    Args:
        website_url: Company website URL
        
    Returns:
        Enriched data dict
    """
    enricher = CompanyEnricher()
    result = enricher.enrich_from_website(website_url)
    return result.to_dict()


def enrich_company_by_name_quick(company_name: str) -> Dict[str, Any]:
    """
    Quick enrichment from company name without database.
    
    This is the recommended way to enrich a company when you only have the name.
    
    Args:
        company_name: Company name (e.g., "Google", "Microsoft")
        
    Returns:
        Enriched data dict
    """
    enricher = CompanyEnricher()
    result = enricher.enrich_company_from_name(company_name)
    return result.to_dict()


def extract_contacts_from_text(text: str) -> List[Dict[str, str]]:
    """
    Extract contacts from any text.
    
    Args:
        text: Text to search
        
    Returns:
        List of contact dicts
    """
    return extract_emails_with_context(text)


if __name__ == "__main__":
    # Test the enricher
    import sys
    
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        
        # Check if it's a URL or company name
        if arg.startswith('http') or '.' in arg and '/' in arg:
            print(f"Enriching from URL: {arg}")
            result = enrich_company_quick(arg)
        else:
            print(f"Enriching from name: {arg}")
            result = enrich_company_by_name_quick(arg)
        
        print(f"\n{'='*50}")
        print(f"Website: {result.get('website')}")
        print(f"LinkedIn: {result.get('linkedin_url')}")
        print(f"Description: {(result.get('description') or '')[:200]}...")
        print(f"Industry: {result.get('industry')}")
        print(f"Founded: {result.get('founded')}")
        print(f"Headquarters: {result.get('headquarters')}")
        print(f"Employees: {result.get('num_employees')}")
        print(f"\nSources: {result.get('sources')}")
        print(f"Completeness: {len([v for v in result.values() if v])} fields filled")
        
        print(f"\nEmails found: {len(result.get('emails', []))}")
        for contact in result.get('contacts', [])[:5]:
            print(f"  - {contact['email']} ({contact.get('type', 'unknown')})")
    else:
        print("Usage:")
        print("  python company_enricher.py <website_url>")
        print("  python company_enricher.py <company_name>")
        print("\nExamples:")
        print("  python company_enricher.py https://google.com")
        print("  python company_enricher.py 'Google'")
        print("  python company_enricher.py 'Microsoft Corporation'")
