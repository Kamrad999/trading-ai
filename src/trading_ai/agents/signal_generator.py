"""
Real signal generation for Trading AI.

Implements keyword impact scoring, macro sentiment scoring, urgency score,
symbol extraction, directional bias, confidence score, and event severity weighting.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from ..core.models import Article, Signal, SignalDirection, Urgency
from ..infrastructure.config import config
from ..infrastructure.logging import get_logger


class SignalGenerator:
    """Real signal generation engine."""
    
    def __init__(self) -> None:
        """Initialize signal generator with keyword libraries."""
        self.logger = get_logger("signal_generator")
        
        # Bullish keywords with impact scores
        self.bullish_keywords = {
            # High impact (0.8-1.0)
            'bullish': 0.9, 'rally': 0.8, 'surge': 0.8, 'jump': 0.8,
            'soar': 0.9, 'skyrocket': 0.9, 'boom': 0.8, 'explosion': 0.8,
            'breakthrough': 0.9, 'milestone': 0.8, 'record': 0.8, 'all-time high': 0.9,
            'beat expectations': 0.8, 'exceed': 0.8, 'outperform': 0.8,
            
            # Medium impact (0.5-0.7)
            'rise': 0.6, 'increase': 0.5, 'growth': 0.6, 'gain': 0.6,
            'positive': 0.5, 'optimistic': 0.6, 'strong': 0.5, 'robust': 0.6,
            'upgrade': 0.7, 'buy': 0.6, 'recommend': 0.5, 'target': 0.5,
            
            # Lower impact (0.3-0.4)
            'up': 0.4, 'higher': 0.4, 'improve': 0.3, 'boost': 0.4,
            'support': 0.3, 'momentum': 0.4, 'trend': 0.3
        }
        
        # Bearish keywords with impact scores
        self.bearish_keywords = {
            # High impact (0.8-1.0)
            'bearish': 0.9, 'crash': 0.9, 'plunge': 0.8, 'collapse': 0.9,
            'tumble': 0.8, 'slump': 0.8, 'freefall': 0.9, 'meltdown': 0.9,
            'crisis': 0.8, 'panic': 0.8, 'disaster': 0.8, 'catastrophe': 0.9,
            'miss expectations': 0.8, 'disappoint': 0.7, 'underperform': 0.7,
            
            # Medium impact (0.5-0.7)
            'fall': 0.6, 'drop': 0.6, 'decline': 0.5, 'decrease': 0.5,
            'negative': 0.5, 'pessimistic': 0.6, 'weak': 0.5, 'fragile': 0.6,
            'downgrade': 0.7, 'sell': 0.6, 'avoid': 0.5, 'risk': 0.5,
            
            # Lower impact (0.3-0.4)
            'down': 0.4, 'lower': 0.4, 'worsen': 0.3, 'cut': 0.4,
            'resistance': 0.3, 'concern': 0.3, 'warning': 0.4
        }
        
        # Urgency keywords
        self.urgency_keywords = {
            'breaking': 1.0, 'urgent': 0.9, 'immediate': 0.8,
            'critical': 0.8, 'alert': 0.7, 'warning': 0.6,
            'developing': 0.5, 'update': 0.4, 'latest': 0.3
        }
        
        # Event severity weighting
        self.event_severity = {
            'earnings': 0.7, 'merger': 0.9, 'acquisition': 0.9,
            'bankruptcy': 1.0, 'fraud': 0.9, 'scandal': 0.8,
            'regulation': 0.6, 'approval': 0.7, 'rejection': 0.7,
            'launch': 0.5, 'recall': 0.8, 'lawsuit': 0.8,
            'patent': 0.4, 'innovation': 0.5, 'research': 0.4
        }
        
        # Symbol extraction patterns
        self.symbol_patterns = [
            r'\b[A-Z]{2,5}\b',  # Stock symbols (2-5 uppercase letters)
            r'\$[A-Z]{2,5}\b',  # $ prefixed symbols
            r'\([A-Z]{2,5}\)',  # Parenthesized symbols
            r'\b[A-Z]{1,4}\.\d{1,2}\b',  # Futures contracts
        ]
        
        # Confidence thresholds
        self.min_confidence_threshold = config.MIN_SIGNAL_CONFIDENCE
        self.max_signals_per_article = 3
        
    def generate_signals(self, articles: List[Article]) -> List[Signal]:
        """
        Generate trading signals from validated articles.
        
        Args:
            articles: List of validated articles
            
        Returns:
            List of generated signals
        """
        signals = []
        
        self.logger.info(f"Generating signals from {len(articles)} articles")
        
        for article in articles:
            article_signals = self._generate_article_signals(article)
            signals.extend(article_signals)
        
        # Sort by confidence and limit
        signals.sort(key=lambda s: s.confidence, reverse=True)
        
        self.logger.info(
            f"Signal generation completed: {len(signals)} signals generated, "
            f"avg confidence: {sum(s.confidence for s in signals) / len(signals):.3f}" if signals else "No signals generated"
        )
        
        return signals
    
    def _generate_article_signals(self, article: Article) -> List[Signal]:
        """Generate signals from a single article."""
        signals = []
        
        # Get validation metadata
        validation_meta = article.metadata.get("validation", {})
        article_confidence = validation_meta.get("confidence_score", 0.5)
        
        # Extract text for analysis
        text = f"{article.title} {article.content}".lower()
        
        # Calculate sentiment scores
        bullish_score = self._calculate_keyword_score(text, self.bullish_keywords)
        bearish_score = self._calculate_keyword_score(text, self.bearish_keywords)
        
        # Skip if no clear sentiment
        if max(bullish_score, bearish_score) < 0.3:
            return signals
        
        # Determine direction
        if bullish_score > bearish_score:
            direction = SignalDirection.BUY
            sentiment_score = bullish_score
        elif bearish_score > bullish_score:
            direction = SignalDirection.SELL
            sentiment_score = bearish_score
        else:
            return signals  # Neutral sentiment, no signal
        
        # Calculate urgency
        urgency_score = self._calculate_keyword_score(text, self.urgency_keywords)
        urgency = self._determine_urgency(urgency_score)
        
        # Extract symbols
        symbols = self._extract_symbols(article.title, article.content)
        
        # Calculate event severity
        event_severity = self._calculate_event_severity(text)
        
        # Calculate final confidence
        base_confidence = (sentiment_score + urgency_score) / 2
        final_confidence = base_confidence * article_confidence * event_severity
        
        # Skip if below threshold
        if final_confidence < self.min_confidence_threshold:
            return signals
        
        # Generate signal for each symbol found
        for symbol in symbols[:self.max_signals_per_article]:
            signal = Signal(
                direction=direction,
                confidence=min(final_confidence, 1.0),
                urgency=urgency,
                market_regime=self._detect_market_regime(article),
                position_size=self._calculate_position_size(final_confidence, event_severity),
                execution_priority=self._calculate_execution_priority(urgency_score, final_confidence),
                symbol=symbol,
                article_id=hashlib.sha256(f"{article.title}{article.url}".encode()).hexdigest()[:16],
                generated_at=datetime.now(timezone.utc),
                metadata={
                    "source": article.source,
                    "sentiment_score": sentiment_score,
                    "urgency_score": urgency_score,
                    "event_severity": event_severity,
                    "validation_confidence": article_confidence,
                    "keywords_found": self._get_found_keywords(text)
                }
            )
            signals.append(signal)
        
        return signals
    
    def _calculate_keyword_score(self, text: str, keyword_dict: Dict[str, float]) -> float:
        """Calculate keyword impact score."""
        total_score = 0.0
        keyword_count = 0
        
        for keyword, impact in keyword_dict.items():
            # Count occurrences
            pattern = r'\b' + re.escape(keyword) + r'\b'
            matches = re.findall(pattern, text, re.IGNORECASE)
            
            if matches:
                count = len(matches)
                # Apply diminishing returns for multiple occurrences
                weight = 1.0 - (0.1 * (count - 1)) if count > 1 else 1.0
                weight = max(weight, 0.3)  # Minimum weight
                
                total_score += impact * weight
                keyword_count += count
        
        # Normalize by text length
        text_length = len(text.split())
        if text_length > 0:
            normalized_score = total_score / min(text_length / 100, 10)  # Cap normalization
        else:
            normalized_score = 0
        
        return min(normalized_score, 1.0)
    
    def _determine_urgency(self, urgency_score: float) -> Urgency:
        """Determine signal urgency from score."""
        if urgency_score >= 0.8:
            return Urgency.HIGH
        elif urgency_score >= 0.5:
            return Urgency.MEDIUM
        else:
            return Urgency.LOW
    
    def _extract_symbols(self, title: str, content: str) -> List[str]:
        """Extract trading symbols from text."""
        symbols = set()
        text = f"{title} {content}"
        
        for pattern in self.symbol_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # Clean up symbol
                symbol = match.strip('$()')
                if len(symbol) >= 2 and len(symbol) <= 5:  # Reasonable symbol length
                    symbols.add(symbol.upper())
        
        # Filter out common words that match symbol patterns
        common_words = {'THE', 'FOR', 'AND', 'TO', 'IN', 'ON', 'AT', 'BY', 'WITH', 'FROM', 'UP', 'IT', 'IS', 'BE', 'ARE'}
        symbols = {s for s in symbols if s not in common_words}
        
        return list(symbols)
    
    def _calculate_event_severity(self, text: str) -> float:
        """Calculate event severity weighting."""
        severity_score = 0.0
        
        for event, severity in self.event_severity.items():
            if event in text:
                severity_score = max(severity_score, severity)
        
        # Default severity if no specific event found
        return severity_score if severity_score > 0 else 0.5
    
    def _detect_market_regime(self, article: Article) -> str:
        """Detect market regime from article content."""
        text = f"{article.title} {article.content}".lower()
        
        # Simple regime detection based on keywords
        if any(word in text for word in ['bull market', 'rally', 'boom', 'growth']):
            return "RISK_ON"
        elif any(word in text for word in ['bear market', 'crash', 'recession', 'downturn']):
            return "RISK_OFF"
        elif any(word in text for word in ['volatile', 'uncertain', 'mixed']):
            return "VOLATILE"
        else:
            return "NEUTRAL"
    
    def _calculate_position_size(self, confidence: float, event_severity: float) -> float:
        """Calculate recommended position size."""
        base_size = confidence * 0.1  # Max 10% per signal
        severity_adjustment = event_severity
        return min(base_size * severity_adjustment, 0.2)  # Cap at 20%
    
    def _calculate_execution_priority(self, urgency_score: float, confidence: float) -> int:
        """Calculate execution priority (1=highest, 10=lowest)."""
        priority_score = (urgency_score * 0.6 + confidence * 0.4)
        
        if priority_score >= 0.8:
            return 1
        elif priority_score >= 0.6:
            return 2
        elif priority_score >= 0.4:
            return 3
        else:
            return 4
    
    def _get_found_keywords(self, text: str) -> Dict[str, int]:
        """Get all keywords found in text."""
        found = {}
        
        all_keywords = {**self.bullish_keywords, **self.bearish_keywords, **self.urgency_keywords}
        
        for keyword in all_keywords:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                found[keyword] = len(matches)
        
        return found
    
    def get_signal_stats(self) -> Dict[str, Any]:
        """Get signal generation statistics."""
        return {
            'bullish_keywords': len(self.bullish_keywords),
            'bearish_keywords': len(self.bearish_keywords),
            'urgency_keywords': len(self.urgency_keywords),
            'event_types': len(self.event_severity),
            'min_confidence_threshold': self.min_confidence_threshold,
            'max_signals_per_article': self.max_signals_per_article
        }
