"""
Error Collection

Accumulates errors across pipeline steps for reporting.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Error:
    """Single error record."""
    step: str
    message: str
    context: dict = field(default_factory=dict)


class Errors:
    """Collects errors across pipeline execution."""
    
    def __init__(self):
        self._errors: list[Error] = []
    
    def add(self, step: str, message: str, context: dict = None) -> None:
        """Add an error.
        
        Args:
            step: Pipeline step name where error occurred
            message: Error description
            context: Optional dict with additional context (file, row, etc.)
        """
        self._errors.append(Error(
            step=step,
            message=message,
            context=context or {}
        ))
    
    def has_errors(self) -> bool:
        """Return True if any errors have been recorded."""
        return len(self._errors) > 0
    
    def count(self) -> int:
        """Return number of errors."""
        return len(self._errors)
    
    def for_step(self, step: str) -> list[Error]:
        """Return errors for a specific step."""
        return [e for e in self._errors if e.step == step]
    
    @property
    def all(self) -> list[Error]:
        """Return all errors."""
        return self._errors
    
    def summary(self) -> dict[str, int]:
        """Return error counts by step."""
        counts: dict[str, int] = {}
        for e in self._errors:
            counts[e.step] = counts.get(e.step, 0) + 1
        return counts
    
    def clear(self) -> None:
        """Clear all errors."""
        self._errors = []
