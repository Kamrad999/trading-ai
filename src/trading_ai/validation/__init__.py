"""
Validation modules for the Trading AI system.

Validation components provide news credibility assessment, duplicate detection, and source scoring.
They form the quality control layer that ensures data integrity.
"""

from .news_validator import NewsValidator
from .duplicate_filter import DuplicateFilter
from .credibility_scorer import CredibilityScorer

__all__ = [
    "NewsValidator",
    "DuplicateFilter",
    "CredibilityScorer"
]
