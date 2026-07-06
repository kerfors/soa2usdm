"""
Analytics Tracking

Collects metrics across pipeline execution.
"""

from datetime import datetime, timezone
from typing import Any


class AnalyticsBase:
    """Base class for analytics - defines interface."""
    
    def record(self, key: str, value: Any) -> None:
        """Record a metric value."""
        pass
    
    def increment(self, key: str, amount: int = 1) -> None:
        """Increment a counter."""
        pass
    
    def start_timer(self, key: str) -> None:
        """Start a timer."""
        pass
    
    def stop_timer(self, key: str) -> float:
        """Stop a timer, return elapsed seconds."""
        pass
    
    @property
    def all(self) -> dict:
        """Return all metrics."""
        return {}


class Analytics(AnalyticsBase):
    """Collects metrics across pipeline execution."""
    
    def __init__(self):
        self._metrics: dict[str, Any] = {}
        self._timers: dict[str, datetime] = {}
    
    def record(self, key: str, value: Any) -> None:
        """Record a metric value."""
        self._metrics[key] = value
    
    def increment(self, key: str, amount: int = 1) -> None:
        """Increment a counter."""
        self._metrics[key] = self._metrics.get(key, 0) + amount
    
    def start_timer(self, key: str) -> None:
        """Start a timer."""
        self._timers[key] = datetime.now(timezone.utc)
    
    def stop_timer(self, key: str) -> float:
        """Stop a timer, return elapsed seconds."""
        if key not in self._timers:
            return 0.0
        start = self._timers.pop(key)
        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        self._metrics[f"{key}_seconds"] = elapsed
        return elapsed
    
    @property
    def all(self) -> dict:
        """Return all metrics."""
        return self._metrics.copy()
    
    def clear(self) -> None:
        """Clear all metrics."""
        self._metrics = {}
        self._timers = {}
