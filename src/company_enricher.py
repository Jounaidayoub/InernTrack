#!/usr/bin/env python3
"""
Company Data Enricher (v1.0)

Free company enrichment using:
- Website scraping (/about, /contact pages)
- Email extraction from job descriptions and web pages
- Social media URL discovery

No external APIs required - completely free!

Author: El Moujahid Marouane
Version: 1.0
"""

import re
import requests
from urllib.parse import urljoin, urlparse
from typing import Optional, Dict, Any, List, Set
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
    Enriches company data from website scraping.
    
    Features:
    - About page scraping for description
    - Contact page scraping for emails
    - Social media link discovery
    - Careers page detection
    
    Usage:
        enricher = CompanyEnricher()
        data = enricher.enrich("https://company.com")
    """
    
    def __init__(self, db_client=None):
        """
        Initialize the enricher.
        
        Args:
            db_client: Optional DatabaseClient for storing results
        """
        self.db = db_client
        self.logger = logger
    
    def enrich_from_website(self, website_url: str) -> Dict[str, Any]:
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
            Dict with enriched company data
        """
        result = {
            'website': None,
            'description': None,
            'emails': [],
            'contacts': [],
            'linkedin_url': None,
            'glassdoor_url': None,
            'careers_url': None,
            'about_url': None,
            'contact_url': None,
            'enriched_at': datetime.utcnow().isoformat(),
            'enrichment_source': 'website',
        }
        
        # Normalize URL
        base_url = normalize_website_url(website_url)
        if not base_url:
            self.logger.warning(f"Invalid website URL: {website_url}")
            return result
        
        result['website'] = base_url
        self.logger.info(f"Enriching company from: {base_url}")
        
        # Fetch homepage
        homepage_html = fetch_page(base_url)
        if homepage_html:
            # Extract social links from homepage
            social = extract_social_links(homepage_html, base_url)
            result.update(social)
            
            # Extract emails from homepage
            homepage_emails = extract_emails_with_context(homepage_html)
            result['contacts'].extend(homepage_emails)
        
        # Find and scrape about page
        about_url = find_about_page(base_url)
        if about_url:
            result['about_url'] = about_url
            about_html = fetch_page(about_url)
            if about_html:
                desc = extract_company_description(about_html)
                if desc:
                    result['description'] = desc
                
                # More social links might be on about page
                social = extract_social_links(about_html, base_url)
                for key, value in social.items():
                    if not result.get(key):
                        result[key] = value
        
        # Find and scrape contact page
        contact_url = find_contact_page(base_url)
        if contact_url:
            result['contact_url'] = contact_url
            contact_html = fetch_page(contact_url)
            if contact_html:
                contact_emails = extract_emails_with_context(contact_html)
                result['contacts'].extend(contact_emails)
        
        # Find careers page
        careers_url = find_careers_page(base_url)
        if careers_url:
            result['careers_url'] = careers_url
        
        # Deduplicate emails
        seen_emails = set()
        unique_contacts = []
        for contact in result['contacts']:
            if contact['email'] not in seen_emails:
                seen_emails.add(contact['email'])
                unique_contacts.append(contact)
        result['contacts'] = unique_contacts
        result['emails'] = list(seen_emails)
        
        self.logger.info(f"Enrichment complete: {len(result['emails'])} emails found")
        return result
    
    def enrich_from_job_description(self, description: str, company_name: str = None) -> Dict[str, Any]:
        """
        Extract contact information from job description.
        
        Args:
            description: Job description text
            company_name: Optional company name for filtering
            
        Returns:
            Dict with extracted contacts
        """
        result = {
            'emails': [],
            'contacts': [],
            'enrichment_source': 'job_description',
        }
        
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
        
        result['contacts'] = contacts
        result['emails'] = [c['email'] for c in contacts]
        
        return result
    
    def enrich_company(self, company_id: int, website_url: str = None) -> Dict[str, Any]:
        """
        Full enrichment for a company, optionally saving to database.
        
        Args:
            company_id: Database company ID
            website_url: Company website (if known)
            
        Returns:
            Enriched company data
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
        
        # Use provided URL or existing
        url = website_url or company.get('website') or company.get('company_url')
        
        if not url:
            self.logger.warning(f"No website URL for company {company_id}")
            return {'error': 'No website URL available'}
        
        # Enrich from website
        enriched = self.enrich_from_website(url)
        
        # Update company in database
        updates = {}
        if enriched.get('description') and not company.get('description'):
            updates['description'] = enriched['description']
        if enriched.get('linkedin_url') and not company.get('linkedin_url'):
            updates['linkedin_url'] = enriched['linkedin_url']
        if enriched.get('glassdoor_url') and not company.get('glassdoor_url'):
            updates['glassdoor_url'] = enriched['glassdoor_url']
        if enriched.get('website') and not company.get('website'):
            updates['website'] = enriched['website']
        
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
        for contact_data in enriched.get('contacts', []):
            self._save_contact(company_id, contact_data)
        
        return enriched
    
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
    Quick enrichment without database.
    
    Args:
        website_url: Company website URL
        
    Returns:
        Enriched data dict
    """
    enricher = CompanyEnricher()
    return enricher.enrich_from_website(website_url)


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
        url = sys.argv[1]
        print(f"Enriching: {url}")
        result = enrich_company_quick(url)
        
        print(f"\nWebsite: {result.get('website')}")
        print(f"Description: {result.get('description', '')[:200]}...")
        print(f"LinkedIn: {result.get('linkedin_url')}")
        print(f"Glassdoor: {result.get('glassdoor_url')}")
        print(f"Careers: {result.get('careers_url')}")
        print(f"\nEmails found: {len(result.get('emails', []))}")
        for contact in result.get('contacts', []):
            print(f"  - {contact['email']} ({contact['type']})")
    else:
        print("Usage: python company_enricher.py <website_url>")
