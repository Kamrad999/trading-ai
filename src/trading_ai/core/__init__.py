"""
Core components for the Trading AI system.

This module contains the fundamental data models, exceptions, and orchestration
logic that form the backbone of the trading pipeline.
"""

from .models import Article, Signal, Order, Position, PipelineResult, SystemStatus
from .exceptions import (
    TradingError, 
    RiskError, 
    BrokerError, 
    ValidationError, 
    ConfigurationError,
    RiskLimitExceeded,
    ExposureLimitExceeded,
    DrawdownExceeded,
    ConnectionError,
    OrderError,
    AuthenticationError,
    SourceValidationError,
    ContentValidationError,
    DuplicateError,
    MissingConfigError,
    InvalidConfigError,
    ExecutionError,
    PipelineError,
    SystemError
)
from .orchestrator import PipelineOrchestrator

__all__ = [
    "Article",
    "Signal", 
    "Order",
    "Position",
    "PipelineResult",
    "SystemStatus",
    "TradingError",
    "RiskError",
    "BrokerError", 
    "ValidationError",
    "ConfigurationError",
    "RiskLimitExceeded",
    "ExposureLimitExceeded",
    "DrawdownExceeded",
    "ConnectionError",
    "OrderError",
    "AuthenticationError",
    "SourceValidationError",
    "ContentValidationError",
    "DuplicateError",
    "MissingConfigError",
    "InvalidConfigError",
    "ExecutionError",
    "PipelineError",
    "SystemError",
    "PipelineOrchestrator"
]
