"""
Real tests for duplicate filtering functionality.

Tests URL hash deduplication, title similarity, timestamp window checks,
and state-backed seen article registry.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from trading_ai.validation.duplicate_filter import DuplicateFilter
from trading_ai.core.models import Article


class TestDuplicateFilter:
    """Real duplicate filtering tests."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.filter = DuplicateFilter()
    
    def test_duplicate_filter_initialization(self):
        """Test DuplicateFilter initializes correctly."""
        assert self.filter is not None
        assert self.filter.title_similarity_threshold == 0.85
        assert self.filter.timestamp_window_hours == 24
        assert self.filter.url_hash_cache_size == 10000
        assert self.filter.max_recent_articles == 1000
    
    def test_url_hash_generation(self):
        """Test URL hash generation."""
        url1 = "https://example.com/article1"
        url2 = "https://example.com/article1?utm_source=test"
        url3 = "https://example.com/article2"
        
        hash1 = self.filter._generate_url_hash(url1)
        hash2 = self.filter._generate_url_hash(url2)
        hash3 = self.filter._generate_url_hash(url3)
        
        # Same URL with different tracking params should have same hash
        assert hash1 == hash2
        # Different URLs should have different hashes
        assert hash1 != hash3
        assert len(hash1) == 16
    
    def test_title_similarity_detection(self):
        """Test title similarity detection."""
        # Create test articles
        article1 = Article(
            title="Bitcoin reaches new all-time high of $100,000",
            content="Bitcoin price surged to new heights",
            source="Test Source",
            timestamp=datetime.now(timezone.utc),
            url="https://example.com/article1",
            metadata={}
        )
        
        article2 = Article(
            title="Bitcoin reaches new all-time high of $100,000",  # Exact same title
            content="Different content",
            source="Another Source",
            timestamp=datetime.now(timezone.utc),
            url="https://example.com/article2",
            metadata={}
        )
        
        article3 = Article(
            title="Bitcoin reaches new all-time high of $99,999",  # Very similar title
            content="Bitcoin price almost reached new heights",
            source="Test Source",
            timestamp=datetime.now(timezone.utc),
            url="https://example.com/article3",
            metadata={}
        )
        
        # Add first article to seen articles
        self.filter._add_to_seen_articles(article1)
        
        # Exact duplicate should be detected
        assert self.filter._has_similar_title(article2) is True
        
        # Very similar title should be detected
        assert self.filter._has_similar_title(article3) is True
    
    def test_title_similarity_threshold(self):
        """Test title similarity threshold."""
        article1 = Article(
            title="Bitcoin price analysis",
            content="Content 1",
            source="Test Source",
            timestamp=datetime.now(timezone.utc),
            url="https://example.com/article1",
            metadata={}
        )
        
        article2 = Article(
            title="Stock market analysis",  # Different enough
            content="Content 2",
            source="Test Source",
            timestamp=datetime.now(timezone.utc),
            url="https://example.com/article2",
            metadata={}
        )
        
        # Add first article
        self.filter._add_to_seen_articles(article1)
        
        # Different title should not be detected as duplicate
        assert self.filter._has_similar_title(article2) is False
    
    def test_timestamp_window_check(self):
        """Test timestamp window duplicate detection."""
        now = datetime.now(timezone.utc)
        old_time = now - timedelta(hours=25)  # Older than 24 hour window
        
        article1 = Article(
            title="Test Article",
            content="Content 1",
            source="Test Source",
            timestamp=now,
            url="https://example.com/article1",
            metadata={}
        )
        
        article2 = Article(
            title="Test Article",  # Same title
            content="Content 2",
            source="Test Source",
            timestamp=old_time,  # But too old
            url="https://example.com/article2",
            metadata={}
        )
        
        # Add recent article
        self.filter._add_to_seen_articles(article1)
        
        # Old article should not be detected as duplicate
        assert self.filter._has_recent_similar_article(article2) is False
    
    def test_duplicate_detection(self):
        """Test comprehensive duplicate detection."""
        now = datetime.now(timezone.utc)
        
        article1 = Article(
            title="Bitcoin hits new record",
            content="Bitcoin reached a new price record",
            source="Test Source",
            timestamp=now,
            url="https://example.com/article1",
            metadata={}
        )
        
        article2 = Article(
            title="Bitcoin hits new record",  # Same title
            content="Different content",
            source="Test Source",
            timestamp=now,
            url="https://example.com/article2",  # Different URL
            metadata={}
        )
        
        article3 = Article(
            title="Ethereum analysis",  # Different title
            content="Ethereum price analysis",
            source="Test Source",
            timestamp=now,
            url="https://example.com/article3",
            metadata={}
        )
        
        # Add first article
        self.filter._add_to_seen_articles(article1)
        
        # Same title should be detected as duplicate
        assert self.filter._is_duplicate(article2) is True
        
        # Different title should not be duplicate
        assert self.filter._is_duplicate(article3) is False
    
    def test_filter_duplicates_batch(self):
        """Test filtering duplicates from article batch."""
        now = datetime.now(timezone.utc)
        
        articles = [
            Article("Article 1", "Content 1", "Source1", now, "https://example.com/1", {}),
            Article("Article 1", "Content 2", "Source2", now, "https://example.com/2", {}),  # Duplicate title
            Article("Article 2", "Content 3", "Source1", now, "https://example.com/3", {}),
            Article("Article 3", "Content 4", "Source1", now, "https://example.com/4", {}),
            Article("Article 3", "Content 5", "Source2", now, "https://example.com/5", {}),  # Duplicate title
        ]
        
        unique_articles = self.filter.filter_duplicates(articles)
        
        # Should have 3 unique articles
        assert len(unique_articles) == 3
        # Should have removed 2 duplicates
        assert len(articles) - len(unique_articles) == 2
    
    def test_state_persistence(self):
        """Test state persistence across filter instances."""
        now = datetime.now(timezone.utc)
        
        article = Article(
            title="Test Article",
            content="Test content",
            source="Test Source",
            timestamp=now,
            url="https://example.com/test",
            metadata={}
        )
        
        # Add article to first filter instance
        self.filter._add_to_seen_articles(article)
        
        # Create new filter instance (should load state)
        new_filter = DuplicateFilter()
        
        # New filter should have the article in seen articles
        assert len(new_filter.seen_articles) > 0
        assert len(new_filter.url_hashes) > 0
    
    def test_cleanup_old_entries(self):
        """Test cleanup of old entries."""
        now = datetime.now(timezone.utc)
        old_time = now - timedelta(hours=25)
        
        # Add recent and old articles
        recent_article = Article("Recent", "Content", "Source", now, "https://example.com/recent", {})
        old_article = Article("Old", "Content", "Source", old_time, "https://example.com/old", {})
        
        self.filter._add_to_seen_articles(recent_article)
        self.filter._add_to_seen_articles(old_article)
        
        # Should have both articles initially
        assert len(self.filter.seen_articles) == 2
        
        # Run cleanup
        self.filter._cleanup_old_entries()
        
        # Should only have recent article
        assert len(self.filter.seen_articles) == 1
        assert "Recent" in str(self.filter.seen_articles)
    
    def test_find_similar_articles(self):
        """Test finding similar articles."""
        now = datetime.now(timezone.utc)
        
        article1 = Article(
            title="Bitcoin price analysis for today",
            content="Bitcoin price analysis",
            source="Test Source",
            timestamp=now,
            url="https://example.com/article1",
            metadata={}
        )
        
        article2 = Article(
            title="Bitcoin price analysis tomorrow",
            content="Different content",
            source="Test Source",
            timestamp=now,
            url="https://example.com/article2",
            metadata={}
        )
        
        # Add first article
        self.filter._add_to_seen_articles(article1)
        
        # Find similar articles to second
        similar = self.filter.find_similar_articles(article2)
        
        # Should find the first article as similar
        assert len(similar) == 1
        assert similar[0]["similarity"] > 0.8  # High similarity
        assert "Bitcoin price analysis" in similar[0]["title"]
    
    def test_get_duplicate_stats(self):
        """Test getting duplicate filter statistics."""
        stats = self.filter.get_duplicate_stats()
        
        assert "url_hashes_cached" in stats
        assert "recent_articles_count" in stats
        assert "seen_articles_count" in stats
        assert "title_similarity_threshold" in stats
        assert "timestamp_window_hours" in stats
        assert stats["title_similarity_threshold"] == 0.85
        assert stats["timestamp_window_hours"] == 24
    
    def test_reset_duplicate_state(self):
        """Test resetting duplicate filter state."""
        # Add some articles
        article = Article("Test", "Content", "Source", datetime.now(timezone.utc), "https://example.com/test", {})
        self.filter._add_to_seen_articles(article)
        
        # Should have some data
        assert len(self.filter.seen_articles) > 0
        assert len(self.filter.url_hashes) > 0
        
        # Reset state
        self.filter.reset_duplicate_state()
        
        # Should be empty
        assert len(self.filter.seen_articles) == 0
        assert len(self.filter.url_hashes) == 0
        assert len(self.filter.recent_articles) == 0
    
    def test_max_articles_per_feed_limit(self):
        """Test max articles per feed limit."""
        # Create more articles than the limit
        articles = []
        for i in range(60):  # More than max_articles_per_feed (50)
            articles.append(Article(f"Article {i}", f"Content {i}", "Source", datetime.now(timezone.utc), f"https://example.com/{i}", {}))
        
        unique_articles = self.filter.filter_duplicates(articles)
        
        # Should process all articles (limit is in news_collector, not duplicate_filter)
        assert len(unique_articles) == len(articles)
    
    def test_performance_with_large_batch(self):
        """Test performance with large article batch."""
        import time
        
        # Create large batch
        articles = []
        for i in range(1000):
            articles.append(Article(f"Article {i}", f"Content {i}", "Source", datetime.now(timezone.utc), f"https://example.com/{i}", {}))
        
        start_time = time.time()
        unique_articles = self.filter.filter_duplicates(articles)
        processing_time = (time.time() - start_time) * 1000
        
        # Should complete within reasonable time
        assert processing_time < 5000  # Less than 5 seconds
        assert len(unique_articles) == len(articles)  # All should be unique


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
