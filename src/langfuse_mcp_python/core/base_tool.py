"""
Enhanced Base Tool with Production Features
- Retry logic with exponential backoff
- Caching layer
- Proper error handling
- Metrics collection
- Structured logging
"""

from __future__ import annotations

import hashlib
import json
import logging
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Callable
from functools import wraps

from httpx import HTTPStatusError, RequestError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)


# Structured logging
class StructuredLogger:
    """JSON structured logging for production observability"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
                '"logger": "%(name)s", "message": "%(message)s"}'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def info(self, message: str, **kwargs):
        self.logger.info(json.dumps({"message": message, **kwargs}))
    
    def warning(self, message: str, **kwargs):
        self.logger.warning(json.dumps({"message": message, **kwargs}))
    
    def error(self, message: str, **kwargs):
        self.logger.error(json.dumps({"message": message, **kwargs}))


# Simple in-memory cache with TTL
class InMemoryCache:
    """Production-ready cache with TTL support"""
    
    def __init__(self, default_ttl: int = 300):
        self.cache: Dict[str, tuple[Any, datetime]] = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        if key in self.cache:
            value, expiry = self.cache[key]
            if datetime.now() < expiry:
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache with TTL"""
        ttl = ttl or self.default_ttl
        expiry = datetime.now() + timedelta(seconds=ttl)
        self.cache[key] = (value, expiry)
    
    def invalidate(self, pattern: str = None):
        """Invalidate cache entries matching pattern"""
        if pattern is None:
            self.cache.clear()
        else:
            keys_to_delete = [k for k in self.cache.keys() if pattern in k]
            for key in keys_to_delete:
                del self.cache[key]
    
    @staticmethod
    def make_key(*args, **kwargs) -> str:
        """Generate cache key from arguments"""
        key_data = json.dumps([args, sorted(kwargs.items())], sort_keys=True, default=str)
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]


