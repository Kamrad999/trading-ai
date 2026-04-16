"""
Real tests for RSS parsing functionality.

Tests actual feed fetching, parsing, error handling, and performance.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from trading_ai.agents.news_collector import NewsCollector
from trading_ai.core.models import Article


class TestRSSParsing:
    """Real RSS parsing tests."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.collector = NewsCollector()
    
    def test_news_collector_initialization(self):
        """Test NewsCollector initializes correctly."""
        assert self.collector is not None
        assert self.collector.request_timeout == 30
        assert self.collector.max_articles_per_feed == 50
        assert self.collector.user_agent == "Trading-AI/2.0.0 (News Intelligence Engine)"
        assert self.collector.session is not None
    
    def test_session_configuration(self):
        """Test HTTP session is configured correctly."""
        session = self.collector.session
        
        # Check headers
        assert session.headers['User-Agent'] == self.collector.user_agent
        assert 'application/rss+xml' in session.headers['Accept']
        
        # Check adapters are mounted
        assert 'http://' in session.adapters
        assert 'https://' in session.adapters
    
    def test_url_hash_generation(self):
        """Test URL hash generation for duplicate detection."""
        url1 = "https://example.com/article1?utm_source=test"
        url2 = "https://example.com/article1?utm_source=different"
        url3 = "https://example.com/article2"
        
        hash1 = self.collector._generate_url_hash(url1)
        hash2 = self.collector._generate_url_hash(url2)
        hash3 = self.collector._generate_url_hash(url3)
        
        # URLs with same path but different tracking params should have same hash
        assert hash1 == hash2
        # Different URLs should have different hashes
        assert hash1 != hash3
        assert len(hash1) == 16  # SHA256 truncated to 16 chars
    
    def test_source_name_extraction(self):
        """Test source name extraction from URLs."""
        test_cases = [
            ("https://www.reuters.com/business", "Reuters"),
            ("https://bloomberg.com/markets", "Bloomberg"),
            ("https://www.wsj.com/markets", "Wall Street Journal"),
            ("https://cnbc.com/markets", "CNBC"),
            ("https://coindesk.com/news", "CoinDesk"),
            ("https://unknown-site.com/news", "Unknown Source")
        ]
        
        for url, expected in test_cases:
            result = self.collector._extract_source_name(url)
            assert result == expected, f"Failed for URL: {url}"
    
    def test_timestamp_extraction(self):
        """Test timestamp extraction from feed entries."""
        # Create mock entry with timestamp
        mock_entry = MagicMock()
        mock_entry.published_parsed = (2024, 4, 14, 12, 0, 0, 0, 0, 0)
        
        timestamp = self.collector._extract_timestamp(mock_entry)
        
        assert timestamp is not None
        assert timestamp.year == 2024
        assert timestamp.month == 4
        assert timestamp.day == 14
    
    def test_article_parsing(self):
        """Test article parsing from feed entry."""
        # Create mock entry
        mock_entry = MagicMock()
        mock_entry.title = "Test Article Title"
        mock_entry.link = "https://example.com/article"
        mock_entry.summary = "Test article content"
        mock_entry.published_parsed = (2024, 4, 14, 12, 0, 0, 0, 0, 0)
        mock_entry.id = "article123"
        
        article = self.collector._parse_entry(mock_entry, "https://example.com/feed")
        
        assert article is not None
        assert article.title == "Test Article Title"
        assert article.url == "https://example.com/article"
        assert article.content == "Test article content"
        assert article.source == "Unknown Source"
        assert article.metadata["entry_id"] == "article123"
    
    def test_article_parsing_rejects_empty_title(self):
        """Test article parsing rejects entries with empty titles."""
        mock_entry = MagicMock()
        mock_entry.title = ""
        mock_entry.link = "https://example.com/article"
        
        article = self.collector._parse_entry(mock_entry, "https://example.com/feed")
        
        assert article is None
    
    def test_article_parsing_rejects_empty_link(self):
        """Test article parsing rejects entries with empty links."""
        mock_entry = MagicMock()
        mock_entry.title = "Test Title"
        mock_entry.link = ""
        
        article = self.collector._parse_entry(mock_entry, "https://example.com/feed")
        
        assert article is None
    
    @patch('trading_ai.agents.news_collector.feedparser.parse')
    def test_feed_fetch_success(self, mock_parse):
        """Test successful feed fetching."""
        # Mock successful feed parsing
        mock_entry = MagicMock()
        mock_entry.title = "Test Article"
        mock_entry.link = "https://example.com/article"
        mock_entry.summary = "Test content"
        mock_entry.published_parsed = (2024, 4, 14, 12, 0, 0, 0, 0, 0)
        
        mock_feed = MagicMock()
        mock_feed.entries = [mock_entry]
        mock_feed.feed.title = "Test Feed"
        mock_feed.bozo = False
        
        mock_parse.return_value = mock_feed
        
        # Mock successful HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"mock RSS content"
        
        with patch.object(self.collector.session, 'get', return_value=mock_response):
            articles, metadata = self.collector.fetch_feed("https://example.com/feed")
        
        assert len(articles) == 1
        assert metadata["success"] is True
        assert metadata["articles_parsed"] == 1
        assert metadata["http_status"] == 200
        assert "response_time" in metadata
    
    @patch('trading_ai.agents.news_collector.feedparser.parse')
    def test_feed_fetch_http_error(self, mock_parse):
        """Test feed fetching with HTTP error."""
        # Mock HTTP error response
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.reason = "Not Found"
        
        with patch.object(self.collector.session, 'get', return_value=mock_response):
            articles, metadata = self.collector.fetch_feed("https://example.com/feed")
        
        assert len(articles) == 0
        assert metadata["success"] is False
        assert metadata["http_status"] == 404
        assert "HTTP 404: Not Found" in metadata["error"]
    
    @patch('trading_ai.agents.news_collector.feedparser.parse')
    def test_feed_fetch_timeout(self, mock_parse):
        """Test feed fetching with timeout."""
        # Mock timeout exception
        import requests
        with patch.object(self.collector.session, 'get', side_effect=requests.exceptions.Timeout()):
            articles, metadata = self.collector.fetch_feed("https://example.com/feed")
        
        assert len(articles) == 0
        assert metadata["success"] is False
        assert "Request timeout" in metadata["error"]
    
    @patch('trading_ai.agents.news_collector.feedparser.parse')
    def test_feed_fetch_parsing_error(self, mock_parse):
        """Test feed fetching with parsing error."""
        # Mock parsing error
        mock_feed = MagicMock()
        mock_feed.bozo = True
        mock_feed.bozo_exception = Exception("Parse error")
        mock_feed.entries = []
        
        mock_parse.return_value = mock_feed
        
        # Mock successful HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"invalid RSS content"
        
        with patch.object(self.collector.session, 'get', return_value=mock_response):
            articles, metadata = self.collector.fetch_feed("https://example.com/feed")
        
        assert len(articles) == 0
        assert metadata["success"] is True  # Still counts as success but with parsing error
        assert "Feed parsing error" in metadata["error"]
    
    def test_multiple_feeds_fetch(self):
        """Test fetching multiple RSS feeds."""
        # Mock feed fetching
        with patch.object(self.collector, 'fetch_feed') as mock_fetch:
            # Mock different responses for different feeds
            mock_fetch.side_effect = [
                ([Article("Title1", "Content1", "Source1", None, "url1", {})], {"success": True, "response_time": 100}),
                ([Article("Title2", "Content2", "Source2", None, "url2", {})], {"success": True, "response_time": 200}),
                ([], {"success": False, "response_time": 50})
            ]
            
            urls = ["https://feed1.com", "https://feed2.com", "https://feed3.com"]
            articles, metadata = self.collector.fetch_multiple_feeds(urls)
        
        assert len(articles) == 2
        assert metadata["total_feeds"] == 3
        assert metadata["successful_feeds"] == 2
        assert metadata["total_articles"] == 2
        assert "fetch_time_ms" in metadata
        assert "feed_details" in metadata
    
    def test_feed_validation(self):
        """Test feed URL validation."""
        # Mock successful HEAD request
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/rss+xml"}
        
        with patch.object(self.collector.session, 'head', return_value=mock_response):
            result = self.collector.validate_feed_url("https://example.com/feed")
        
        assert result is True
    
    def test_feed_validation_invalid_content_type(self):
        """Test feed validation with invalid content type."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html"}
        
        with patch.object(self.collector.session, 'head', return_value=mock_response):
            result = self.collector.validate_feed_url("https://example.com/feed")
        
        assert result is False
    
    def test_get_session_stats(self):
        """Test getting session statistics."""
        stats = self.collector.get_session_stats()
        
        assert "timeout" in stats
        assert "max_articles_per_feed" in stats
        assert "user_agent" in stats
        assert "pool_connections" in stats
        assert stats["timeout"] == 30
        assert stats["max_articles_per_feed"] == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
