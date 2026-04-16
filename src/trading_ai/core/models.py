"""
Core data models for the Trading AI system.

This module defines the fundamental data structures used throughout the trading pipeline.
All models are designed to be immutable where possible and include comprehensive type hints.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class SignalDirection(str, Enum):
    """Trading signal direction."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class SignalType(str, Enum):
    """Signal type classification."""
    MACRO = "MACRO"
    EARNINGS = "EARNINGS"
    NEWS = "NEWS"
    TECHNICAL = "TECHNICAL"
    SENTIMENT = "SENTIMENT"


class Urgency(str, Enum):
    """Signal urgency level."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class MarketRegime(str, Enum):
    """Market regime classification."""
    RISK_ON = "RISK_ON"
    RISK_OFF = "RISK_OFF"
    SIDEWAYS = "SIDEWAYS"
    VOLATILE = "VOLATILE"


class OrderSide(str, Enum):
    """Order side."""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """Order type."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class TimeInForce(str, Enum):
    """Time in force."""
    DAY = "DAY"
    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"


class PipelineStatus(str, Enum):
    """Pipeline execution status."""
    SUCCESS = "SUCCESS"
    DEGRADED = "DEGRADED"
    HALTED = "HALTED"
    FAILED = "FAILED"


class MarketSession(str, Enum):
    """Market session classification."""
    PREMARKET = "PREMARKET"
    REGULAR = "REGULAR"
    AFTER_HOURS = "AFTER_HOURS"
    CLOSED = "CLOSED"
    CRYPTO_24_7 = "CRYPTO_24_7"


@dataclass(frozen=True)
class Article:
    """News article data structure."""
    title: str
    content: str
    source: str
    timestamp: datetime
    url: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Validate article data."""
        if not self.title.strip():
            raise ValueError("Article title cannot be empty")
        if not self.content.strip():
            raise ValueError("Article content cannot be empty")
        if not self.source.strip():
            raise ValueError("Article source cannot be empty")
        if not self.url.strip():
            raise ValueError("Article URL cannot be empty")


@dataclass(frozen=True)
class Signal:
    """Trading signal data structure."""
    direction: SignalDirection
    confidence: float
    urgency: Urgency
    market_regime: MarketRegime
    position_size: float
    execution_priority: int
    symbol: str
    signal_type: SignalType = SignalType.NEWS
    article_id: Optional[str] = None
    generated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Validate signal data."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Signal confidence must be between 0.0 and 1.0")
        if self.position_size <= 0:
            raise ValueError("Position size must be positive")
        if self.execution_priority < 0:
            raise ValueError("Execution priority must be non-negative")


@dataclass(frozen=True)
class Order:
    """Order data structure."""
    symbol: str
    side: OrderSide
    quantity: int
    order_type: OrderType
    time_in_force: TimeInForce
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Validate order data."""
        if not self.symbol.strip():
            raise ValueError("Order symbol cannot be empty")
        if self.quantity <= 0:
            raise ValueError("Order quantity must be positive")
        if self.order_type == OrderType.LIMIT and self.limit_price is None:
            raise ValueError("Limit orders must have a limit price")
        if self.order_type in [OrderType.STOP, OrderType.STOP_LIMIT] and self.stop_price is None:
            raise ValueError("Stop orders must have a stop price")


@dataclass(frozen=True)
class Position:
    """Position data structure."""
    symbol: str
    quantity: int
    avg_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Validate position data."""
        if not self.symbol.strip():
            raise ValueError("Position symbol cannot be empty")
        if self.avg_price <= 0:
            raise ValueError("Average price must be positive")
        if self.current_price <= 0:
            raise ValueError("Current price must be positive")


@dataclass(frozen=True)
class Execution:
    """Trade execution data structure."""
    order_id: str
    symbol: str
    side: OrderSide
    quantity: int
    price: float
    timestamp: datetime
    commission: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Validate execution data."""
        if not self.order_id.strip():
            raise ValueError("Execution order ID cannot be empty")
        if not self.symbol.strip():
            raise ValueError("Execution symbol cannot be empty")
        if self.quantity <= 0:
            raise ValueError("Execution quantity must be positive")
        if self.price <= 0:
            raise ValueError("Execution price must be positive")
        if self.commission < 0:
            raise ValueError("Commission cannot be negative")


@dataclass(frozen=True)
class Alert:
    """Alert data structure."""
    level: str
    message: str
    source: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Validate alert data."""
        if not self.level.strip():
            raise ValueError("Alert level cannot be empty")
        if not self.message.strip():
            raise ValueError("Alert message cannot be empty")
        if not self.source.strip():
            raise ValueError("Alert source cannot be empty")


@dataclass(frozen=True)
class ValidationResult:
    """Validation result data structure."""
    is_valid: bool
    confidence_score: float
    reasons: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Validate validation result."""
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")


@dataclass(frozen=True)
class RiskAssessment:
    """Risk assessment data structure."""
    risk_score: float
    position_size_limit: float
    reasons: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Validate risk assessment."""
        if not 0.0 <= self.risk_score <= 1.0:
            raise ValueError("Risk score must be between 0.0 and 1.0")
        if self.position_size_limit <= 0:
            raise ValueError("Position size limit must be positive")


@dataclass(frozen=True)
class PipelineResult:
    """Pipeline execution result."""
    status: PipelineStatus
    articles_processed: int
    signals_generated: int
    orders_sent: int
    alerts_sent: int
    pipeline_latency_ms: float
    stage_results: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Validate pipeline result."""
        if self.articles_processed < 0:
            raise ValueError("Articles processed cannot be negative")
        if self.signals_generated < 0:
            raise ValueError("Signals generated cannot be negative")
        if self.orders_sent < 0:
            raise ValueError("Orders sent cannot be negative")
        if self.alerts_sent < 0:
            raise ValueError("Alerts sent cannot be negative")
        if self.pipeline_latency_ms < 0:
            raise ValueError("Pipeline latency cannot be negative")


@dataclass(frozen=True)
class SystemStatus:
    """System health status."""
    version: str
    kill_switch_active: bool
    market_session: str
    portfolio_exposure_pct: float
    daily_drawdown_pct: float
    circuit_states: Dict[str, str]
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Validate system status."""
        if not self.version.strip():
            raise ValueError("Version cannot be empty")
        if not 0.0 <= self.portfolio_exposure_pct <= 1.0:
            raise ValueError("Portfolio exposure must be between 0.0 and 1.0")
        if self.daily_drawdown_pct < 0:
            raise ValueError("Daily drawdown cannot be negative")


# Type aliases for better readability
ArticleID = str
SignalID = str
OrderID = str
PositionID = str
ExecutionID = str
AlertID = str
