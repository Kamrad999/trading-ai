"""
Logging infrastructure for the Trading AI system.

Provides structured logging with correlation IDs, performance tracking,
and integration with monitoring systems.
"""

from __future__ import annotations

import logging
import sys
import time
from datetime import datetime
from typing import Any, Dict, Optional
from contextlib import contextmanager

from .config import config


class TradingLogger:
    """Enhanced logger with correlation tracking and performance metrics."""
    
    def __init__(self, name: str = "trading_ai") -> None:
        """Initialize logger with structured formatting."""
        self.logger = logging.getLogger(name)
        self._setup_logger()
        self._correlation_id: Optional[str] = None
    
    def _setup_logger(self) -> None:
        """Configure logger with appropriate handlers and formatting."""
        if self.logger.handlers:
            return
        
        self.logger.setLevel(
            logging.DEBUG if config.DEBUG else logging.INFO
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG if config.DEBUG else logging.INFO)
        
        # File handler
        from pathlib import Path
        Path(config.LOG_DIR).mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(config.PERFORMANCE_LOG_FILE)
        file_handler.setLevel(logging.INFO)
        
        # Formatters
        console_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        file_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s [%(correlation_id)s]: %(message)s | %(extra)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        console_handler.setFormatter(console_formatter)
        file_handler.setFormatter(file_formatter)
        
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
    
    def set_correlation_id(self, correlation_id: str) -> None:
        """Set correlation ID for request tracking."""
        self._correlation_id = correlation_id
    
    def _log_with_context(self, level: int, message: str, **kwargs: Any) -> None:
        """Log message with correlation context."""
        extra = {
            "correlation_id": self._correlation_id or "none",
            "extra": str(kwargs) if kwargs else ""
        }
        self.logger.log(level, message, extra=extra)
    
    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        self._log_with_context(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        self._log_with_context(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        self._log_with_context(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        self._log_with_context(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical message."""
        self._log_with_context(logging.CRITICAL, message, **kwargs)
    
    def log_trade(self, trade_data: Dict[str, Any]) -> None:
        """Log trade execution with structured data."""
        self.info("Trade executed", **trade_data)
    
    def log_signal(self, signal_data: Dict[str, Any]) -> None:
        """Log signal generation with structured data."""
        self.info("Signal generated", **signal_data)
    
    def log_pipeline_start(self, pipeline_id: str, stage_count: int) -> None:
        """Log pipeline execution start."""
        self.info(
            f"Pipeline started: {pipeline_id}",
            pipeline_id=pipeline_id,
            stage_count=stage_count
        )
    
    def log_pipeline_complete(self, pipeline_id: str, duration_ms: float, status: str) -> None:
        """Log pipeline execution completion."""
        self.info(
            f"Pipeline completed: {pipeline_id}",
            pipeline_id=pipeline_id,
            duration_ms=duration_ms,
            status=status
        )
    
    def log_stage_start(self, stage: str, pipeline_id: str) -> None:
        """Log pipeline stage start."""
        self.debug(
            f"Stage started: {stage}",
            stage=stage,
            pipeline_id=pipeline_id
        )
    
    def log_stage_complete(self, stage: str, pipeline_id: str, duration_ms: float, success: bool) -> None:
        """Log pipeline stage completion."""
        self.debug(
            f"Stage completed: {stage}",
            stage=stage,
            pipeline_id=pipeline_id,
            duration_ms=duration_ms,
            success=success
        )
    
    def log_risk_event(self, risk_type: str, details: Dict[str, Any]) -> None:
        """Log risk management event."""
        self.warning(
            f"Risk event: {risk_type}",
            risk_type=risk_type,
            **details
        )
    
    def log_broker_event(self, broker: str, event_type: str, details: Dict[str, Any]) -> None:
        """Log broker-related event."""
        self.info(
            f"Broker event: {broker} - {event_type}",
            broker=broker,
            event_type=event_type,
            **details
        )
    
    def log_performance(self, metrics: Dict[str, Any]) -> None:
        """Log performance metrics."""
        self.info("Performance metrics", **metrics)
    
    def log_error_with_traceback(self, error: Exception, context: Dict[str, Any]) -> None:
        """Log error with full traceback and context."""
        import traceback
        
        self.error(
            f"Error occurred: {type(error).__name__}: {error}",
            error_type=type(error).__name__,
            error_message=str(error),
            context=context,
            traceback=traceback.format_exc()
        )
    
    @contextmanager
    def performance_context(self, operation: str):
        """Context manager for performance tracking."""
        start_time = time.time()
        try:
            yield
        finally:
            duration_ms = (time.time() - start_time) * 1000
            self.debug(
                f"Operation completed: {operation}",
                operation=operation,
                duration_ms=duration_ms
            )
    
    @contextmanager
    def pipeline_context(self, pipeline_id: str):
        """Context manager for pipeline execution."""
        self.set_correlation_id(pipeline_id)
        start_time = time.time()
        
        try:
            self.log_pipeline_start(pipeline_id, 13)  # 13 stages
            yield
            duration_ms = (time.time() - start_time) * 1000
            self.log_pipeline_complete(pipeline_id, duration_ms, "SUCCESS")
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.log_pipeline_complete(pipeline_id, duration_ms, "FAILED")
            self.log_error_with_traceback(e, {"pipeline_id": pipeline_id})
            raise
        finally:
            self.set_correlation_id(None)


class StructuredLogger:
    """Logger for structured data output (JSON format)."""
    
    def __init__(self, name: str = "structured") -> None:
        """Initialize structured logger."""
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    def _setup_logger(self) -> None:
        """Setup structured logger."""
        if self.logger.handlers:
            return
        
        self.logger.setLevel(logging.INFO)
        
        from pathlib import Path
        Path(config.LOG_DIR).mkdir(parents=True, exist_ok=True)
        
        handler = logging.FileHandler(
            config.LOG_DIR + "/structured.log"
        )
        
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        
        self.logger.addHandler(handler)
    
    def log_structured(self, event_type: str, data: Dict[str, Any]) -> None:
        """Log structured event."""
        import json
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "data": data
        }
        
        self.logger.info(json.dumps(log_entry))


# Global logger instances
main_logger = TradingLogger()
structured_logger = StructuredLogger()


def get_logger(name: str = "trading_ai") -> TradingLogger:
    """Get logger instance."""
    return TradingLogger(name)


def get_structured_logger(name: str = "structured") -> StructuredLogger:
    """Get structured logger instance."""
    return StructuredLogger(name)


# Convenience functions for backward compatibility
def log_trade(trade_data: Dict[str, Any]) -> None:
    """Log trade execution."""
    main_logger.log_trade(trade_data)


def log_signal(signal_data: Dict[str, Any]) -> None:
    """Log signal generation."""
    main_logger.log_signal(signal_data)


def log_error(error: Exception, context: Dict[str, Any]) -> None:
    """Log error with context."""
    main_logger.log_error_with_traceback(error, context)


def log_performance(metrics: Dict[str, Any]) -> None:
    """Log performance metrics."""
    main_logger.log_performance(metrics)
