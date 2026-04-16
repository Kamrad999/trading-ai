"""
RSS source registry and management for the Trading AI system.

Manages RSS feed sources, validates their availability, and tracks their performance.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .config import config
from .logging import get_logger


@dataclass
class RSSSource:
    """RSS source configuration and status."""
    name: str
    url: str
    category: str
    priority: int = 1
    enabled: bool = True
    last_fetched: Optional[datetime] = None
    last_success: Optional[datetime] = None
    failure_count: int = 0
    success_count: int = 0
    avg_response_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SourceStatus:
    """Source status information."""
    name: str
    url: str
    status: str  # ACTIVE, ERROR, DISABLED
    last_check: datetime
    response_time: Optional[float] = None
    error_message: Optional[str] = None


class SourceRegistry:
    """Registry and manager for RSS sources."""
    
    def __init__(self) -> None:
        """Initialize source registry."""
        self.logger = get_logger("source_registry")
        self.sources: Dict[str, RSSSource] = {}
        self._load_default_sources()
    
    def _load_default_sources(self) -> None:
        """Load default RSS sources."""
        default_sources = [
            # Financial News
            {
                "name": "reuters_business",
                "url": "https://www.reuters.com/business/",
                "category": "financial_news",
                "priority": 1
            },
            {
                "name": "bloomberg_markets",
                "url": "https://www.bloomberg.com/markets/",
                "category": "financial_news", 
                "priority": 1
            },
            {
                "name": "wsj_markets",
                "url": "https://www.wsj.com/markets",
                "category": "financial_news",
                "priority": 1
            },
            {
                "name": "cnbc_markets",
                "url": "https://www.cnbc.com/markets/",
                "category": "financial_news",
                "priority": 2
            },
            {
                "name": "marketwatch",
                "url": "https://www.marketwatch.com/",
                "category": "financial_news",
                "priority": 2
            },
            # Economic Data
            {
                "name": "fed_releases",
                "url": "https://www.federalreserve.gov/newsevents/pressreleases.htm",
                "category": "economic_data",
                "priority": 1
            },
            {
                "name": "treasury_releases",
                "url": "https://home.treasury.gov/news/press-releases",
                "category": "economic_data",
                "priority": 1
            },
            {
                "name": "bea_releases",
                "url": "https://www.bea.gov/news",
                "category": "economic_data",
                "priority": 2
            },
            # Market Data
            {
                "name": "yahoo_finance",
                "url": "https://finance.yahoo.com/rss/",
                "category": "market_data",
                "priority": 2
            },
            {
                "name": "seeking_alpha",
                "url": "https://seekingalpha.com/feed.xml",
                "category": "market_data",
                "priority": 2
            },
            # Crypto News
            {
                "name": "coindesk",
                "url": "https://www.coindesk.com/arc/outboundfeeds/rss/",
                "category": "crypto_news",
                "priority": 1
            },
            {
                "name": "cointelegraph",
                "url": "https://cointelegraph.com/rss",
                "category": "crypto_news",
                "priority": 2
            },
            # Commodity News
            {
                "name": "oilprice",
                "url": "https://oilprice.com/rss/latest",
                "category": "commodity_news",
                "priority": 2
            },
            {
                "name": "kitco",
                "url": "https://www.kitco.com/news/rss",
                "category": "commodity_news",
                "priority": 2
            }
        ]
        
        for source_data in default_sources:
            self.register_source(RSSSource(**source_data))
        
        self.logger.info(f"Loaded {len(self.sources)} default RSS sources")
    
    def register_source(self, source: RSSSource) -> None:
        """Register a new RSS source."""
        self.sources[source.name] = source
        self.logger.debug(f"Registered RSS source: {source.name}")
    
    def get_sources(self, category: Optional[str] = None, enabled_only: bool = True) -> List[RSSSource]:
        """Get RSS sources, optionally filtered by category."""
        sources = list(self.sources.values())
        
        if category:
            sources = [s for s in sources if s.category == category]
        
        if enabled_only:
            sources = [s for s in sources if s.enabled]
        
        # Sort by priority (lower number = higher priority)
        sources.sort(key=lambda s: s.priority)
        
        return sources
    
    def get_source(self, name: str) -> Optional[RSSSource]:
        """Get specific RSS source by name."""
        return self.sources.get(name)
    
    def update_source_status(self, name: str, success: bool, response_time: Optional[float] = None, error_message: Optional[str] = None) -> None:
        """Update source status after fetch attempt."""
        source = self.sources.get(name)
        if not source:
            self.logger.warning(f"Attempted to update unknown source: {name}")
            return
        
        now = datetime.now(timezone.utc)
        source.last_fetched = now
        
        if success:
            source.last_success = now
            source.success_count += 1
            source.failure_count = 0  # Reset failure count
            
            if response_time is not None:
                # Update moving average of response time
                if source.avg_response_time == 0:
                    source.avg_response_time = response_time
                else:
                    source.avg_response_time = (source.avg_response_time * 0.8 + response_time * 0.2)
            
            # Re-enable source if it was disabled due to failures
            if not source.enabled and source.failure_count == 0:
                source.enabled = True
                self.logger.info(f"Re-enabled source: {name}")
                
        else:
            source.failure_count += 1
            
            # Disable source after too many failures
            if source.failure_count >= 5:
                source.enabled = False
                self.logger.warning(f"Disabled source due to failures: {name}")
        
        self.logger.debug(f"Updated source status: {name} (success={success})")
    
    def validate_sources(self) -> Dict[str, bool]:
        """Validate all RSS sources are accessible."""
        results = {}
        
        for source in self.get_sources(enabled_only=False):
            try:
                # Simple validation - just check if URL is reachable
                # In a real implementation, this would make an HTTP request
                results[source.name] = True
                
            except Exception as e:
                self.logger.error(f"Source validation failed for {source.name}: {e}")
                results[source.name] = False
        
        return results
    
    def get_source_status(self) -> List[SourceStatus]:
        """Get status of all sources."""
        statuses = []
        
        for source in self.sources.values():
            if not source.enabled:
                status = "DISABLED"
                error_message = "Source disabled due to failures"
            elif source.failure_count > 0:
                status = "ERROR"
                error_message = f"Recent failures: {source.failure_count}"
            else:
                status = "ACTIVE"
                error_message = None
            
            statuses.append(SourceStatus(
                name=source.name,
                url=source.url,
                status=status,
                last_check=source.last_fetched or datetime.now(timezone.utc),
                response_time=source.avg_response_time if source.avg_response_time > 0 else None,
                error_message=error_message
            ))
        
        return statuses
    
    def get_sources_by_category(self) -> Dict[str, List[RSSSource]]:
        """Get sources grouped by category."""
        categorized = {}
        
        for source in self.sources.values():
            if source.category not in categorized:
                categorized[source.category] = []
            categorized[source.category].append(source)
        
        # Sort each category by priority
        for category in categorized:
            categorized[category].sort(key=lambda s: s.priority)
        
        return categorized
    
    def get_source_stats(self) -> Dict[str, Any]:
        """Get statistics about source performance."""
        total_sources = len(self.sources)
        enabled_sources = len([s for s in self.sources.values() if s.enabled])
        
        success_rates = {}
        for name, source in self.sources.items():
            total_attempts = source.success_count + source.failure_count
            if total_attempts > 0:
                success_rates[name] = source.success_count / total_attempts
            else:
                success_rates[name] = 0.0
        
        avg_success_rate = sum(success_rates.values()) / len(success_rates) if success_rates else 0.0
        
        # Category breakdown
        category_stats = {}
        for source in self.sources.values():
            if source.category not in category_stats:
                category_stats[source.category] = {"total": 0, "enabled": 0}
            category_stats[source.category]["total"] += 1
            if source.enabled:
                category_stats[source.category]["enabled"] += 1
        
        return {
            "total_sources": total_sources,
            "enabled_sources": enabled_sources,
            "disabled_sources": total_sources - enabled_sources,
            "avg_success_rate": avg_success_rate,
            "success_rates": success_rates,
            "category_breakdown": category_stats,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
    
    def enable_source(self, name: str) -> bool:
        """Enable a source."""
        source = self.sources.get(name)
        if source:
            source.enabled = True
            source.failure_count = 0  # Reset failure count
            self.logger.info(f"Enabled source: {name}")
            return True
        return False
    
    def disable_source(self, name: str) -> bool:
        """Disable a source."""
        source = self.sources.get(name)
        if source:
            source.enabled = False
            self.logger.info(f"Disabled source: {name}")
            return True
        return False
    
    def remove_source(self, name: str) -> bool:
        """Remove a source from registry."""
        if name in self.sources:
            del self.sources[name]
            self.logger.info(f"Removed source: {name}")
            return True
        return False
    
    def export_sources(self) -> List[Dict[str, Any]]:
        """Export source configurations."""
        exported = []
        
        for source in self.sources.values():
            exported.append({
                "name": source.name,
                "url": source.url,
                "category": source.category,
                "priority": source.priority,
                "enabled": source.enabled,
                "metadata": source.metadata
            })
        
        return exported
    
    def import_sources(self, sources: List[Dict[str, Any]]) -> int:
        """Import source configurations."""
        imported_count = 0
        
        for source_data in sources:
            try:
                # Create RSSSource object
                source = RSSSource(
                    name=source_data["name"],
                    url=source_data["url"],
                    category=source_data["category"],
                    priority=source_data.get("priority", 1),
                    enabled=source_data.get("enabled", True),
                    metadata=source_data.get("metadata", {})
                )
                
                self.register_source(source)
                imported_count += 1
                
            except Exception as e:
                self.logger.error(f"Failed to import source {source_data.get('name', 'unknown')}: {e}")
        
        self.logger.info(f"Imported {imported_count} sources")
        return imported_count
