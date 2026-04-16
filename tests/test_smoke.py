"""
Smoke tests for Trading AI.

Basic tests to verify the system can start up and core components work.
"""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_imports():
    """Test that all main modules can be imported."""
    from trading_ai.core.models import Article, Signal, Order, Position
    from trading_ai.core.exceptions import TradingError, RiskLimitExceeded
    from trading_ai.core.orchestrator import PipelineOrchestrator
    from trading_ai.infrastructure.config import Config
    from trading_ai.infrastructure.logging import get_logger
    from trading_ai.infrastructure.state_manager import StateManager
    from trading_ai.infrastructure.source_registry import SourceRegistry
    
    # Test that classes can be instantiated
    assert Article is not None
    assert Signal is not None
    assert Order is not None
    assert Position is not None
    assert TradingError is not None
    assert RiskLimitExceeded is not None
    assert PipelineOrchestrator is not None
    assert Config is not None
    assert get_logger is not None
    assert StateManager is not None
    assert SourceRegistry is not None


@pytest.mark.smoke
def test_config_validation():
    """Test configuration validation."""
    from trading_ai.infrastructure.config import config
    
    # Test that config loads and validates
    assert config.PAPER_MODE is True
    assert config.LIVE_MODE is False
    assert config.PORTFOLIO_SIZE_USD > 0
    assert 0.0 <= config.MAX_RISK_PER_TRADE <= 1.0
    assert 0.0 <= config.MIN_SIGNAL_CONFIDENCE <= 1.0


@pytest.mark.smoke
def test_orchestrator_creation():
    """Test that orchestrator can be created."""
    from trading_ai.core.orchestrator import PipelineOrchestrator
    
    orchestrator = PipelineOrchestrator()
    assert orchestrator is not None
    assert orchestrator.kill_switch_active is False
    
    # Test system status
    status = orchestrator.get_system_status()
    assert status is not None
    assert status.version == "2.0.0"
    assert status.market_session in ["PREMARKET", "REGULAR", "AFTER_HOURS", "CLOSED", "CRYPTO_24_7"]


@pytest.mark.smoke
def test_logging():
    """Test logging functionality."""
    from trading_ai.infrastructure.logging import get_logger
    
    logger = get_logger("test")
    assert logger is not None
    
    # Test that logging methods exist
    assert hasattr(logger, 'info')
    assert hasattr(logger, 'error')
    assert hasattr(logger, 'debug')
    assert hasattr(logger, 'warning')


@pytest.mark.smoke
def test_state_manager():
    """Test state manager functionality."""
    from trading_ai.infrastructure.state_manager import StateManager
    
    sm = StateManager()
    assert sm is not None
    
    # Test empty state creation
    state = sm.load_state()
    assert state is not None
    assert "version" in state
    assert "pipeline_state" in state
    assert "positions" in state
    assert "orders" in state


@pytest.mark.smoke
def test_source_registry():
    """Test source registry functionality."""
    from trading_ai.infrastructure.source_registry import SourceRegistry, RSSSource
    
    registry = SourceRegistry()
    assert registry is not None
    
    # Test that default sources are loaded
    sources = registry.get_sources()
    assert len(sources) > 0
    
    # Test source categories
    categorized = registry.get_sources_by_category()
    assert len(categorized) > 0
    
    # Test source stats
    stats = registry.get_source_stats()
    assert "total_sources" in stats
    assert "enabled_sources" in stats


@pytest.mark.smoke
def test_models():
    """Test data model creation and validation."""
    from trading_ai.core.models import Article, Signal, Order, Position, SignalDirection, OrderSide
    from datetime import datetime, timezone
    
    # Test Article creation
    article = Article(
        title="Test Article",
        content="Test content",
        source="Test Source",
        timestamp=datetime.now(timezone.utc),
        url="https://example.com"
    )
    assert article is not None
    assert article.title == "Test Article"
    
    # Test Signal creation
    signal = Signal(
        direction=SignalDirection.BUY,
        confidence=0.8,
        urgency="HIGH",
        market_regime="RISK_ON",
        position_size=0.1,
        execution_priority=1
    )
    assert signal is not None
    assert signal.direction == SignalDirection.BUY
    assert signal.confidence == 0.8
    
    # Test Order creation
    order = Order(
        symbol="AAPL",
        side=OrderSide.BUY,
        quantity=100,
        order_type="MARKET",
        time_in_force="DAY"
    )
    assert order is not None
    assert order.symbol == "AAPL"
    assert order.side == OrderSide.BUY
    
    # Test Position creation
    position = Position(
        symbol="AAPL",
        quantity=100,
        avg_price=150.0,
        current_price=155.0,
        unrealized_pnl=500.0
    )
    assert position is not None
    assert position.symbol == "AAPL"
    assert position.unrealized_pnl == 500.0


@pytest.mark.smoke
def test_exceptions():
    """Test exception hierarchy and utilities."""
    from trading_ai.core.exceptions import (
        TradingError, RiskLimitExceeded, BrokerError, 
        ValidationError, ConfigurationError,
        format_error, is_recoverable_error, is_critical_error
    )
    
    # Test exception creation
    error = TradingError("Test error", "TEST_ERROR")
    assert error.error_code == "TEST_ERROR"
    assert str(error) == "[TEST_ERROR] Test error"
    
    # Test specific exceptions
    risk_error = RiskLimitExceeded("Risk limit exceeded", "test_limit", 0.05, 0.02)
    assert risk_error.limit_type == "test_limit"
    assert risk_error.current_value == 0.05
    assert risk_error.limit_value == 0.02
    
    # Test utility functions
    formatted = format_error(risk_error)
    assert "type" in formatted
    assert "message" in formatted
    assert "error_code" in formatted
    
    assert not is_recoverable_error(risk_error)
    assert not is_critical_error(risk_error)


@pytest.mark.smoke
def test_pipeline_dry_run():
    """Test pipeline execution in dry run mode."""
    from trading_ai.core.orchestrator import PipelineOrchestrator
    
    orchestrator = PipelineOrchestrator()
    result = orchestrator.run_pipeline(dry_run=True)
    
    assert result is not None
    assert result.status.value in ["SUCCESS", "DEGRADED", "FAILED"]
    assert result.articles_processed >= 0
    assert result.signals_generated >= 0
    assert result.orders_sent >= 0
    assert result.alerts_sent >= 0
    assert result.pipeline_latency_ms >= 0


if __name__ == "__main__":
    # Run smoke tests directly
    pytest.main([__file__, "-v", "-m", "smoke"])
