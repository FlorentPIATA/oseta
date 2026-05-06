"""OSETA — Modèles SQLAlchemy (base de données).

Toutes les opérations sont async via asyncpg.
Jamais modifier ce fichier sans créer une migration Alembic.
"""

from datetime import datetime
from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, Numeric, String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, backref, relationship


class Base(DeclarativeBase):
    pass


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)
    type = Column(String(32), nullable=False)   # models.enums.SourceType
    url = Column(Text)
    reliability = Column(Float, default=0.5)    # [0, 1]
    api_endpoint = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    articles = relationship("Article", back_populates="source")


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("sources.id"))
    title = Column(Text, nullable=False)
    content = Column(Text)
    url = Column(Text, unique=True)
    published_at = Column(DateTime(timezone=True))
    sector_tag = Column(String(64))
    sentiment_score = Column(Float)             # [-1, 1]
    status = Column(String(32), default="raw")  # models.enums.ArticleStatus
    llm_analysis = Column(JSONB)
    ci_score = Column(Float)                    # Confidence Index [0, 100]
    is_score = Column(Float)                    # Impact Score [0, 100]
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    source = relationship("Source", back_populates="articles")


class Sector(Base):
    __tablename__ = "sectors"

    id = Column(Integer, primary_key=True)
    code = Column(String(32), unique=True, nullable=False)  # ex: GICS_45
    name = Column(String(128), nullable=False)
    parent_id = Column(Integer, ForeignKey("sectors.id"), nullable=True)
    level = Column(String(16), default="macro")  # models.enums.SectorLevel
    volatility_index = Column(Float)
    trend_direction = Column(String(16))
    metadata_ = Column("metadata", JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    children = relationship("Sector", back_populates="parent", foreign_keys=[parent_id])
    parent = relationship("Sector", back_populates="children", foreign_keys=[parent_id], remote_side=[id])
    links_from = relationship("SectorLink", foreign_keys="SectorLink.source_sector_id")
    links_to = relationship("SectorLink", foreign_keys="SectorLink.target_sector_id")


class SectorLink(Base):
    __tablename__ = "sector_links"

    id = Column(Integer, primary_key=True)
    source_sector_id = Column(Integer, ForeignKey("sectors.id"), nullable=False)
    target_sector_id = Column(Integer, ForeignKey("sectors.id"), nullable=False)
    correlation_coeff = Column(Float)           # Pearson [-1, 1]
    lag_days = Column(Integer, default=0)
    strength = Column(Float)                    # force composite
    link_type = Column(String(32))              # models.enums.LinkType
    method = Column(String(16), default="pearson")
    confidence = Column(Float)                  # [0, 1]
    last_computed_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("source_sector_id", "target_sector_id", "link_type"),
    )


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True)
    sector_id = Column(Integer, ForeignKey("sectors.id"), nullable=False)
    linked_sector_id = Column(Integer, ForeignKey("sectors.id"), nullable=True)
    prediction_type = Column(String(32))        # impact_propagation, trend_reversal
    horizon_days = Column(Integer)
    confidence_score = Column(Float)            # [0, 1]
    predicted_direction = Column(String(16))    # positive, negative, neutral
    predicted_magnitude = Column(String(32))    # low, moderate, high
    features_used = Column(JSONB, default={})
    model_version = Column(String(32))
    status = Column(String(16), default="pending")  # models.enums.PredictionStatus
    realized_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DataStream(Base):
    """Séries temporelles multi-sources (ETF prices, macro indicators)."""

    __tablename__ = "data_streams"

    id           = Column(Integer, primary_key=True)
    time         = Column(DateTime(timezone=True), nullable=False)
    stream_type  = Column(String(32), nullable=False)   # 'etf_price' | 'macro_indicator'
    source_label = Column(String(64), nullable=False)   # 'XLK' | 'DFF'
    sector_id    = Column(Integer, ForeignKey("sectors.id"), nullable=True)
    value        = Column(Numeric(18, 8), nullable=False)
    unit         = Column(String(16))                   # 'USD' | 'percent' | 'index'
    is_stale     = Column(Boolean, default=False)
    fetched_at   = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("time", "source_label", name="uq_datastream_time_label"),
    )


class CorrelationMatrixEntry(Base):
    """Matrice de corrélation pré-calculée (jamais recalculée à la requête)."""

    __tablename__ = "correlation_matrix"

    id           = Column(Integer, primary_key=True)
    computed_at  = Column(DateTime(timezone=True), nullable=False)
    sector_a_id  = Column(Integer, ForeignKey("sectors.id"), nullable=False)
    sector_b_id  = Column(Integer, ForeignKey("sectors.id"), nullable=False)
    correlation  = Column(Numeric(5, 4), nullable=False)   # [-1, 1]
    p_value      = Column(Numeric(10, 8))
    lag_days     = Column(Integer, default=0)
    method       = Column(String(16), default="pearson")
    window_days  = Column(Integer, default=90)
    sample_size  = Column(Integer)

    __table_args__ = (
        UniqueConstraint(
            "computed_at", "sector_a_id", "sector_b_id", "method",
            name="uq_corrmatrix_entry",
        ),
    )
