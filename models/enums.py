"""OSETA — Enums partagés entre DB et API."""

from enum import StrEnum


class RiskLevel(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class DisruptionLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ArticleStatus(StrEnum):
    RAW = "raw"
    ANALYZED = "analyzed"
    SCORED = "scored"
    PUBLISHED = "published"
    REJECTED = "rejected"


class SectorLevel(StrEnum):
    MACRO = "macro"   # ex: Technology
    MESO = "meso"     # ex: Semiconductors
    MICRO = "micro"   # ex: GPU Fabrication


class LinkType(StrEnum):
    SUPPLY_CHAIN = "supply_chain"
    MACRO = "macro"
    REGULATORY = "regulatory"
    TECH_SPILLOVER = "tech_spillover"


class PredictionStatus(StrEnum):
    PENDING = "pending"
    REALIZED = "realized"
    PARTIAL = "partial"
    FAILED = "failed"


class CorrelationMethod(StrEnum):
    PEARSON = "pearson"
    SPEARMAN = "spearman"
    # Phase 2+ :
    # GRANGER = "granger"
    # TRANSFER_ENTROPY = "transfer_entropy"


class SourceType(StrEnum):
    NEWS = "news"
    FINANCIAL = "financial"
    REGULATORY = "regulatory"
    SOCIAL = "social"
    MACRO = "macro"
    SUPPLY_CHAIN = "supply_chain"
