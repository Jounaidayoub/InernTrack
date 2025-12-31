# Contributing to InternTrack

Thank you for your interest in contributing to InternTrack. This document provides guidelines and instructions for contributing.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Git
- A GitHub account

### Setting Up the Development Environment

1. Fork the repository on GitHub

2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/InternTrack.git
   cd InternTrack
   ```

3. Add the upstream repository:
   ```bash
   git remote add upstream https://github.com/marouaneMJH/InternTrack.git
   ```


4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Copy the environment file:
   ```bash
   cp .env.example .env
   ```

## Development Workflow

### Creating a Branch

Create a new branch for your work:

```bash
git checkout -b feat/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions or updates

### Making Changes

1. Make your changes in the appropriate files
2. Follow the existing code style and conventions
3. Add or update tests if applicable
4. Update documentation if needed

### Code Style

- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and small
- Use type hints where appropriate

Example:

```python
def fetch_internships(search_term: str, location: str) -> list[dict]:
    """
    Fetch internship listings from configured job boards.
    
    Args:
        search_term: Job title or keywords to search
        location: Geographic location for the search
        
    Returns:
        List of internship dictionaries with job details
    """
    pass
```

### Commit Messages

Write clear and descriptive commit messages:

```
type: short description

Longer description if needed. Explain what and why,
not how (the code shows how).

Fixes #123
```

Types:
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `style` - Formatting, no code change
- `refactor` - Code restructuring
- `test` - Adding tests
- `chore` - Maintenance tasks

### Testing - NOT SUPPORTED FOR THE MOMENT

Run tests before submitting:

```bash
make test
# or
python -m pytest
```

Ensure your changes do not break existing functionality.

### Submitting a Pull Request

1. Push your branch to your fork:
   ```bash
   git push origin feat/your-feature-name
   ```

2. Go to GitHub and create a Pull Request

3. Fill out the PR template:
   - Describe what changes you made
   - Reference any related issues
   - List any breaking changes
   - Include screenshots for UI changes

4. Wait for review and address any feedback

## Project Structure

Understanding the codebase:

```
src/                     # Core application logic
├── main.py              # Pipeline entry point
├── config.py            # Configuration management
├── jobspy_client.py     # Job scraping
├── database_client.py   # Database operations
├── normalizer.py        # Data transformation
└── logger_setup.py      # Logging setup

web/                     # Web interface
├── app.py               # Flask application
├── routes.py            # Route handlers
├── templates/           # HTML templates
└── static/              # CSS and JavaScript

data/                    # Database files
scripts/                 # Utility scripts
```

## Areas for Contribution

### Good First Issues

- Documentation improvements
- Bug fixes
- Test coverage
- Code cleanup

### Feature Development

- Application tracking improvements
- New job board integrations
- Email automation
- Document generation
- Analytics dashboard

### Documentation

- README updates
- Code comments
- API documentation
- User guides

## Reporting Issues

When reporting bugs:

1. Check existing issues first
2. Use a clear and descriptive title
3. Describe steps to reproduce
4. Include expected vs actual behavior
5. Add relevant logs or screenshots
6. Specify your environment (OS, Python version)

## Questions

If you have questions:

1. Check the README and existing documentation
2. Search existing issues
3. Open a new issue with the question label

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on the code, not the person
- Help others learn and grow

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT License).
