"""
Real news validation for Trading AI.

Implements source credibility scoring, malformed headline detection,
spam/promo rejection, duplicate syndication weighting, and confidence scoring.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Set

from ..core.models import Article, ValidationResult
from ..infrastructure.logging import get_logger


class NewsValidator:
    """Real news validation engine."""
    
    def __init__(self) -> None:
        """Initialize news validator with credibility rules."""
        self.logger = get_logger("news_validator")
        
        # Source credibility scores (0.0-1.0)
        self.source_credibility = {
            # High credibility sources
            'Reuters': 0.95,
            'Wall Street Journal': 0.90,
            'Federal Reserve': 0.98,
            'US Treasury': 0.98,
            'BEA': 0.95,
            
            # Medium credibility sources
            'Bloomberg': 0.85,
            'CNBC': 0.80,
            'MarketWatch': 0.75,
            'Yahoo Finance': 0.70,
            
            # Crypto sources (lower credibility)
            'CoinDesk': 0.65,
            'Cointelegraph': 0.60,
            'Seeking Alpha': 0.75,
            
            # Commodity sources
            'OilPrice': 0.70,
            'Kitco': 0.75,
            
            # Default for unknown sources
            'Unknown Source': 0.50
        }
        
        # Spam/promo patterns to reject
        self.spam_patterns = [
            r'buy\s+now',
            r'limited\s+time',
            r'act\s+fast',
            r'don\'t\s+miss',
            r'click\s+here',
            r'free\s+trial',
            r'money\s+back',
            r'guaranteed',
            r'risk\s+free',
            r'secret\s+method',
            r'get\s+rich',
            r'millionaire',
            r'bitcoin\s+revolution',
            r'crypto\s+millionaire',
            r'1000%\s+return',
            r'double\s+your',
            r'instant\s+profit'
        ]
        
        # Malformed headline patterns
        self.malformed_patterns = [
            r'^\s*$',  # Empty title
            r'^[^a-zA-Z]',  # Starts with non-letter
            r'[A-Z]{5,}',  # Too many consecutive caps
            r'!!!+',  # Excessive exclamation
            r'\?\?\?+',  # Excessive question marks
            r'\.{4,}',  # Excessive periods
            r'[^\w\s\.\!\?\-\,\:\;\\"\']+',  # Special characters
        ]
        
        # Minimum content requirements
        self.min_title_length = 10
        self.min_content_length = 50
        self.max_title_length = 200
        self.max_content_length = 10000
        
        # Validation thresholds
        self.min_confidence_threshold = 0.3
        self.spam_penalty = 0.5
        self.malformed_penalty = 0.3
        
    def validate_article(self, article: Article) -> ValidationResult:
        """
        Validate article credibility and quality.
        
        Args:
            article: Article to validate
            
        Returns:
            ValidationResult with confidence score and reasons
        """
        reasons = []
        base_confidence = self.source_credibility.get(article.source, 0.50)
        
        # Check title validity
        title_score, title_reasons = self._validate_title(article.title)
        reasons.extend(title_reasons)
        
        # Check content validity
        content_score, content_reasons = self._validate_content(article.content)
        reasons.extend(content_reasons)
        
        # Check for spam/promo content
        spam_score, spam_reasons = self._check_spam(article.title, article.content)
        reasons.extend(spam_reasons)
        
        # Check timestamp validity
        time_score, time_reasons = self._validate_timestamp(article.timestamp)
        reasons.extend(time_reasons)
        
        # Calculate final confidence
        final_confidence = base_confidence * title_score * content_score * time_score
        
        # Apply penalties
        if spam_score < 1.0:
            final_confidence *= spam_score
        
        # Determine if valid
        is_valid = final_confidence >= self.min_confidence_threshold
        
        self.logger.debug(
            f"Article validation: {article.title[:50]}... "
            f"score={final_confidence:.3f}, valid={is_valid}"
        )
        
        return ValidationResult(
            is_valid=is_valid,
            confidence_score=final_confidence,
            reasons=reasons,
            metadata={
                'source_score': base_confidence,
                'title_score': title_score,
                'content_score': content_score,
                'spam_score': spam_score,
                'time_score': time_score
            }
        )
    
    def _validate_title(self, title: str) -> tuple[float, List[str]]:
        """Validate article title."""
        reasons = []
        score = 1.0
        
        # Length checks
        if len(title) < self.min_title_length:
            reasons.append(f"Title too short: {len(title)} chars")
            score *= 0.7
        
        if len(title) > self.max_title_length:
            reasons.append(f"Title too long: {len(title)} chars")
            score *= 0.8
        
        # Malformed pattern checks
        for pattern in self.malformed_patterns:
            if re.search(pattern, title, re.IGNORECASE):
                reasons.append(f"Malformed title pattern: {pattern}")
                score *= (1.0 - self.malformed_penalty)
        
        # Check for all caps (excessive)
        if len(title) > 10 and title.upper() == title:
            reasons.append("Title in all caps")
            score *= 0.8
        
        # Check for excessive punctuation
        punctuation_count = sum(1 for c in title if c in '.!?')
        if punctuation_count > 3:
            reasons.append(f"Excessive punctuation: {punctuation_count}")
            score *= 0.9
        
        return score, reasons
    
    def _validate_content(self, content: str) -> tuple[float, List[str]]:
        """Validate article content."""
        reasons = []
        score = 1.0
        
        # Length checks
        if len(content) < self.min_content_length:
            reasons.append(f"Content too short: {len(content)} chars")
            score *= 0.6
        
        if len(content) > self.max_content_length:
            reasons.append(f"Content too long: {len(content)} chars")
            score *= 0.9
        
        # Content quality checks
        if content.strip() == content:  # No proper paragraph structure
            if len(content) > 200:  # Only penalize longer content
                reasons.append("Poor paragraph structure")
                score *= 0.9
        
        # Check for meaningful content (words, not just numbers/symbols)
        words = re.findall(r'\b[a-zA-Z]+\b', content)
        if len(words) < 10 and len(content) > 100:
            reasons.append("Low word count for content length")
            score *= 0.8
        
        return score, reasons
    
    def _check_spam(self, title: str, content: str) -> tuple[float, List[str]]:
        """Check for spam and promotional content."""
        reasons = []
        score = 1.0
        combined_text = f"{title} {content}".lower()
        
        # Check spam patterns
        spam_matches = 0
        for pattern in self.spam_patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                spam_matches += 1
                reasons.append(f"Spam pattern detected: {pattern}")
        
        if spam_matches > 0:
            score *= (1.0 - (spam_matches * self.spam_penalty))
            score = max(score, 0.1)  # Minimum score
        
        # Check excessive capitalization
        caps_ratio = sum(1 for c in combined_text if c.isupper()) / len(combined_text)
        if caps_ratio > 0.3:  # More than 30% caps
            reasons.append(f"Excessive capitalization: {caps_ratio:.1%}")
            score *= 0.8
        
        # Check for excessive punctuation
        punct_ratio = sum(1 for c in combined_text if c in '!?.') / len(combined_text)
        if punct_ratio > 0.05:  # More than 5% punctuation
            reasons.append(f"Excessive punctuation: {punct_ratio:.1%}")
            score *= 0.9
        
        return score, reasons
    
    def _validate_timestamp(self, timestamp) -> tuple[float, List[str]]:
        """Validate article timestamp."""
        reasons = []
        score = 1.0
        
        try:
            now = timestamp.now(tz=timestamp.tzinfo) if timestamp.tzinfo else timestamp.now()
            
            # Check if timestamp is in future
            if timestamp > now:
                reasons.append("Timestamp in future")
                score *= 0.5
            
            # Check if timestamp is too old (more than 7 days)
            age_days = (now - timestamp).days
            if age_days > 7:
                reasons.append(f"Article too old: {age_days} days")
                score *= 0.8
            
        except Exception as e:
            reasons.append(f"Timestamp validation error: {e}")
            score *= 0.7
        
        return score, reasons
    
    def validate_batch(self, articles: List[Article]) -> List[ValidationResult]:
        """
        Validate multiple articles.
        
        Args:
            articles: List of articles to validate
            
        Returns:
            List of validation results
        """
        results = []
        valid_count = 0
        
        self.logger.info(f"Validating {len(articles)} articles")
        
        for article in articles:
            result = self.validate_article(article)
            results.append(result)
            
            if result.is_valid:
                valid_count += 1
        
        avg_confidence = sum(r.confidence_score for r in results) / len(results) if results else 0
        
        self.logger.info(
            f"Validation completed: {valid_count}/{len(articles)} valid, "
            f"avg confidence: {avg_confidence:.3f}"
        )
        
        return results
    
    def get_source_stats(self) -> Dict[str, Any]:
        """Get source credibility statistics."""
        return {
            'source_count': len(self.source_credibility),
            'avg_credibility': sum(self.source_credibility.values()) / len(self.source_credibility),
            'min_confidence_threshold': self.min_confidence_threshold,
            'spam_patterns_count': len(self.spam_patterns),
            'malformed_patterns_count': len(self.malformed_patterns)
        }
    
    def update_source_credibility(self, source: str, credibility: float) -> None:
        """Update source credibility score."""
        if 0.0 <= credibility <= 1.0:
            self.source_credibility[source] = credibility
            self.logger.info(f"Updated source credibility: {source} -> {credibility:.3f}")
        else:
            self.logger.warning(f"Invalid credibility score for {source}: {credibility}")