# Metrics collection
class MetricsCollector:
    """Collect operational metrics"""
    
    def __init__(self):
        self.counters: Dict[str, int] = {}
        self.timings: Dict[str, List[float]] = {}
    
    def increment(self, metric: str, value: int = 1):
        """Increment a counter"""
        self.counters[metric] = self.counters.get(metric, 0) + value
    
    def record_timing(self, metric: str, duration_ms: float):
        """Record a timing metric"""
        if metric not in self.timings:
            self.timings[metric] = []
        self.timings[metric].append(duration_ms)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get aggregated statistics"""
        stats = {"counters": self.counters}
        
        # Calculate percentiles for timings
        for metric, timings in self.timings.items():
            if timings:
                sorted_timings = sorted(timings)
                stats[f"{metric}_p50"] = sorted_timings[len(sorted_timings) // 2]
                stats[f"{metric}_p95"] = sorted_timings[int(len(sorted_timings) * 0.95)]
                stats[f"{metric}_avg"] = sum(timings) / len(timings)
        
        return stats


class BaseLangfuseTool(ABC):
    """
    Enhanced base class for Langfuse tools with production features:
    - Automatic retry with exponential backoff
    - Caching with TTL
    - Proper error handling
    - Metrics collection
    - Structured logging
    """
    
    def __init__(
        self,
        langfuse_client,
        cache: Optional[InMemoryCache] = None,
        metrics: Optional[MetricsCollector] = None,
    ):
        self.langfuse = langfuse_client
        self.cache = cache or InMemoryCache(default_ttl=300)
        self.metrics = metrics or MetricsCollector()
        self.logger = StructuredLogger(self.__class__.__name__)
    
    @abstractmethod
    async def execute(self, args: Dict[str, Any]) -> str:
        """Execute the tool - must be implemented by subclass"""
        pass
    
    # ============================================================================
    # RETRY LOGIC
    # ============================================================================
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((RequestError, HTTPStatusError)),
        reraise=True,
    )
    async def _fetch_with_retry(self, fetch_func: Callable, *args, **kwargs) -> Any:
        """
        Execute API call with automatic retry logic
        - Retries up to 3 times
        - Exponential backoff (2s, 4s, 8s)
        - Only retries on network/HTTP errors
        """
        start_time = datetime.now()
        
        try:
            result = fetch_func(*args, **kwargs)
            if asyncio.iscoroutine(result):
                result = await result
            
            # Record success metrics
            duration = (datetime.now() - start_time).total_seconds() * 1000
            self.metrics.increment(f"{self.__class__.__name__}.success")
            self.metrics.record_timing(f"{self.__class__.__name__}.latency", duration)
            
            return result
        
        except HTTPStatusError as e:
            self.metrics.increment(f"{self.__class__.__name__}.http_error_{e.response.status_code}")
            self.logger.error(
                "HTTP error",
                status_code=e.response.status_code,
                url=str(e.request.url),
            )
            raise
        
        except RequestError as e:
            self.metrics.increment(f"{self.__class__.__name__}.network_error")
            self.logger.error("Network error", error=str(e))
            raise
        
        except Exception as e:
            self.metrics.increment(f"{self.__class__.__name__}.unknown_error")
            self.logger.error("Unknown error", error=str(e), error_type=type(e).__name__)
            raise
    
    # ============================================================================
    # CACHING HELPERS
    # ============================================================================
    
    def _get_cached_or_fetch(
        self,
        cache_key: str,
        fetch_func: Callable,
        ttl: Optional[int] = None,
    ) -> Any:
        """
        Get from cache or fetch and cache
        - Checks cache first
        - Falls back to fetch if cache miss
        - Automatically caches result
        """
        # Try cache first
        cached = self.cache.get(cache_key)
        if cached is not None:
            self.metrics.increment(f"{self.__class__.__name__}.cache_hit")
            self.logger.info("Cache hit", key=cache_key[:16])
            return cached
        
        # Cache miss - fetch from API
        self.metrics.increment(f"{self.__class__.__name__}.cache_miss")
        self.logger.info("Cache miss", key=cache_key[:16])
        
        result = fetch_func()
        self.cache.set(cache_key, result, ttl=ttl)
        
        return result
    
    # ============================================================================
    # PAGINATION HELPERS
    # ============================================================================
    
    async def _fetch_all_paginated(
        self,
        fetch_func: Callable,
        max_pages: int = 100,
        **kwargs
    ) -> List[Any]:
        """
        Fetch all pages of a paginated API response
        - Automatically handles pagination
        - Safety limit to prevent infinite loops
        - Returns flattened list of all items
        """
        all_items = []
        page = 1
        
        self.logger.info("Starting paginated fetch", max_pages=max_pages)
        
        while page <= max_pages:
            response = await self._fetch_with_retry(
                fetch_func,
                page=page,
                limit=100,
                **kwargs
            )
            
            if not response.data:
                break
            
            all_items.extend(response.data)
            
            # Check if we've reached the last page
            if hasattr(response, 'meta'):
                if page >= response.meta.total_pages:
                    self.logger.info(
                        "Reached last page",
                        page=page,
                        total_pages=response.meta.total_pages,
                        items_fetched=len(all_items)
                    )
                    break
            
            page += 1
        
        self.logger.info("Pagination complete", total_items=len(all_items), pages=page - 1)
        return all_items
    
    # ============================================================================
    # METRIC CALCULATION (FIXED)
    # ============================================================================
    
    def _calculate_trace_metrics(self, trace) -> Dict[str, Any]:
        """
        Calculate accurate metrics from trace
        FIXED: Now properly extracts real values instead of returning zeros
        """
        metrics = {
            "latency_ms": 0,
            "tokens": 0,
            "cost": 0.0,
            "observation_count": 0,
        }
        
        # Extract latency
        if hasattr(trace, 'latency') and trace.latency is not None:
            metrics["latency_ms"] = float(trace.latency)
        
        # Extract token usage
        if hasattr(trace, 'usage') and trace.usage:
            if hasattr(trace.usage, 'total'):
                metrics["tokens"] = int(trace.usage.total)
            elif hasattr(trace.usage, 'totalTokens'):
                metrics["tokens"] = int(trace.usage.totalTokens)
        
        # Extract cost
        if hasattr(trace, 'calculated_total_cost') and trace.calculated_total_cost is not None:
            metrics["cost"] = float(trace.calculated_total_cost)
        elif hasattr(trace, 'calculatedTotalCost') and trace.calculatedTotalCost is not None:
            metrics["cost"] = float(trace.calculatedTotalCost)
        
        # Extract observation count
        if hasattr(trace, 'observation_count'):
            metrics["observation_count"] = int(trace.observation_count)
        elif hasattr(trace, 'observationCount'):
            metrics["observation_count"] = int(trace.observationCount)
        
        return metrics
    
    def _calculate_observation_metrics(self, observation) -> Dict[str, Any]:
        """Calculate metrics for a single observation"""
        metrics = {
            "latency_ms": 0,
            "tokens": 0,
            "cost": 0.0,
        }
        
        # Calculate duration
        if hasattr(observation, 'start_time') and hasattr(observation, 'end_time'):
            if observation.start_time and observation.end_time:
                delta = observation.end_time - observation.start_time
                metrics["latency_ms"] = delta.total_seconds() * 1000
        
        # Extract tokens
        if hasattr(observation, 'usage') and observation.usage:
            if hasattr(observation.usage, 'total'):
                metrics["tokens"] = int(observation.usage.total)
        
        # Extract cost
        if hasattr(observation, 'calculated_total_cost') and observation.calculated_total_cost:
            metrics["cost"] = float(observation.calculated_total_cost)
        
        return metrics
    
    # ============================================================================
    # STATUS HELPERS
    # ============================================================================
    
    def _get_trace_status(self, trace) -> str:
        """Determine trace status from trace object"""
        if hasattr(trace, 'level'):
            if trace.level == "ERROR":
                return "error"
            elif trace.level == "WARNING":
                return "warning"
        
        # Check if trace has any error observations
        if hasattr(trace, 'observations'):
            for obs in trace.observations:
                if hasattr(obs, 'level') and obs.level == "ERROR":
                    return "error"
        
        return "completed"
    
    # ============================================================================
    # DATETIME HELPERS
    # ============================================================================
    
    def _parse_datetime(self, value: Optional[str]) -> Optional[datetime]:
        """Parse ISO 8601 datetime strings safely"""
        if not value:
            return None
        
        try:
            # Handle various ISO 8601 formats
            if value.endswith('Z'):
                value = value.replace('Z', '+00:00')
            return datetime.fromisoformat(value)
        except (ValueError, AttributeError):
            self.logger.warning("Failed to parse datetime", value=value)
            return None
    
    def _coerce_to_naive_utc(self, dt: datetime) -> datetime:
        """Convert datetime to naive UTC for safe comparisons"""
        if dt is None:
            return None
        
        if dt.tzinfo is None:
            return dt
        
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    
    def _format_datetime(self, dt: Optional[datetime]) -> str:
        """Format datetime for display"""
        if dt is None:
            return "N/A"
        return dt.isoformat()
    
    # ============================================================================
    # FORMATTING HELPERS
    # ============================================================================
    
    def _format_cost(self, cost: float) -> str:
        """Format cost in USD"""
        return f"${cost:.4f}"
    
    def _format_duration(self, ms: float) -> str:
        """Format duration in human-readable format"""
        if ms < 1000:
            return f"{ms:.0f}ms"
        elif ms < 60000:
            return f"{ms/1000:.2f}s"
        else:
            return f"{ms/60000:.2f}m"
    
    def _format_tokens(self, tokens: int) -> str:
        """Format token count"""
        if tokens >= 1_000_000:
            return f"{tokens/1_000_000:.2f}M"
        elif tokens >= 1_000:
            return f"{tokens/1_000:.1f}K"
        else:
            return str(tokens)
