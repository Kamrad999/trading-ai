"""
Configuration management for the Trading AI system.

This module centralizes all system-wide constants, thresholds, environment toggles,
broker settings, risk controls, timing intervals, and file paths.

All modules should import from here rather than hard-coding values:
    from trading_ai.infrastructure.config import (
        PORTFOLIO_SIZE_USD, MIN_SIGNAL_CONFIDENCE, PAPER_MODE
    )
"""

from __future__ import annotations

import os
from typing import Any, Final, Dict, List, Tuple


class Config:
    """Configuration manager with validation and environment support."""
    
    def __init__(self, config_file: str = None) -> None:
        """Initialize configuration with optional file override."""
        self._config_file = config_file
        self._validate_config()
    
    # ==================== RUNTIME MODE ====================
    
    PAPER_MODE: Final[bool] = True
    """Simulation/paper-trading mode. No real orders reach exchanges."""
    
    LIVE_MODE: Final[bool] = False
    """Live-trading mode. When True, PAPER_MODE must be False."""
    
    DEFAULT_BROKER: Final[str] = "paper"
    """Active broker adapter: 'paper' | 'alpaca' | 'ibkr' | 'binance'."""
    
    ENABLE_PLUGINS: Final[bool] = True
    """Load optional plugin modules from /plugins directory."""
    
    DEBUG: Final[bool] = True
    """Enable verbose debug-level logging across all modules."""
    
    TEST_MODE: Final[bool] = True
    """Test mode for rapid development with simulated data."""
    
    # ==================== PORTFOLIO + RISK ====================
    
    PORTFOLIO_SIZE_USD: Final[float] = 25_000.0
    """Total notional capital allocated to the strategy (USD)."""
    
    MAX_OPEN_POSITIONS: Final[int] = 5
    """Hard ceiling on concurrent open positions."""
    
    MAX_RISK_PER_TRADE: Final[float] = 0.02
    """Maximum fraction of portfolio risked on a single trade (2%)."""
    
    MAX_PORTFOLIO_EXPOSURE: Final[float] = 0.95
    """Maximum portfolio exposure (95% of portfolio)."""
    
    MAX_TICKER_EXPOSURE: Final[float] = 0.10
    """Maximum fraction of portfolio allocated to any single ticker (10%)."""
    
    DAILY_LOSS_LIMIT: Final[float] = 0.025
    """Intraday drawdown fraction that triggers full trading halt (2.5%)."""
    
    WARNING_DRAWDOWN: Final[float] = 0.015
    """Intraday drawdown fraction that triggers risk-warning alert (1.5%)."""
    
    # Drawdown policy tiers - single source of truth for all risk modules
    DRAWDOWN_POLICY_TIERS: Final[List[Tuple[float, str, float]]] = [
        # (threshold_pct, action_name, position_size_multiplier)
        (0.025, "FULL_KILL_SWITCH", 0.0),    # >= 2.5% -> block all trades
        (0.015, "HEAVY_REDUCTION", 0.4),     # 1.5-2.5% -> 40% position size
        (0.005, "WARNING_ALERT", 0.8),       # 0.5-1.5% -> reduce 20%
        (0.0,   "NORMAL", 1.0),              # < 0.5% -> full size
    ]
    
    # Drawdown action constants
    DRAWDOWN_ACTION_KILL_SWITCH = "FULL_KILL_SWITCH"
    DRAWDOWN_ACTION_HEAVY_REDUCTION = "HEAVY_REDUCTION"
    DRAWDOWN_ACTION_WARNING = "WARNING_ALERT"
    DRAWDOWN_ACTION_NORMAL = "NORMAL"
    
    # ==================== SIGNAL THRESHOLDS ====================
    
    MIN_SIGNAL_CONFIDENCE: Final[float] = 0.80
    """Minimum model confidence required for actionable signals."""
    
    ELITE_SIGNAL_CONFIDENCE: Final[float] = 0.90
    """Confidence level that qualifies a signal as 'elite'."""
    
    CONVICTION_BONUS_THRESHOLD: Final[float] = 0.92
    """Confidence level for conviction-sizing bonus."""
    
    EXECUTION_CONFIDENCE_THRESHOLD: Final[float] = 0.80
    """Confidence threshold for immediate execution."""
    
    SIGNAL_HALF_LIFE_MINUTES: Final[int] = 20
    """Minutes before a signal is considered stale."""
    
    # ==================== TIMING CONTROLS ====================
    
    NEWS_POLL_INTERVAL_SECONDS: Final[int] = 300
    """How often news engine fetches fresh headlines (5 minutes)."""
    
    COOLDOWN_MINUTES: Final[int] = 15
    """Minimum gap between successive entries on same ticker."""
    
    MACRO_FREEZE_PRE_MINUTES: Final[int] = 30
    """Minutes before macro events to block new entries."""
    
    MACRO_FREEZE_POST_MINUTES: Final[int] = 15
    """Minutes after macro events before normal flow resumes."""
    
    FAILURE_BACKOFF_BASE_SECONDS: Final[int] = 5
    """Base delay for exponential back-off on API failures."""
    
    REGIME_DETECTION_WINDOW: Final[int] = 252
    """Days for market regime detection window."""
    
    # ==================== EXECUTION TEMPLATES ====================
    
    EXECUTION_TEMPLATES: Final[Dict[str, Dict[str, Any]]] = {
        "crypto": {
            "position_size_pct": 0.05,
            "stop_loss_pct": 0.02,
            "take_profit_pct": 0.04,
            "conviction_multiplier": 1.5,
        },
        "equities": {
            "position_size_pct": 0.08,
            "stop_loss_pct": 0.015,
            "take_profit_pct": 0.03,
            "conviction_multiplier": 1.3,
        },
        "forex": {
            "position_size_pct": 0.06,
            "stop_loss_pct": 0.01,
            "take_profit_pct": 0.02,
            "conviction_multiplier": 1.4,
        },
        "commodities": {
            "position_size_pct": 0.04,
            "stop_loss_pct": 0.025,
            "take_profit_pct": 0.05,
            "conviction_multiplier": 1.6,
        },
    }
    
    # ==================== BROKER CONFIGURATIONS ====================
    
    ALPACA_CONFIG: Final[Dict[str, Any]] = {
        "api_key": os.getenv("ALPACA_API_KEY", ""),
        "secret_key": os.getenv("ALPACA_SECRET_KEY", ""),
        "base_url": "https://api.alpaca.markets",
        "paper": True,
        "data_feed": "sip",
    }
    
    IBKR_CONFIG: Final[Dict[str, Any]] = {
        "host": os.getenv("IBKR_HOST", "127.0.0.1"),
        "port": int(os.getenv("IBKR_PORT", "7497")),
        "client_id": 1,
        "timeout": 10,
    }
    
    BINANCE_CONFIG: Final[Dict[str, Any]] = {
        "api_key": os.getenv("BINANCE_API_KEY", ""),
        "secret_key": os.getenv("BINANCE_SECRET_KEY", ""),
        "testnet": True,
        "base_url": "https://testnet.binance.vision",
    }
    
    # ==================== ALERT CONFIGURATIONS ====================
    
    ALERT_CONFIG: Final[Dict[str, Dict[str, Any]]] = {
        "email": {
            "enabled": True,
            "recipients": os.getenv("ALERT_EMAIL_RECIPIENTS", "").split(","),
            "smtp_host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
            "smtp_port": int(os.getenv("SMTP_PORT", "587")),
        },
        "webhook": {
            "enabled": bool(os.getenv("WEBHOOK_URL")),
            "url": os.getenv("WEBHOOK_URL", ""),
        },
        "slack": {
            "enabled": bool(os.getenv("SLACK_WEBHOOK_URL")),
            "webhook_url": os.getenv("SLACK_WEBHOOK_URL", ""),
        },
    }
    
    # ==================== FILE PATHS ====================
    
    DATA_DIR: Final[str] = os.getenv("TRADING_AI_DATA_DIR", "./data")
    """Directory for data files."""
    
    LOG_DIR: Final[str] = os.getenv("TRADING_AI_LOG_DIR", "./logs")
    """Directory for log files."""
    
    STATE_FILE: Final[str] = os.path.join(DATA_DIR, "state.json")
    """File for system state persistence."""
    
    VALIDATION_MEMORY_FILE: Final[str] = os.path.join(DATA_DIR, "validation_memory.json")
    """File for validation memory persistence."""
    
    PERFORMANCE_LOG_FILE: Final[str] = os.path.join(LOG_DIR, "performance.log")
    """File for performance logging."""
    
    # ==================== MARKET SESSIONS ====================
    
    MARKET_SESSIONS: Final[Dict[str, Dict[str, str]]] = {
        "US_EQUITIES": {
            "open": "14:30",
            "close": "21:00",
            "timezone": "UTC",
        },
        "FOREX": {
            "open": "00:00",
            "close": "23:59",
            "timezone": "UTC",
        },
        "CRYPTO": {
            "open": "00:00",
            "close": "23:59",
            "timezone": "UTC",
        },
    }
    
    # ==================== VALIDATION ====================
    
    VALID_BROKERS: Final[frozenset] = frozenset({"paper", "alpaca", "ibkr", "binance"})
    """Set of valid broker identifiers."""
    
    def _validate_config(self) -> None:
        """Validate configuration consistency."""
        if self.LIVE_MODE and self.PAPER_MODE:
            raise ValueError("Cannot have both LIVE_MODE and PAPER_MODE enabled")
        
        if self.DEFAULT_BROKER not in self.VALID_BROKERS:
            raise ValueError(f"Invalid broker: {self.DEFAULT_BROKER}")
        
        if not 0.0 <= self.MIN_SIGNAL_CONFIDENCE <= 1.0:
            raise ValueError("MIN_SIGNAL_CONFIDENCE must be between 0.0 and 1.0")
        
        if not 0.0 <= self.MAX_RISK_PER_TRADE <= 1.0:
            raise ValueError("MAX_RISK_PER_TRADE must be between 0.0 and 1.0")
        
        if self.PORTFOLIO_SIZE_USD <= 0:
            raise ValueError("PORTFOLIO_SIZE_USD must be positive")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        return getattr(self, key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value (for testing only)."""
        if not hasattr(self, key):
            raise KeyError(f"Unknown configuration key: {key}")
        setattr(self, key, value)
    
    def as_dict(self) -> Dict[str, Any]:
        """Return configuration as dictionary."""
        return {
            key: getattr(self, key)
            for key in dir(self)
            if not key.startswith("_") and not callable(getattr(self, key))
        }
    
    def reload(self) -> None:
        """Reload configuration (placeholder for future implementation)."""
        self._validate_config()


# Global configuration instance
config = Config()


# Convenience functions for backward compatibility
def get_config() -> Config:
    """Get global configuration instance."""
    return config


def validate_config() -> bool:
    """Validate configuration."""
    try:
        config._validate_config()
        return True
    except Exception:
        return False


# Field name constants for unified access
SIGNAL_FIELD_DIRECTION = "direction"
SIGNAL_FIELD_CONFIDENCE = "confidence"
SIGNAL_FIELD_MARKET_REGIME = "market_regime"
SIGNAL_FIELD_POSITION_SIZE = "position_size"

REGIME_FIELD_NAME = "name"
REGIME_FIELD_GROSS_CAP = "gross_cap"

POSITION_FIELD_SIZE = "size"
POSITION_FIELD_EXPOSURE = "exposure"
