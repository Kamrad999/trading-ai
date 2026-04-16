#!/usr/bin/env python3
"""
Production health check script for Trading AI.

Validates system health and readiness for production deployment.
"""

import sys
import os
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from trading_ai.infrastructure.env_validator import validate_environment
from trading_ai.core.orchestrator import PipelineOrchestrator
from trading_ai.infrastructure.state_manager import StateManager


def check_environment() -> bool:
    """Check environment configuration."""
    print("Checking environment configuration...")
    try:
        config = validate_environment()
        print("Environment validation: PASSED")
        return True
    except Exception as e:
        print(f"Environment validation: FAILED - {e}")
        return False


def check_imports() -> bool:
    """Check critical imports."""
    print("Checking critical imports...")
    try:
        from trading_ai.core.orchestrator import PipelineOrchestrator
        from trading_ai.agents.news_collector import NewsCollector
        from trading_ai.validation.duplicate_filter import DuplicateFilter
        from trading_ai.risk.risk_manager import RiskManager
        from trading_ai.monitoring.performance_tracker import PerformanceTracker
        print("Import validation: PASSED")
        return True
    except Exception as e:
        print(f"Import validation: FAILED - {e}")
        return False


def check_state_manager() -> bool:
    """Check state manager functionality."""
    print("Checking state manager...")
    try:
        state_manager = StateManager()
        
        # Test state save/load
        test_state = {"health_check": True, "timestamp": time.time()}
        state_manager.save_state(test_state)
        
        loaded_state = state_manager.load_state()
        assert loaded_state["health_check"] == True
        
        print("State manager validation: PASSED")
        return True
    except Exception as e:
        print(f"State manager validation: FAILED - {e}")
        return False


def check_orchestrator() -> bool:
    """Check orchestrator initialization."""
    print("Checking orchestrator...")
    try:
        orchestrator = PipelineOrchestrator()
        
        # Test system status
        status = orchestrator.get_system_status()
        assert hasattr(status, 'portfolio_exposure_pct')
        assert hasattr(status, 'daily_drawdown_pct')
        assert hasattr(status, 'kill_switch_active')
        
        print("Orchestrator validation: PASSED")
        return True
    except Exception as e:
        print(f"Orchestrator validation: FAILED - {e}")
        return False


def check_pipeline_dry_run() -> bool:
    """Check pipeline dry run execution."""
    print("Checking pipeline dry run...")
    try:
        orchestrator = PipelineOrchestrator()
        
        # Run dry run
        result = orchestrator.run_pipeline(dry_run=True)
        
        assert result is not None
        assert result.success is True
        assert result.pipeline_id is not None
        
        print("Pipeline dry run validation: PASSED")
        return True
    except Exception as e:
        print(f"Pipeline dry run validation: FAILED - {e}")
        return False


def check_data_directories() -> bool:
    """Check data directories exist and are writable."""
    print("Checking data directories...")
    try:
        config = validate_environment()
        data_dir = Path(config["TRADING_AI_DATA_DIR"])
        state_file = Path(config["TRADING_AI_STATE_FILE"])
        
        # Check data directory
        if not data_dir.exists():
            data_dir.mkdir(parents=True, exist_ok=True)
        
        # Test write permissions
        test_file = data_dir / "health_check_test"
        test_file.write_text("test")
        test_file.unlink()
        
        # Check state file directory
        state_dir = state_file.parent
        if not state_dir.exists():
            state_dir.mkdir(parents=True, exist_ok=True)
        
        print("Data directories validation: PASSED")
        return True
    except Exception as e:
        print(f"Data directories validation: FAILED - {e}")
        return False


def main() -> int:
    """Main health check function."""
    print("Trading AI Production Health Check")
    print("=" * 40)
    
    checks = [
        ("Environment", check_environment),
        ("Imports", check_imports),
        ("Data Directories", check_data_directories),
        ("State Manager", check_state_manager),
        ("Orchestrator", check_orchestrator),
        ("Pipeline Dry Run", check_pipeline_dry_run),
    ]
    
    passed = 0
    total = len(checks)
    
    for check_name, check_func in checks:
        print(f"\n[{passed + 1}/{total}] {check_name}")
        if check_func():
            passed += 1
        else:
            print(f"Health check FAILED at {check_name}")
            return 1
    
    print(f"\nHealth Check Summary: {passed}/{total} checks passed")
    
    if passed == total:
        print("All health checks PASSED - System ready for production!")
        return 0
    else:
        print("Some health checks FAILED - System not ready for production!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
