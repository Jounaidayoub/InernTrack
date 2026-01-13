"""
Web Routes Package

OOP-based Flask routes for internship tracking web UI.
Each route group is in its own module with a controller class.

Author: El Moujahid Marouane
Version: 4.0
"""

from flask import Blueprint

from .base import BaseController
from .pages import PagesController
from .internships import InternshipsController
from .companies import CompaniesController
from .contacts import ContactsController
from .database import DatabaseController
from .export import ExportController
from .settings import SettingsController
from .profile import ProfileController
from .resume import ResumeController


def create_blueprint() -> Blueprint:
    """Create and configure the main blueprint with all routes."""
    bp = Blueprint('main', __name__)
    
    # Register all controllers
    PagesController(bp).register_routes()
    InternshipsController(bp).register_routes()
    CompaniesController(bp).register_routes()
    ContactsController(bp).register_routes()
    DatabaseController(bp).register_routes()
    ExportController(bp).register_routes()
    SettingsController(bp).register_routes()
    ProfileController(bp).register_routes()
    ResumeController(bp).register_routes()
    
    return bp


# Create the blueprint instance
bp = create_blueprint()

__all__ = [
    'bp',
    'create_blueprint',
    'BaseController',
    'PagesController',
    'InternshipsController',
    'CompaniesController',
    'ContactsController',
    'DatabaseController',
    'ExportController',
    'SettingsController',
    'ProfileController',
    'ResumeController',
]
