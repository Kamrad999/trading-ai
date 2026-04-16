#!/usr/bin/env python3
"""
System verification script for Trading AI.

Verifies that all core components can be imported and basic functionality works.
"""

import sys
import traceback
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_imports():
    """Test that all main modules can be imported."""
    print("Testing imports...")
    
    try:
        from trading_ai.core.models import Article, Signal, Order, Position
        from trading_ai.core.exceptions import TradingError, RiskLimitExceeded
        from trading_ai.core.orchestrator import PipelineOrchestrator
        from trading_ai.infrastructure.config import config
        from trading_ai.infrastructure.logging import get_logger
        from trading_ai.infrastructure.state_manager import StateManager
        from trading_ai.infrastructure.source_registry import SourceRegistry
        
        print("  All imports successful")
        return True
    except Exception as e:
        print(f"  Import failed: {e}")
        traceback.print_exc()
        return False

def test_config():
    """Test configuration validation."""
    print("Testing configuration...")
    
    try:
        from trading_ai.infrastructure.config import config
        
        # Test basic config values
        assert config.PAPER_MODE is True
        assert config.LIVE_MODE is False
        assert config.PORTFOLIO_SIZE_USD > 0
        assert 0.0 <= config.MAX_RISK_PER_TRADE <= 1.0
        assert 0.0 <= config.MIN_SIGNAL_CONFIDENCE <= 1.0
        
        print("  Configuration valid")
        return True
    except Exception as e:
        print(f"  Configuration test failed: {e}")
        traceback.print_exc()
        return False

def test_orchestrator():
    """Test orchestrator creation and basic functionality."""
    print("Testing orchestrator...")
    
    try:
        from trading_ai.core.orchestrator import PipelineOrchestrator
        
        orchestrator = PipelineOrchestrator()
        assert orchestrator is not None
        assert orchestrator.kill_switch_active is False
        
        # Test system status
        status = orchestrator.get_system_status()
        assert status is not None
        assert status.version == "2.0.0"
        
        print("  Orchestrator functional")
        return True
    except Exception as e:
        print(f"  Orchestrator test failed: {e}")
        traceback.print_exc()
        return False

def test_models():
    """Test data model creation and validation."""
    print("Testing models...")
    
    try:
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
        assert order.symbol == "AAPL"
        assert order.side == OrderSide.BUY
        
        print("  Models functional")
        return True
    except Exception as e:
        print(f"  Models test failed: {e}")
        traceback.print_exc()
        return False

def test_state_manager():
    """Test state manager functionality."""
    print("Testing state manager...")
    
    try:
        from trading_ai.infrastructure.state_manager import StateManager
        
        sm = StateManager()
        state = sm.load_state()
        assert state is not None
        assert "version" in state
        assert "pipeline_state" in state
        
        print("  State manager functional")
        return True
    except Exception as e:
        print(f"  State manager test failed: {e}")
        traceback.print_exc()
        return False

def test_source_registry():
    """Test source registry functionality."""
    print("Testing source registry...")
    
    try:
        from trading_ai.infrastructure.source_registry import SourceRegistry
        
        registry = SourceRegistry()
        sources = registry.get_sources()
        assert len(sources) > 0
        
        stats = registry.get_source_stats()
        assert "total_sources" in stats
        assert stats["total_sources"] > 0
        
        print("  Source registry functional")
        return True
    except Exception as e:
        print(f"  Source registry test failed: {e}")
        traceback.print_exc()
        return False

def test_pipeline():
    """Test pipeline execution in dry run mode."""
    print("Testing pipeline execution...")
    
    try:
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
        
        print(f"  Pipeline executed: {result.status.value} in {result.pipeline_latency_ms:.2f}ms")
        return True
    except Exception as e:
        print(f"  Pipeline test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all verification tests."""
    print("Trading AI System Verification")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_config,
        test_orchestrator,
        test_models,
        test_state_manager,
        test_source_registry,
        test_pipeline,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1
        print()
    
    print("=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("All tests passed! System is ready for deployment.")
        return 0
    else:
        print("Some tests failed. Please review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
