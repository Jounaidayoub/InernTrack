# InternTrack

An internship tracking and automation platform that helps job seekers find, apply to, and manage internship opportunities.

## Overview

InternTrack is a comprehensive internship management system that automates the internship search process from discovery to application. The application scrapes internship listings from multiple job boards, stores them in a local database, and provides a web interface for browsing and managing opportunities.

### Current Features

- Multi-site job scraping (LinkedIn, Indeed) using JobSpy
- Local SQLite database for storing companies, internships, and applications
- Web dashboard for browsing internships and companies
- Advanced filtering and search capabilities
- CSV export functionality
- Database status monitoring

### Planned Features

- Automated document generation (cover letters, resumes tailored per position)
- Email automation for sending applications
- Application status tracking and pipeline management
- Offer tracking and comparison
- Interview scheduling integration
- Analytics and reporting on application success rates

## Architecture

The application follows an MVC pattern with separation between the scraping pipeline and the web interface.

```
internship-sync/
├── src/                     # Core scraping and data pipeline
│   ├── main.py              # Pipeline orchestration
│   ├── config.py            # Configuration management
│   ├── jobspy_client.py     # Job scraping client
│   ├── database_client.py   # SQLite database operations
│   ├── normalizer.py        # Data transformation
│   └── logger_setup.py      # Logging configuration
├── web/                     # Flask web application
│   ├── app.py               # Flask app initialization
│   ├── routes.py            # API and page routes
│   ├── templates/           # Jinja2 HTML templates
│   └── static/              # CSS and JavaScript assets
├── data/                    # Database and CSV files
├── scripts/                 # Utility scripts
└── Makefile                 # Build and run commands
```

## Installation

### Prerequisites

- Python 3.10 or higher
- pip package manager

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/marouaneMJH/InternTrack.git
   cd InternTrack
   ```

2. Create and activate a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # or
   venv\Scripts\activate     # Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

## Configuration

All configuration is managed through environment variables in the `.env` file.

### Search Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| SEARCH_TERMS | Comma-separated job titles to search | `Software Engineer Intern,Data Science Intern` |
| LOCATIONS | Comma-separated locations | `Casablanca,Rabat,Remote` |
| RESULTS_WANTED | Max results per search combination | `100` |
| HOURS_OLD | Filter jobs posted within N hours | `72` |

### Scraping Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| SITE_NAMES | Job boards to scrape | `linkedin,indeed` |
| JOB_TYPE | Type of position | `internship` |
| EXPERIENCE_LEVELS | Required experience | `internship,entry_level` |
| COUNTRY_INDEED | Country for Indeed searches | `Morocco` |

### Application Behavior

| Variable | Description | Default |
|----------|-------------|---------|
| DRY_RUN | Test mode without DB writes | `false` |
| LOG_LEVEL | Logging verbosity | `INFO` |
| DATABASE_PATH | SQLite database location | `data/internship_sync_new.db` |

### Supported Job Sites

- LinkedIn
- Indeed

### Supported Countries

The following countries are supported for job searches:

Argentina, Australia, Austria, Bahrain, Bangladesh, Belgium, Brazil, Bulgaria, Canada, Chile, China, Colombia, Costa Rica, Croatia, Cyprus, Czech Republic, Denmark, Ecuador, Egypt, Estonia, Finland, France, Germany, Greece, Hong Kong, Hungary, India, Indonesia, Ireland, Italy, Japan, Kuwait, Latvia, Lithuania, Luxembourg, Malaysia, Malta, Mexico, Morocco, Netherlands, New Zealand, Nigeria, Norway, Oman, Pakistan, Panama, Peru, Philippines, Poland, Portugal, Qatar, Romania, Saudi Arabia, Singapore, Slovakia, Slovenia, South Africa, South Korea, Spain, Sweden, Switzerland, Taiwan, Thailand, Turkey, Ukraine, United Arab Emirates, United Kingdom, United States, Uruguay, Venezuela, Vietnam, Worldwide, Remote

## Usage

### Running the Scraper

Fetch new internship listings:

```bash
make dev
# or
python -m src.main
```

### Running the Web Interface

Start the Flask development server:

```bash
make web
# or
python -m web.app
```

Access the dashboard at http://localhost:5000

### Available Make Commands

| Command | Description |
|---------|-------------|
| `make dev` | Run the scraping pipeline |
| `make web` | Start the web server |
| `make test` | Run tests ! NOT SUPPORTED |
| `make clean` | Remove generated files |

## Database Schema

The application uses SQLite with the following tables:

### companies
Stores company information including name, website, industry, and country.

### internships
Stores job listings with title, description, location, URL, status, and remote flag.

### applications
Tracks application status, dates, and associated documents.

### contacts
Stores recruiter and company contact information.

### documents
Manages resumes, cover letters, and other application documents.

### offers_received
Tracks received offers with salary, benefits, and response deadlines.

## Web Interface

The web dashboard provides:

- Internships list with search and filtering
- Companies directory
- Database status and statistics
- CSV export for external analysis

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/internships` | GET | List internships with pagination |
| `/api/internship/<id>` | GET | Get internship details |
| `/api/companies` | GET | List companies with pagination |
| `/api/company/<id>` | GET | Get company details |
| `/api/db_status` | GET | Database statistics |
| `/export/internships.csv` | GET | Export internships to CSV |


## Troubleshooting

### Common Issues

**JobSpy scraping fails**
- Ensure your IP is not rate-limited by job sites
- Try reducing RESULTS_WANTED
- Check that SITE_NAMES only includes supported sites for your region

**Database errors**
- Verify DATABASE_PATH directory exists
- Check file permissions on the data directory

**Web interface not loading**
- Ensure Flask is installed: `pip install flask`
- Check for port conflicts on 5000

### Logging

Enable debug logging for detailed output:

```bash
LOG_LEVEL=DEBUG python -m src.main
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License