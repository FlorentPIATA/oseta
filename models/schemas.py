"""OSETA — Schémas Pydantic pour l'API (in/out).

Ces modèles sont utilisés par FastAPI pour la validation des requêtes
et la sérialisation des réponses. Ils sont distincts des modèles DB.
"""

from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl, field_validator
from typing import Any

from models.enums import (
    ArticleStatus, DisruptionLevel, RiskLevel,
    SectorLevel, LinkType, PredictionStatus, CorrelationMethod,
)


# ─────────────────────────────── Articles ────────────────────────────────

class ArticleBase(BaseModel):
    title: str
    url: str
    published_at: datetime | None = None
    sector_tag: str | None = None


class ArticleCreate(ArticleBase):
    content: str
    source_id: int


class ArticleRead(ArticleBase):
    id: int
    status: ArticleStatus
    sentiment_score: float | None = None
    ci_score: float | None = None
    is_score: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ArticleDetailed(ArticleRead):
    content: str | None = None
    llm_analysis: dict[str, Any] | None = None


class ArticleListResponse(BaseModel):
    items: list[ArticleRead]
    total: int
    skip: int
    limit: int


# ─────────────────────────────── Sectors ─────────────────────────────────

class SectorBase(BaseModel):
    code: str
    name: str
    level: SectorLevel = SectorLevel.MACRO


class SectorCreate(SectorBase):
    parent_id: int | None = None


class SectorRead(SectorBase):
    id: int
    parent_id: int | None = None
    volatility_index: float | None = None
    trend_direction: str | None = None

    model_config = {"from_attributes": True}


class CorrelationResult(BaseModel):
    source_sector_id: int
    target_sector_id: int
    source_sector_name: str
    target_sector_name: str
    correlation_coeff: float = Field(ge=-1, le=1)
    lag_days: int = Field(ge=0, le=365)
    strength: float = Field(ge=0, le=1)
    method: CorrelationMethod
    confidence: float = Field(ge=0, le=1)
    is_significant: bool
    link_type: LinkType
    p_value: float | None = None
    computed_at: datetime | None = None


# ─────────────────────────────── Scoring ─────────────────────────────────

class CIScore(BaseModel):
    """Confidence Index — fiabilité de l'information."""
    total: float = Field(ge=0, le=100)
    source_credibility: float = Field(ge=0, le=100)
    cross_source_coherence: float = Field(ge=0, le=100)
    freshness: float = Field(ge=0, le=100)
    contradiction_penalty: float = Field(ge=0, le=1)
    is_published: bool  # CI >= 65


class ISScore(BaseModel):
    """Impact Score — importance stratégique."""
    total: float = Field(ge=0, le=100)
    strategic_importance: float = Field(ge=0, le=100)
    source_diversity: float = Field(ge=0, le=100)
    tech_breadth: float = Field(ge=0, le=100)
    disruptive_potential: float = Field(ge=0, le=100)
    ecosystem_maturity: float = Field(ge=0, le=100)
    risk_level: RiskLevel
    alert_required: bool  # IS >= 80


# ─────────────────────────────── Predictions ─────────────────────────────

class PredictionRead(BaseModel):
    id: int
    sector_id: int
    sector_code: str | None = None
    linked_sector_id: int | None
    linked_sector_code: str | None = None
    prediction_type: str
    horizon_days: int
    confidence_score: float
    predicted_direction: str
    predicted_magnitude: str
    status: PredictionStatus
    realized_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────── Health ──────────────────────────────────

class ComponentStatus(BaseModel):
    name: str
    status: str   # ok | degraded | down
    latency_ms: float | None = None
    detail: str | None = None


class HealthResponse(BaseModel):
    status: str   # ok | degraded | down
    version: str
    environment: str
    components: list[ComponentStatus]
    uptime_seconds: float
