"""
Base classes and types for the service layer.

Author: El Moujahid Marouane
Version: 1.0
"""

from typing import Optional, Any
from dataclasses import dataclass


@dataclass
class ServiceResult:
    """Standard result wrapper for service operations."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    status_code: int = 200
