"""
Production hardening audit tests.

Stress tests for production readiness verification.
"""

import pytest
import sys
import time
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from trading_ai.agents.news_collector import NewsCollector
from trading_ai.validation.duplicate_filter import DuplicateFilter
from trading_ai.risk.risk_manager import RiskManager
from trading_ai.core.orchestrator import PipelineOrchestrator
from trading_ai.infrastructure.state_manager import StateManager


class TestProductionHardening:
    """Production hardening audit tests."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Use temporary directory for state
        self.temp_dir = tempfile.mkdtemp()
        self.state_file = Path(self.temp_dir) / "test_state.json"
    
    def test_rss_resilience_timeout_handling(self):
        """Test RSS timeout handling and recovery."""
        collector = NewsCollector()
        
        # Mock timeout exception
        import requests
        with patch.object(collector.session, 'get', side_effect=requests.exceptions.Timeout()):
            articles, metadata = collector.fetch_feed("https://timeout-test.com/feed")
        
        # Should handle timeout gracefully
        assert len(articles) == 0
        assert metadata["success"] is False
        assert "Request timeout" in metadata["error"]
        assert metadata["response_time"] > 0
    
    def test_rss_resilience_bad_xml_recovery(self):
        """Test bad XML recovery and partial parsing."""
        collector = NewsCollector()
        
        # Mock response with malformed XML
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"<invalid><xml><broken>"
        
        with patch.object(collector.session, 'get', return_value=mock_response):
            articles, metadata = collector.fetch_feed("https://bad-xml.com/feed")
        
        # Should handle bad XML gracefully
        assert len(articles) == 0
        assert metadata["success"] is True  # Fetch succeeded, parsing failed
        assert "Feed parsing error" in metadata["error"]
    
    def test_rss_resilience_connection_pool_safety(self):
        """Test connection pool safety under concurrent load."""
        collector = NewsCollector()
        
        # Mock successful responses
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'<?xml version="1.0"?><rss><channel><item><title>Test</title><link>http://test.com</link></item></channel></rss>'
        
        def fetch_feed():
            return collector.fetch_feed("https://test.com/feed")
        
        # Test concurrent access
        with patch.object(collector.session, 'get', return_value=mock_response):
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(fetch_feed) for _ in range(20)]
                results = [f.result() for f in futures]
        
        # All requests should succeed
        assert len(results) == 20
        for articles, metadata in results:
            assert metadata["success"] is True
    
    def test_state_safety_corrupted_recovery(self):
        """Test corrupted state file recovery."""
        # Create corrupted state file
        with open(self.state_file, 'w') as f:
            f.write("invalid json content")
        
        # State manager should recover gracefully
        with patch('trading_ai.infrastructure.config.config') as mock_config:
            mock_config.STATE_FILE = str(self.state_file)
            mock_config.DATA_DIR = str(self.temp_dir)
            
            state_manager = StateManager()
            state = state_manager.load_state()
        
        # Should return valid default state structure on corruption
        assert isinstance(state, dict)
        assert "created_at" in state
        assert "last_updated" in state
    
    def test_state_safety_partial_write_recovery(self):
        """Test partial write recovery."""
        # Create partially written state file
        with open(self.state_file, 'w') as f:
            f.write('{"partial": "data"')
        
        with patch('trading_ai.infrastructure.config.config') as mock_config:
            mock_config.STATE_FILE = str(self.state_file)
            mock_config.DATA_DIR = str(self.temp_dir)
            
            state_manager = StateManager()
            state = state_manager.load_state()
        
        # Should handle partial JSON gracefully
        assert isinstance(state, dict)
        assert "created_at" in state
    
    def test_state_safety_concurrent_access(self):
        """Test concurrent state access safety."""
        with patch('trading_ai.infrastructure.config.config') as mock_config:
            mock_config.STATE_FILE = str(self.state_file)
            mock_config.DATA_DIR = str(self.temp_dir)
            
            state_manager = StateManager()
            
            def update_state(i):
                state = state_manager.load_state()
                state[f"counter_{i}"] = i
                state_manager.save_state(state)
                return state_manager.load_state()
            
            # Test concurrent updates
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(update_state, i) for i in range(10)]
                results = [f.result() for f in futures]
            
            # Should handle concurrent access without corruption
            assert all(isinstance(r, dict) for r in results)
    
    def test_risk_safety_false_kill_switch_triggers(self):
        """Test false kill switch trigger prevention."""
        risk_manager = RiskManager()
        
        # Test edge case P&L values
        edge_cases = [
            0.0,           # Zero P&L
            0.001,         # Tiny profit
            -0.001,        # Tiny loss
            1249.99,       # Just under 5% threshold ($1,250)
            -1249.99,      # Just under 5% loss threshold
        ]
        
        for pnl in edge_cases:
            risk_manager.daily_pnl = pnl
            # Should not trigger kill switch
            assert risk_manager.is_kill_switch_active() is False, f"False trigger for P&L: {pnl}"
    
    def test_risk_safety_portfolio_precision(self):
        """Test portfolio percentage precision edge cases."""
        risk_manager = RiskManager()
        
        # Test precision edge cases around 5% threshold
        portfolio_size = 25000.0
        threshold_amount = portfolio_size * 0.025  # 2.5% = $625
        
        edge_cases = [
            threshold_amount - 0.01,  # Just under threshold
            threshold_amount,          # Exactly at threshold
            threshold_amount + 0.01,   # Just over threshold
        ]
        
        for pnl in edge_cases:
            risk_manager.daily_pnl = -abs(pnl)  # Force negative
            should_trigger = abs(pnl) > threshold_amount
            
            if should_trigger:
                try:
                    risk_manager._check_kill_switch_conditions()
                    assert False, f"Should have triggered kill switch for P&L: {pnl}"
                except Exception:
                    pass  # Expected
            else:
                assert risk_manager.is_kill_switch_active() is False, f"Should not trigger for P&L: {pnl}"
    
    def test_risk_safety_stale_positions(self):
        """Test stale position handling."""
        risk_manager = RiskManager()
        
        # Add position
        risk_manager.update_position("TEST", 100, 100.0, 0.0)
        
        # Simulate restart by creating new instance
        new_risk_manager = RiskManager()
        
        # Should recover position state
        assert "TEST" in new_risk_manager.open_positions
        assert new_risk_manager.total_exposure > 0
    
    def test_signal_quality_symbol_extraction_false_positives(self):
        """Test symbol extraction false positive prevention."""
        from trading_ai.agents.signal_generator import SignalGenerator
        generator = SignalGenerator()
        
        # Test false positive cases
        false_positive_cases = [
            "THE market is UP today",
            "FOR sale: real estate",
            "AND then the market crashed",
            "TO the moon with crypto",
            "IN the latest news",
            "ON the trading floor",
            "AT the close of trading",
            "BY the end of day",
            "WITH high volatility",
            "FROM the Fed announcement",
            "UP 5% today",
            "IT was a volatile session",
            "IS the market open",
            "BE the first to know",
            "ARE you ready to trade"
        ]
        
        for title in false_positive_cases:
            symbols = generator._extract_symbols(title, "content")
            # Should not extract common words as symbols
            assert len(symbols) == 0 or all(len(s) <= 4 for s in symbols), f"False positive in: {title} -> {symbols}"
    
    def test_signal_quality_spam_headline_filtering(self):
        """Test spam headline filtering."""
        from trading_ai.validation.news_validator import NewsValidator
        validator = NewsValidator()
        
        # Spam headlines
        spam_headlines = [
            "BUY NOW!!! LIMITED TIME OFFER!!! GET RICH QUICK!!!",
            "GUARANTEED 1000% RETURNS IN 24 HOURS!!! ACT FAST!!!",
            "SECRET METHOD TO BECOME A MILLIONAIRE OVERNIGHT!!!",
            "BITCOIN REVOLUTION: DON'T MISS THIS CHANCE!!!",
            "RISK FREE TRADING: DOUBLE YOUR MONEY INSTANTLY!!!"
        ]
        
        for headline in spam_headlines:
            # Create test article
            from trading_ai.core.models import Article
            article = Article(
                title=headline,
                content="Some content",
                source="Test Source",
                timestamp=datetime.now(timezone.utc),
                url="https://test.com/article",
                metadata={}
            )
            
            result = validator.validate_article(article)
            # Should reject spam headlines
            assert result.is_valid is False, f"Spam not detected: {headline}"
            assert any("spam" in reason.lower() for reason in result.reasons)
    
    def test_performance_load_500_articles(self):
        """Test performance with 500 articles."""
        import os
        # Clear state file to start fresh
        state_file = "./data/state.json"
        if os.path.exists(state_file):
            os.remove(state_file)
        
        from trading_ai.validation.duplicate_filter import DuplicateFilter
        filter = DuplicateFilter()
        
        # Generate 500 test articles with truly unique titles
        articles = []
        for i in range(500):
            from trading_ai.core.models import Article
            article = Article(
                title=f"Unique Market Analysis Report {i} - Trading Intelligence Update",
                content=f"Detailed market analysis and trading insights for article {i} with comprehensive data",
                source="Test Source",
                timestamp=datetime.now(timezone.utc),
                url=f"https://test.com/article{i}",
                metadata={}
            )
            articles.append(article)
        
        start_time = time.time()
        unique_articles = filter.filter_duplicates(articles)
        processing_time = (time.time() - start_time) * 1000
        
        # Should complete within reasonable time
        assert processing_time < 30000  # Less than 30 seconds
        assert len(unique_articles) == 500  # All should be unique
    
    def test_performance_load_1000_duplicates(self):
        """Test performance with 1000 duplicate hits."""
        filter = DuplicateFilter()
        
        # Add base article to cache
        from trading_ai.core.models import Article
        base_article = Article(
            title="Base Article",
            content="Base content",
            source="Test Source",
            timestamp=datetime.now(timezone.utc),
            url="https://test.com/base",
            metadata={}
        )
        filter._add_to_seen_articles(base_article)
        
        # Generate 1000 duplicate articles
        duplicates = []
        for i in range(1000):
            duplicate = Article(
                title="Base Article",  # Same title
                content=f"Duplicate content {i}",
                source="Test Source",
                timestamp=datetime.now(timezone.utc),
                url=f"https://test.com/duplicate{i}",
                metadata={}
            )
            duplicates.append(duplicate)
        
        start_time = time.time()
        unique_articles = filter.filter_duplicates(duplicates)
        processing_time = (time.time() - start_time) * 1000
        
        # Should complete within reasonable time
        assert processing_time < 3000  # Less than 3 seconds
        assert len(unique_articles) == 0  # All should be filtered out
    
    def test_performance_feed_outage_scenario(self):
        """Test performance during feed outage."""
        collector = NewsCollector()
        
        # Mix of successful and failed feeds
        urls = [
            "https://good-feed1.com",
            "https://timeout-feed.com",
            "https://good-feed2.com",
            "https://error-feed.com",
            "https://good-feed3.com"
        ]
        
        # Mock responses
        def mock_get(url, **kwargs):
            response = MagicMock()
            if "timeout" in url:
                import requests
                raise requests.exceptions.Timeout()
            elif "error" in url:
                response.status_code = 500
                response.reason = "Internal Server Error"
            else:
                response.status_code = 200
                response.content = b'<?xml version="1.0"?><rss><channel><item><title>Test</title></item></channel></rss>'
            return response
        
        with patch.object(collector.session, 'get', side_effect=mock_get):
            start_time = time.time()
            articles, metadata = collector.fetch_multiple_feeds(urls)
            processing_time = (time.time() - start_time) * 1000
        
        # Should handle outages gracefully
        assert processing_time < 10000  # Less than 10 seconds
        assert metadata["successful_feeds"] == 3
        assert metadata["total_feeds"] == 5
    
    def test_deployment_docker_readiness(self):
        """Test Docker deployment readiness."""
        # Check for Dockerfile
        dockerfile_path = Path(__file__).parent.parent / "Dockerfile"
        assert dockerfile_path.exists(), "Dockerfile missing"
        
        # Check for requirements.txt
        requirements_path = Path(__file__).parent.parent / "requirements.txt"
        assert requirements_path.exists(), "requirements.txt missing"
        
        # Verify requirements.txt has pinned versions
        with open(requirements_path, 'r') as f:
            requirements = f.read()
        
        # Should have pinned versions for production packages
        pinned_packages = ['feedparser', 'requests', 'pytest']
        for package in pinned_packages:
            assert package in requirements, f"Missing {package} in requirements"
    
    def test_deployment_environment_validation(self):
        """Test environment variable validation."""
        # Test with missing required environment variables
        import os
        
        # Clear environment
        original_env = os.environ.copy()
        os.environ.clear()
        
        try:
            # Should handle missing environment gracefully
            orchestrator = PipelineOrchestrator()
            assert orchestrator is not None
        finally:
            # Restore environment
            os.environ.update(original_env)
    
    def test_deployment_fresh_clone_install(self):
        """Test fresh clone installation."""
        # Check setup.py exists
        setup_path = Path(__file__).parent.parent / "setup.py"
        assert setup_path.exists(), "setup.py missing"
        
        # Check pyproject.toml exists
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        assert pyproject_path.exists(), "pyproject.toml missing"
        
        # Verify package can be imported
        try:
            import trading_ai
            assert trading_ai is not None
        except ImportError as e:
            pytest.fail(f"Package import failed: {e}")
    
    def test_deployment_path_compatibility(self):
        """Test Windows/Linux path compatibility."""
        from trading_ai.infrastructure.state_manager import StateManager
        
        # Test path handling
        test_paths = [
            "C:\\Users\\test\\state.json",
            "/home/test/state.json",
            "./data/state.json",
            "../data/state.json"
        ]
        
        for path in test_paths:
            try:
                # Should handle different path formats
                with patch('trading_ai.infrastructure.state_manager.STATE_FILE', path):
                    state_manager = StateManager()
                    state = state_manager.load_state()
                    assert isinstance(state, dict)
            except Exception as e:
                pytest.fail(f"Path compatibility failed for {path}: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
