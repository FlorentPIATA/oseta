"""OSETA — Moteur de scoring CI + IS.

Confidence Index (CI) : fiabilité de l'information [0, 100].
Impact Score (IS) : importance stratégique [0, 100].

Formules transparentes et auditables (§3.3 du CDC).
"""

import math
from datetime import datetime, timezone

from models.schemas import CIScore, ISScore
from models.enums import RiskLevel
from prompts.analyze import ArticleAnalysisOutput
from prompts.score_impact import ImpactScoreOutput


# ────────────────────────── Confidence Index ─────────────────────────────

def compute_ci(
    source_reliability: float,          # [0, 1] — reliabilité de la source
    cross_source_count: int,            # nombre de sources indépendantes
    published_at: datetime | None,
    has_contradiction: bool = False,
    has_primary_source: bool = True,
    source_age_days: int = 365,         # âge de la source en jours (< 90 = pénalité)
) -> CIScore:
    """Calcule le Confidence Index selon la grille OSETA™.

    Args:
        source_reliability: Score de fiabilité historique [0,1].
        cross_source_count: Nb de sources indépendantes (sans filiation).
        published_at: Date de publication de l'article.
        has_contradiction: True si contradiction détectée cross-source.
        has_primary_source: False si aucune source primaire vérifiable.
        source_age_days: Âge de la source en jours.

    Returns:
        CIScore avec détail par sous-critère.
    """
    # Poids CDC §3.3.1
    W_SOURCE_CRED = 0.30
    W_CROSS_SOURCE = 0.25
    W_FRESHNESS = 0.20
    W_CONTRADICTION = 0.15
    W_REPEATABILITY = 0.10

    # Crédibilité source [0, 100]
    source_cred = source_reliability * 100

    # Cohérence cross-source [0, 100] — racine carrée pour décroissance marginale
    cross_coherence = min(100, math.sqrt(max(0, cross_source_count)) * 50)

    # Fraîcheur [0, 100] — demi-vie 30 jours
    if published_at:
        now = datetime.now(timezone.utc)
        age_days = max(0, (now - published_at.replace(tzinfo=timezone.utc)).days)
        freshness = 100 * math.exp(-age_days / 43.3)  # demi-vie 30j
    else:
        freshness = 30.0  # article sans date = pénalité

    # Contradictions [0, 1] — pénalité directe
    contradiction_penalty = 0.60 if has_contradiction else 0.0

    # Répétabilité / source primaire [0, 100]
    repeatability = 100.0 if has_primary_source else 40.0

    # Score brut
    raw_score = (
        W_SOURCE_CRED * source_cred
        + W_CROSS_SOURCE * cross_coherence
        + W_FRESHNESS * freshness
        + W_REPEATABILITY * repeatability
    )

    # Application pénalité contradiction
    raw_score *= (1 - W_CONTRADICTION * contradiction_penalty)

    # Pénalité source nouvelle (< 90 jours)
    if source_age_days < 90:
        raw_score *= 0.5

    # Règle d'or : sans source primaire, CI max = 50
    if not has_primary_source:
        raw_score = min(50.0, raw_score)

    total = round(min(100.0, max(0.0, raw_score)), 2)

    return CIScore(
        total=total,
        source_credibility=round(source_cred, 2),
        cross_source_coherence=round(cross_coherence, 2),
        freshness=round(freshness, 2),
        contradiction_penalty=contradiction_penalty,
        is_published=total >= 65.0,
    )


# ─────────────────────────── Impact Score ────────────────────────────────

def compute_is(
    llm_output: ImpactScoreOutput,
    sector_tags: list[str],
    source_domains: list[str],
) -> ISScore:
    """Calcule l'Impact Score depuis la sortie LLM et les métadonnées.

    Args:
        llm_output: Sortie du prompt score_impact.py.
        sector_tags: Secteurs identifiés.
        source_domains: Domaines des sources utilisées (diversité).

    Returns:
        ISScore avec détail par sous-critère.
    """
    # Poids CDC §3.3.2
    W_STRATEGIC = 0.25
    W_SOURCE_DIV = 0.20
    W_TECH_BREADTH = 0.20
    W_DISRUPTIVE = 0.20
    W_MATURITY = 0.15

    # Importance stratégique [0, 100] — LLM score 1-10 → 0-100
    strategic = (llm_output.strategic_importance_raw / 10) * 100

    # Diversité sources — entropie de Shannon normalisée
    unique_domains = len(set(source_domains))
    source_diversity = min(100, unique_domains * 20)

    # Portée technologique — nb secteurs
    tech_breadth = min(100, len(sector_tags) * 20)

    # Potentiel disruptif — basé sur le niveau de disruption
    disruption_map = {"low": 25, "medium": 50, "high": 75, "critical": 100}
    disruptive = disruption_map.get(
        llm_output.recommended_action.replace("action", "critical")
        .replace("alert", "high")
        .replace("watch", "medium")
        .replace("monitor", "low"),
        50,
    )

    # Maturité écosystème — inverse (novice = impact fort)
    maturity_inverse = 80 if not llm_output.has_historical_precedent else 40

    total = (
        W_STRATEGIC * strategic
        + W_SOURCE_DIV * source_diversity
        + W_TECH_BREADTH * tech_breadth
        + W_DISRUPTIVE * disruptive
        + W_MATURITY * maturity_inverse
    )
    total = round(min(100.0, max(0.0, total)), 2)

    risk_map = {
        "low": RiskLevel.LOW,
        "moderate": RiskLevel.MODERATE,
        "high": RiskLevel.HIGH,
        "critical": RiskLevel.CRITICAL,
    }

    return ISScore(
        total=total,
        strategic_importance=round(strategic, 2),
        source_diversity=round(source_diversity, 2),
        tech_breadth=round(tech_breadth, 2),
        disruptive_potential=round(disruptive, 2),
        ecosystem_maturity=round(maturity_inverse, 2),
        risk_level=risk_map.get(llm_output.risk_level, RiskLevel.MODERATE),
        alert_required=total >= 80.0,
    )
