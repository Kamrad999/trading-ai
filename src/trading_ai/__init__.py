"""
Trading AI - Institutional-Grade Trading Signal Engine

A 13-stage institutional trading pipeline that transforms RSS news feeds 
into real-time, risk-managed trading signals with institutional-grade 
validation, forensic credibility analysis, and multi-market regime detection.
"""

__version__ = "2.0.0"
__author__ = "Trading AI Team"
__description__ = "Institutional-Grade Trading Signal Engine"

from .core.orchestrator import PipelineOrchestrator
from .core.models import Article, Signal, Order, Position
from .core.exceptions import TradingError, RiskLimitExceeded, BrokerError

__all__ = [
    "PipelineOrchestrator",
    "Article", 
    "Signal", 
    "Order", 
    "Position",
    "TradingError",
    "RiskLimitExceeded", 
    "BrokerError"
]
