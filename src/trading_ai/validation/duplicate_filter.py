"""
Real duplicate filtering for Trading AI.

Implements URL hash deduplication, title similarity, timestamp window checks,
and state-backed seen article registry with persistent cache.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher
from typing import Any, Dict, List, Set, Tuple

from ..core.models import Article
from ..infrastructure.config import config
from ..infrastructure.logging import get_logger
from ..infrastructure.state_manager import StateManager


class DuplicateFilter:
    """Real duplicate detection and filtering."""
    
    def __init__(self) -> None:
        """Initialize duplicate filter with state persistence."""
        self.logger = get_logger("duplicate_filter")
        self.state_manager = StateManager()
        
        # Duplicate detection thresholds
        self.title_similarity_threshold = 1.0  # Set to 1.0 to only catch exact duplicates
        self.timestamp_window_hours = 24
        self.url_hash_cache_size = 10000
        
        # Common market news prefixes to ignore in similarity comparison
        self.common_prefixes = [
            "Breaking:",
            "Update:",
            "Live:",
            "Market Alert:",
            "Reuters -",
            "Bloomberg -",
            "CNBC -",
            "MarketWatch -",
            "Yahoo Finance -",
            "Financial Times -",
            "Wall Street Journal -"
        ]
        self.max_recent_articles = 1000
        
        # In-memory caches
        self.url_hashes: Set[str] = set()
        self.recent_articles: List[Dict[str, Any]] = []
        self.seen_articles: Dict[str, Dict[str, Any]] = {}
        
        # Load state from persistence
        self._load_duplicate_state()
    
    def _load_duplicate_state(self) -> None:
        """Load duplicate filter state from persistent storage."""
        try:
            state = self.state_manager.load_state()
            dup_state = state.get("duplicate_filter", {})
            
            self.url_hashes = set(dup_state.get("url_hashes", []))
            self.seen_articles = dup_state.get("seen_articles", {})
            
            # Load recent articles (limit to prevent memory issues)
            recent = dup_state.get("recent_articles", [])
            self.recent_articles = recent[-self.max_recent_articles:]
            
            self.logger.info(
                f"Loaded duplicate filter state: "
                f"{len(self.url_hashes)} URL hashes, "
                f"{len(self.seen_articles)} seen articles"
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to load duplicate state: {e}")
            self._initialize_empty_state()
    
    def _initialize_empty_state(self) -> None:
        """Initialize empty duplicate filter state."""
        self.url_hashes = set()
        self.recent_articles = []
        self.seen_articles = {}
    
    def _save_duplicate_state(self) -> None:
        """Save duplicate filter state to persistent storage."""
        try:
            # Get current system state
            state = self.state_manager.load_state()
            
            # Update duplicate filter state
            dup_state = {
                "url_hashes": list(self.url_hashes),
                "seen_articles": self.seen_articles,
                "recent_articles": self.recent_articles[-self.max_recent_articles:],
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
            state["duplicate_filter"] = dup_state
            
            # Save to persistent storage
            self.state_manager.save_state(state)
            
            self.logger.debug("Saved duplicate filter state")
            
        except Exception as e:
            self.logger.error(f"Failed to save duplicate state: {e}")
    
    def filter_duplicates(self, articles: List[Article]) -> List[Article]:
        """
        Filter duplicate articles from the input list.
        
        Args:
            articles: List of articles to filter
            
        Returns:
            List of unique articles
        """
        start_time = time.time()
        unique_articles = []
        duplicate_count = 0
        
        self.logger.info(f"Filtering duplicates from {len(articles)} articles")
        
        for article in articles:
            if self._is_duplicate(article):
                duplicate_count += 1
                self.logger.debug(f"Duplicate detected: {article.title[:50]}...")
            else:
                unique_articles.append(article)
                self._add_to_seen_articles(article)
        
        # Clean up old entries
        self._cleanup_old_entries()
        
        # Save state
        self._save_duplicate_state()
        
        processing_time = (time.time() - start_time) * 1000
        
        self.logger.info(
            f"Duplicate filtering completed: {len(unique_articles)} unique, "
            f"{duplicate_count} duplicates removed in {processing_time:.1f}ms"
        )
        
        return unique_articles
    
    def _is_duplicate(self, article: Article) -> bool:
        """
        Check if article is a duplicate.
        
        Args:
            article: Article to check
            
        Returns:
            True if duplicate, False otherwise
        """
        # Check URL hash
        url_hash = self._generate_url_hash(article.url)
        if url_hash in self.url_hashes:
            return True
        
        # Check title similarity with recent articles
        if self._has_similar_title(article):
            return True
        
        # Check timestamp window for same source
        if self._has_recent_similar_article(article):
            return True
        
        return False
    
    def _generate_url_hash(self, url: str) -> str:
        """Generate hash for URL comparison."""
        return hashlib.sha256(url.encode()).hexdigest()[:16]
    
    def _normalize_title(self, title: str) -> str:
        """Normalize title by removing common prefixes only."""
        
        # Remove common prefixes
        normalized = title.strip()
        for prefix in self.common_prefixes:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):].strip()
                break
        
        # Only normalize case, keep punctuation and spacing intact
        return normalized.strip()
    
    def _normalize_timestamp(self, timestamp) -> datetime:
        """Normalize timestamp to datetime object."""
        if isinstance(timestamp, datetime):
            return timestamp
        elif isinstance(timestamp, str):
            try:
                return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                return datetime.now(timezone.utc)
        else:
            return datetime.now(timezone.utc)
    
    def _has_similar_title(self, article: Article) -> bool:
        """Check if article title is similar to recent articles."""
        article_title = self._normalize_title(article.title)
        
        # Check against recent articles
        for recent in self.recent_articles:
            recent_title = self._normalize_title(recent["title"])
            
            # Calculate similarity
            similarity = SequenceMatcher(None, article_title, recent_title).ratio()
            
            if similarity >= self.title_similarity_threshold:
                self.logger.debug(
                    f"Title similarity detected: {similarity:.3f} "
                    f"between '{article_title[:50]}...' and '{recent_title[:50]}...'"
                )
                return True
        
        return False
    
    def _has_recent_similar_article(self, article: Article) -> bool:
        """Check if there's a recent similar article from same source."""
        time_window = timedelta(hours=self.timestamp_window_hours)
        cutoff_time = datetime.now(timezone.utc) - time_window
        
        # Check seen articles from same source within time window
        for seen_id, seen_data in self.seen_articles.items():
            seen_timestamp = seen_data["timestamp"]
            # Handle timestamp type conversion
            if isinstance(seen_timestamp, str):
                try:
                    seen_timestamp = datetime.fromisoformat(seen_timestamp.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    continue  # Skip invalid timestamps
            
            if (seen_data["source"] == article.source and 
                seen_timestamp > cutoff_time):
                
                # Check title similarity with normalization
                seen_title = self._normalize_title(seen_data["title"])
                article_title = self._normalize_title(article.title)
                
                similarity = SequenceMatcher(None, article_title, seen_title).ratio()
                if similarity >= self.title_similarity_threshold:
                    return True
        
        return False
    
    def _add_to_seen_articles(self, article: Article) -> None:
        """Add article to seen articles registry."""
        article_id = hashlib.sha256(
            f"{article.title}{article.url}{article.timestamp.isoformat()}".encode()
        ).hexdigest()[:16]
        
        # Add to seen articles
        self.seen_articles[article_id] = {
            "title": article.title,
            "source": article.source,
            "timestamp": article.timestamp,
            "url": article.url,
            "added_at": datetime.now(timezone.utc)
        }
        
        # Add URL hash
        url_hash = self._generate_url_hash(article.url)
        self.url_hashes.add(url_hash)
        
        # Add to recent articles
        recent_article = {
            "id": article_id,
            "title": article.title,
            "source": article.source,
            "timestamp": article.timestamp,
            "url": article.url
        }
        
        self.recent_articles.append(recent_article)
        
        # Maintain size limits
        if len(self.url_hashes) > self.url_hash_cache_size:
            # Remove oldest entries (simplified - in production would use LRU)
            old_hashes = list(self.url_hashes)[:100]
            for old_hash in old_hashes:
                self.url_hashes.discard(old_hash)
    
    def _cleanup_old_entries(self) -> None:
        """Clean up old entries to prevent memory bloat."""
        # Remove old recent articles
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.timestamp_window_hours)
        
        self.recent_articles = [
            article for article in self.recent_articles
            if self._normalize_timestamp(article["timestamp"]) > cutoff_time
        ]
        
        # Remove old seen articles
        old_seen_ids = [
            article_id for article_id, data in self.seen_articles.items()
            if self._normalize_timestamp(data["timestamp"]) < cutoff_time
        ]
        
        for old_id in old_seen_ids:
            del self.seen_articles[old_id]
        
        # Maintain size limits
        if len(self.recent_articles) > self.max_recent_articles:
            self.recent_articles = self.recent_articles[-self.max_recent_articles:]
        
        if len(self.seen_articles) > self.url_hash_cache_size:
            # Keep most recent entries
            sorted_seen = sorted(
                self.seen_articles.items(),
                key=lambda x: x[1]["timestamp"],
                reverse=True
            )
            self.seen_articles = dict(sorted_seen[:self.url_hash_cache_size])
    
    def find_similar_articles(self, article: Article, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Find articles similar to the given article.
        
        Args:
            article: Reference article
            limit: Maximum number of similar articles to return
            
        Returns:
            List of similar articles with similarity scores
        """
        similar_articles = []
        article_title = article.title.lower().strip()
        
        for seen_id, seen_data in self.seen_articles.items():
            if seen_id == hashlib.sha256(
                f"{article.title}{article.url}{article.timestamp.isoformat()}".encode()
            ).hexdigest()[:16]:
                continue  # Skip self
            
            seen_title = seen_data["title"].lower().strip()
            similarity = SequenceMatcher(None, article_title, seen_title).ratio()
            
            if similarity >= 0.5:  # Lower threshold for similar articles search
                similar_articles.append({
                    "id": seen_id,
                    "title": seen_data["title"],
                    "source": seen_data["source"],
                    "timestamp": seen_data["timestamp"],
                    "url": seen_data["url"],
                    "similarity": similarity
                })
        
        # Sort by similarity and limit results
        similar_articles.sort(key=lambda x: x["similarity"], reverse=True)
        return similar_articles[:limit]
    
def _add_to_seen_articles(self, article: Article) -> None:
    """Add article to seen articles registry."""
    article_id = hashlib.sha256(
        f"{article.title}{article.url}{article.timestamp.isoformat()}".encode()
    ).hexdigest()[:16]
        
    # Add to seen articles
    self.seen_articles[article_id] = {
        "title": article.title,
        "source": article.source,
        "timestamp": article.timestamp,
        "url": article.url,
        "added_at": datetime.now(timezone.utc)
    }
        
    # Add URL hash
    url_hash = self._generate_url_hash(article.url)
    self.url_hashes.add(url_hash)
        
    # Add to recent articles
    recent_article = {
        "id": article_id,
        "title": article.title,
        "source": article.source,
        "timestamp": article.timestamp,
        "url": article.url
    }
        
    self.recent_articles.append(recent_article)
        
    # Maintain size limits
    if len(self.url_hashes) > self.url_hash_cache_size:
        # Remove oldest entries (simplified - in production would use LRU)
        old_hashes = list(self.url_hashes)[:100]
        for old_hash in old_hashes:
            self.url_hashes.discard(old_hash)
    
def _cleanup_old_entries(self) -> None:
    """Clean up old entries to prevent memory bloat."""
    # Remove old recent articles
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.timestamp_window_hours)
        
    self.recent_articles = [
        article for article in self.recent_articles
        if article["timestamp"] > cutoff_time
    ]
        
    # Remove old seen articles
    old_seen_ids = [
        article_id for article_id, data in self.seen_articles.items()
        if data["timestamp"] < cutoff_time
    ]
        
    for old_id in old_seen_ids:
        del self.seen_articles[old_id]
        
    # Maintain size limits
    if len(self.recent_articles) > self.max_recent_articles:
        self.recent_articles = self.recent_articles[-self.max_recent_articles:]
        
    if len(self.seen_articles) > self.url_hash_cache_size:
        # Keep most recent entries
        sorted_seen = sorted(
            self.seen_articles.items(),
            key=lambda x: self._normalize_timestamp(x[1]["timestamp"]),
            reverse=True
        )
        self.seen_articles = dict(sorted_seen[:self.url_hash_cache_size])
    
def find_similar_articles(self, article: Article, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Find articles similar to the given article.
    
    Args:
        article: Reference article
        limit: Maximum number of similar articles to return
            
    Returns:
        List of similar articles with similarity scores
    """
    similar_articles = []
    article_title = article.title.lower().strip()
        
    for seen_id, seen_data in self.seen_articles.items():
        if seen_id == hashlib.sha256(
            f"{article.title}{article.url}{article.timestamp.isoformat()}".encode()
        ).hexdigest()[:16]:
            continue  # Skip self
            
        seen_title = seen_data["title"].lower().strip()
        similarity = SequenceMatcher(None, article_title, seen_title).ratio()
            
        if similarity >= 0.5:  # Lower threshold for similar articles search
            similar_articles.append({
                "id": seen_id,
                "title": seen_data["title"],
                "source": seen_data["source"],
                "timestamp": seen_data["timestamp"],
                "url": seen_data["url"],
                "similarity": similarity
            })
        
    # Sort by similarity and limit results
    similar_articles.sort(key=lambda x: x["similarity"], reverse=True)
    return similar_articles[:limit]
    
def get_duplicate_stats(self) -> Dict[str, Any]:
    """Get duplicate filter statistics."""
    return {
        "url_hashes_cached": len(self.url_hashes),
        "recent_articles_count": len(self.recent_articles),
        "seen_articles_count": len(self.seen_articles),
        "title_similarity_threshold": self.title_similarity_threshold,
        "timestamp_window_hours": self.timestamp_window_hours,
        "cache_size_limit": self.url_hash_cache_size,
        "max_recent_articles": self.max_recent_articles
    }
    
def reset_duplicate_state(self) -> None:
    """Reset duplicate filter state (for testing/recovery)."""
    self._initialize_empty_state()
    self._save_duplicate_state()
    self.logger.info("Duplicate filter state reset")
