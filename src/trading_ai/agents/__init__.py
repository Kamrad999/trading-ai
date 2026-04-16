"""
Agent modules for the Trading AI system.

Agents are responsible for data collection, signal generation, and optimization.
They form the intelligence layer of the trading pipeline.
"""

from .news_collector import NewsCollector
from .signal_generator import SignalGenerator
from .regime_detector import RegimeDetector
from .optimizer import SignalOptimizer

__all__ = [
    "NewsCollector",
    "SignalGenerator", 
    "RegimeDetector",
    "SignalOptimizer"
]
