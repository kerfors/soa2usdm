"""
Pipeline Step Base Class

All pipeline steps inherit from this base.
"""

from abc import ABC, abstractmethod
from typing import Any

from .errors import Errors
from .analytics import AnalyticsBase


class PipelineStepBase(ABC):
    """Base class for pipeline steps.
    
    Each step:
    - Receives shared errors and analytics objects
    - Implements execute() to perform its work
    - Adds results to the data dict under its step name
    - Records errors via self._errors.add()
    - Records metrics via self._analytics
    """
    
    # Override in subclass - used as key in result dict
    step_name: str = "base"
    
    def __init__(self, errors: Errors, analytics: AnalyticsBase):
        self._errors = errors
        self._analytics = analytics
    
    @abstractmethod
    def execute(self, data: dict) -> dict:
        """Execute this pipeline step.
        
        Args:
            data: Accumulated results from previous steps.
                  Always contains 'source' with input parameters.
        
        Returns:
            Results dict for this step (will be stored under step_name)
        """
        pass
    
    def _log_error(self, message: str, context: dict = None) -> None:
        """Convenience method to log error with step name."""
        self._errors.add(self.step_name, message, context)
