#!/usr/bin/env python3
"""
Pipeline execution script for Trading AI.

Provides a simple way to run the trading pipeline with various options.
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from trading_ai.core.orchestrator import PipelineOrchestrator
from trading_ai.infrastructure.config import config
from trading_ai.infrastructure.logging import get_logger


def main():
    """Main pipeline execution function."""
    logger = get_logger("pipeline_runner")
    
    print("Trading AI Pipeline Runner")
    print("=" * 50)
    
    # Check configuration
    print(f"Mode: {'LIVE' if config.LIVE_MODE else 'PAPER'}")
    print(f"Default Broker: {config.DEFAULT_BROKER}")
    print(f"Portfolio Size: ${config.PORTFOLIO_SIZE_USD:,.2f}")
    print(f"Max Risk per Trade: {config.MAX_RISK_PER_TRADE:.2%}")
    print()
    
    if config.LIVE_MODE:
        print("WARNING: Running in LIVE trading mode!")
        confirm = input("Type 'LIVE' to confirm: ")
        if confirm != "LIVE":
            print("Live trading cancelled")
            return 1
    
    try:
        print("Starting pipeline execution...")
        orchestrator = PipelineOrchestrator()
        
        # Run pipeline
        result = orchestrator.run_pipeline(dry_run=config.PAPER_MODE)
        
        print("\nPipeline Results:")
        print(f"Status: {result.status.value}")
        print(f"Articles Processed: {result.articles_processed}")
        print(f"Signals Generated: {result.signals_generated}")
        print(f"Orders Sent: {result.orders_sent}")
        print(f"Alerts Sent: {result.alerts_sent}")
        print(f"Pipeline Latency: {result.pipeline_latency_ms:.2f}ms")
        
        if result.status.value == "SUCCESS":
            print("\nPipeline completed successfully!")
            return 0
        else:
            print(f"\nPipeline completed with status: {result.status.value}")
            return 1
            
    except KeyboardInterrupt:
        print("\nPipeline execution cancelled by user")
        return 130
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        print(f"Pipeline execution failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
