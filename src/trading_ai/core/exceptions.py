"""
Exception hierarchy for the Trading AI system.

This module defines all custom exceptions used throughout the trading pipeline.
The hierarchy is designed to provide clear error classification and proper error handling.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class TradingError(Exception):
    """Base class for all trading errors."""
    
    def __init__(self, message: str, error_code: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.context = context or {}
    
    def __str__(self) -> str:
        if self.error_code:
            return f"[{self.error_code}] {super().__str__()}"
        return super().__str__()


class RiskError(TradingError):
    """Base class for risk-related errors."""
    pass


class BrokerError(TradingError):
    """Base class for broker-related errors."""
    pass


class ValidationError(TradingError):
    """Base class for validation errors."""
    pass


class ConfigurationError(TradingError):
    """Base class for configuration errors."""
    pass


class ExecutionError(TradingError):
    """Base class for execution errors."""
    pass


# Risk-specific exceptions
class RiskLimitExceeded(RiskError):
    """Risk limits exceeded."""
    
    def __init__(self, message: str, limit_type: str, current_value: float, limit_value: float) -> None:
        super().__init__(message, "RISK_LIMIT_EXCEEDED")
        self.limit_type = limit_type
        self.current_value = current_value
        self.limit_value = limit_value


class ExposureLimitExceeded(RiskLimitExceeded):
    """Portfolio exposure limits exceeded."""
    
    def __init__(self, current_exposure: float, max_exposure: float) -> None:
        message = f"Portfolio exposure {current_exposure:.2%} exceeds limit {max_exposure:.2%}"
        super().__init__(message, "portfolio_exposure", current_exposure, max_exposure)


class DrawdownExceeded(RiskLimitExceeded):
    """Drawdown limits exceeded."""
    
    def __init__(self, current_drawdown: float, max_drawdown: float) -> None:
        message = f"Drawdown {current_drawdown:.2%} exceeds limit {max_drawdown:.2%}"
        super().__init__(message, "drawdown", current_drawdown, max_drawdown)


class PositionSizeExceeded(RiskLimitExceeded):
    """Position size limits exceeded."""
    
    def __init__(self, requested_size: float, max_size: float) -> None:
        message = f"Position size {requested_size:.2%} exceeds limit {max_size:.2%}"
        super().__init__(message, "position_size", requested_size, max_size)


# Broker-specific exceptions
class ConnectionError(BrokerError):
    """Broker connection error."""
    
    def __init__(self, message: str, broker: str, retry_count: int = 0) -> None:
        super().__init__(message, "BROKER_CONNECTION_ERROR")
        self.broker = broker
        self.retry_count = retry_count


class OrderError(BrokerError):
    """Order execution error."""
    
    def __init__(self, message: str, order_id: str, broker: str) -> None:
        super().__init__(message, "BROKER_ORDER_ERROR")
        self.order_id = order_id
        self.broker = broker


class AuthenticationError(BrokerError):
    """Broker authentication error."""
    
    def __init__(self, message: str, broker: str) -> None:
        super().__init__(message, "BROKER_AUTH_ERROR")
        self.broker = broker


class RateLimitError(BrokerError):
    """Broker rate limit error."""
    
    def __init__(self, message: str, broker: str, retry_after: Optional[int] = None) -> None:
        super().__init__(message, "BROKER_RATE_LIMIT_ERROR")
        self.broker = broker
        self.retry_after = retry_after


# Validation-specific exceptions
class SourceValidationError(ValidationError):
    """Source validation error."""
    
    def __init__(self, message: str, source: str, reason: str) -> None:
        super().__init__(message, "SOURCE_VALIDATION_ERROR")
        self.source = source
        self.reason = reason


class ContentValidationError(ValidationError):
    """Content validation error."""
    
    def __init__(self, message: str, article_id: str, validation_type: str) -> None:
        super().__init__(message, "CONTENT_VALIDATION_ERROR")
        self.article_id = article_id
        self.validation_type = validation_type


class DuplicateError(ValidationError):
    """Duplicate content error."""
    
    def __init__(self, message: str, original_id: str, duplicate_id: str, similarity_score: float) -> None:
        super().__init__(message, "DUPLICATE_ERROR")
        self.original_id = original_id
        self.duplicate_id = duplicate_id
        self.similarity_score = similarity_score


# Configuration-specific exceptions
class MissingConfigError(ConfigurationError):
    """Missing configuration value."""
    
    def __init__(self, config_key: str) -> None:
        message = f"Missing required configuration: {config_key}"
        super().__init__(message, "MISSING_CONFIG_ERROR")
        self.config_key = config_key


class InvalidConfigError(ConfigurationError):
    """Invalid configuration value."""
    
    def __init__(self, config_key: str, value: Any, expected_type: str) -> None:
        message = f"Invalid configuration value for {config_key}: expected {expected_type}, got {type(value).__name__}"
        super().__init__(message, "INVALID_CONFIG_ERROR")
        self.config_key = config_key
        self.value = value
        self.expected_type = expected_type


class ConfigConflictError(ConfigurationError):
    """Configuration conflict error."""
    
    def __init__(self, config_key: str, conflict_reason: str) -> None:
        message = f"Configuration conflict for {config_key}: {conflict_reason}"
        super().__init__(message, "CONFIG_CONFLICT_ERROR")
        self.config_key = config_key
        self.conflict_reason = conflict_reason


# Execution-specific exceptions
class PipelineError(ExecutionError):
    """Pipeline execution error."""
    
    def __init__(self, message: str, stage: str, pipeline_id: Optional[str] = None) -> None:
        super().__init__(message, "PIPELINE_ERROR")
        self.stage = stage
        self.pipeline_id = pipeline_id


class SystemError(ExecutionError):
    """System-level error."""
    
    def __init__(self, message: str, component: str, severity: str = "error") -> None:
        super().__init__(message, "SYSTEM_ERROR")
        self.component = component
        self.severity = severity


class KillSwitchActivated(ExecutionError):
    """Kill switch activated error."""
    
    def __init__(self, reason: str) -> None:
        message = f"Kill switch activated: {reason}"
        super().__init__(message, "KILL_SWITCH_ACTIVATED")
        self.reason = reason


class CircuitBreakerOpen(ExecutionError):
    """Circuit breaker is open."""
    
    def __init__(self, component: str, failure_count: int, threshold: int) -> None:
        message = f"Circuit breaker open for {component}: {failure_count}/{threshold} failures"
        super().__init__(message, "CIRCUIT_BREAKER_OPEN")
        self.component = component
        self.failure_count = failure_count
        self.threshold = threshold


# Data-specific exceptions
class DataError(TradingError):
    """Base class for data-related errors."""
    pass


class DataCorruptionError(DataError):
    """Data corruption error."""
    
    def __init__(self, message: str, data_type: str, data_id: str) -> None:
        super().__init__(message, "DATA_CORRUPTION_ERROR")
        self.data_type = data_type
        self.data_id = data_id


class DataValidationError(DataError):
    """Data validation error."""
    
    def __init__(self, message: str, data_type: str, field: str, value: Any) -> None:
        super().__init__(message, "DATA_VALIDATION_ERROR")
        self.data_type = data_type
        self.field = field
        self.value = value


class DataNotFoundError(DataError):
    """Data not found error."""
    
    def __init__(self, message: str, data_type: str, search_key: str) -> None:
        super().__init__(message, "DATA_NOT_FOUND_ERROR")
        self.data_type = data_type
        self.search_key = search_key


# Utility functions for error handling
def format_error(error: Exception) -> Dict[str, Any]:
    """Format error for logging and reporting."""
    return {
        "type": type(error).__name__,
        "message": str(error),
        "error_code": getattr(error, "error_code", None),
        "context": getattr(error, "context", {}),
        "details": {
            attr: getattr(error, attr)
            for attr in dir(error)
            if not attr.startswith("_") and not callable(getattr(error, attr))
        }
    }


def is_recoverable_error(error: Exception) -> bool:
    """Check if an error is recoverable."""
    recoverable_errors = (
        ConnectionError,
        RateLimitError,
        OrderError,
        CircuitBreakerOpen,
    )
    return isinstance(error, recoverable_errors)


def is_critical_error(error: Exception) -> bool:
    """Check if an error is critical."""
    critical_errors = (
        KillSwitchActivated,
        DataCorruptionError,
        AuthenticationError,
        SystemError,
    )
    return isinstance(error, critical_errors)
