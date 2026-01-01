"""
Base Controller

Provides base class for all route controllers.

Author: El Moujahid Marouane
Version: 1.0
"""

from abc import ABC, abstractmethod
from flask import Blueprint, jsonify

from src.services import ServiceResult


class BaseController(ABC):
    """Base class for route controllers."""
    
    def __init__(self, blueprint: Blueprint):
        self.bp = blueprint
    
    @abstractmethod
    def register_routes(self):
        """Register routes on the blueprint. Must be implemented by subclasses."""
        pass
    
    @staticmethod
    def service_to_response(result: ServiceResult):
        """Convert ServiceResult to Flask JSON response."""
        if result.success:
            return jsonify(result.data), result.status_code
        else:
            response = {'error': result.error}
            if result.data:
                response.update(result.data)
            return jsonify(response), result.status_code
    
    @staticmethod
    def json_response(data, status_code: int = 200):
        """Create a JSON response."""
        return jsonify(data), status_code
    
    @staticmethod
    def error_response(error: str, status_code: int = 400):
        """Create an error JSON response."""
        return jsonify({'error': error}), status_code
