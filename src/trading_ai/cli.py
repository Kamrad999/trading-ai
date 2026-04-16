"""
Command-line interface for Trading AI.

Provides easy access to common operations like running the pipeline,
checking system status, and managing configuration.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core.orchestrator import PipelineOrchestrator
from .infrastructure.config import config
from .infrastructure.logging import get_logger


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Trading AI - Institutional-Grade Trading Signal Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  trading-ai run                    # Run pipeline in paper mode
  trading-ai run --live             # Run pipeline in live mode
  trading-ai status                 # Check system status
  trading-ai config validate        # Validate configuration
  trading-ai config show            # Show current configuration
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run trading pipeline")
    run_parser.add_argument(
        "--live", action="store_true", help="Run in live trading mode"
    )
    run_parser.add_argument(
        "--dry-run", action="store_true", default=True, help="Run in dry-run mode"
    )
    run_parser.add_argument(
        "--pipeline-id", type=str, help="Specific pipeline ID to run"
    )
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Check system status")
    status_parser.add_argument(
        "--verbose", action="store_true", help="Verbose status output"
    )
    
    # Config command
    config_parser = subparsers.add_parser("config", help="Configuration management")
    config_subparsers = config_parser.add_subparsers(dest="config_action")
    
    config_subparsers.add_parser("validate", help="Validate configuration")
    config_subparsers.add_parser("show", help="Show current configuration")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Run tests")
    test_parser.add_argument(
        "--unit", action="store_true", help="Run unit tests only"
    )
    test_parser.add_argument(
        "--integration", action="store_true", help="Run integration tests only"
    )
    test_parser.add_argument(
        "--smoke", action="store_true", help="Run smoke tests only"
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        if args.command == "run":
            return run_pipeline(args)
        elif args.command == "status":
            return show_status(args)
        elif args.command == "config":
            return handle_config(args)
        elif args.command == "test":
            return run_tests(args)
        else:
            parser.print_help()
            return 1
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 130
    except Exception as e:
        print(f"Error: {e}")
        return 1


def run_pipeline(args: argparse.Namespace) -> int:
    """Run the trading pipeline."""
    logger = get_logger("cli")
    
    if args.live and not config.LIVE_MODE:
        print("Error: Live mode not enabled in configuration")
        return 1
    
    if args.live:
        print("WARNING: Running in LIVE trading mode")
        confirm = input("Type 'LIVE' to confirm: ")
        if confirm != "LIVE":
            print("Live trading cancelled")
            return 1
    
    print(f"Starting Trading AI pipeline (mode: {'LIVE' if args.live else 'PAPER'})")
    
    try:
        orchestrator = PipelineOrchestrator()
        result = orchestrator.run_pipeline(dry_run=args.dry_run)
        
        print(f"\nPipeline completed: {result.status.value}")
        print(f"Articles processed: {result.articles_processed}")
        print(f"Signals generated: {result.signals_generated}")
        print(f"Orders sent: {result.orders_sent}")
        print(f"Alerts sent: {result.alerts_sent}")
        print(f"Latency: {result.pipeline_latency_ms:.2f}ms")
        
        if result.status.value == "SUCCESS":
            return 0
        else:
            return 1
            
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        print(f"Pipeline failed: {e}")
        return 1


def show_status(args: argparse.Namespace) -> int:
    """Show system status."""
    try:
        orchestrator = PipelineOrchestrator()
        status = orchestrator.get_system_status()
        
        print(f"Trading AI Status")
        print(f"Version: {status.version}")
        print(f"Kill Switch: {'ACTIVE' if status.kill_switch_active else 'INACTIVE'}")
        print(f"Market Session: {status.market_session}")
        print(f"Portfolio Exposure: {status.portfolio_exposure_pct:.2%}")
        print(f"Daily Drawdown: {status.daily_drawdown_pct:.2%}")
        print(f"Timestamp: {status.timestamp}")
        
        if args.verbose:
            print(f"\nCircuit Breakers:")
            for name, state in status.circuit_states.items():
                print(f"  {name}: {state}")
        
        return 0
        
    except Exception as e:
        print(f"Error getting status: {e}")
        return 1


def handle_config(args: argparse.Namespace) -> int:
    """Handle configuration commands."""
    if args.config_action == "validate":
        try:
            config._validate_config()
            print("Configuration is valid")
            return 0
        except Exception as e:
            print(f"Configuration validation failed: {e}")
            return 1
    
    elif args.config_action == "show":
        print("Current Configuration:")
        print(f"Paper Mode: {config.PAPER_MODE}")
        print(f"Live Mode: {config.LIVE_MODE}")
        print(f"Default Broker: {config.DEFAULT_BROKER}")
        print(f"Portfolio Size: ${config.PORTFOLIO_SIZE_USD:,.2f}")
        print(f"Max Risk per Trade: {config.MAX_RISK_PER_TRADE:.2%}")
        print(f"Daily Loss Limit: {config.DAILY_LOSS_LIMIT:.2%}")
        print(f"Min Signal Confidence: {config.MIN_SIGNAL_CONFIDENCE:.2%}")
        print(f"Debug Mode: {config.DEBUG}")
        return 0
    
    else:
        print("No configuration action specified")
        return 1


def run_tests(args: argparse.Namespace) -> int:
    """Run tests."""
    import subprocess
    
    test_args = ["python", "-m", "pytest"]
    
    if args.unit:
        test_args.extend(["-m", "unit"])
    elif args.integration:
        test_args.extend(["-m", "integration"])
    elif args.smoke:
        test_args.extend(["-m", "smoke"])
    else:
        test_args.append("tests/")
    
    try:
        result = subprocess.run(test_args, cwd=Path.cwd())
        return result.returncode
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
