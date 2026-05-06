"""OSETA — Prompt scoring Impact Score (IS).

L'IS mesure l'importance stratégique d'une information.
Seuil d'alerte executive : IS >= 80.
"""

import litellm
from pydantic import BaseModel, Field
from typing import Literal

from config import settings
from models.enums import RiskLevel


class ImpactScoreOutput(BaseModel):
    """Évaluation LLM de l'importance stratégique."""

    strategic_importance_raw: float = Field(
        ge=1, le=10,
        description="Score brut 1-10 de l'importance stratégique avec justification"
    )
    strategic_justification: str = Field(
        description="Justification en 2-3 phrases du score stratégique"
    )
    sectors_impacted_count: int = Field(
        ge=0,
        description="Nombre de secteurs directement ou indirectement impactés"
    )
    has_historical_precedent: bool = Field(
        description="Cette tendance a-t-elle un précédent historique documenté ?"
    )
    historical_reference: str | None = Field(
        default=None,
        description="Référence au précédent historique si applicable"
    )
    risk_level: Literal["low", "moderate", "high", "critical"] = Field(
        description="Niveau de risque global pour les décideurs"
    )
    recommended_action: Literal["monitor", "watch", "alert", "action"] = Field(
        description="Action recommandée: monitor=veille, watch=surveillance accrue, alert=alerte, action=intervention"
    )


SYSTEM_PROMPT = """Tu es un conseiller stratégique senior pour des décideurs technologiques.
Tu évalues l'importance stratégique d'informations pour aider à prioriser l'attention.

Calibration du score stratégique (1-10) :
- 1-3 : Information marginale, impact sectoriel limité
- 4-6 : Information notable, impact sur 1-2 secteurs sur 3-6 mois
- 7-8 : Information importante, impact multi-sectoriel sur 1-2 ans
- 9-10 : Information critique, rupture potentielle, impact systémique

Sois conservateur : les scores 9-10 doivent être rares et vraiment justifiés.
"""


def score_impact(
    article_summary: str,
    sector_tags: list[str],
    entities: list[str],
) -> ImpactScoreOutput:
    """Évalue l'impact stratégique d'un article analysé.

    Args:
        article_summary: Résumé meso de l'article.
        sector_tags: Secteurs identifiés lors de l'analyse.
        entities: Entités clés identifiées.

    Returns:
        ImpactScoreOutput validé.
    """
    user_content = f"""Article (résumé) : {article_summary}
Secteurs impactés : {', '.join(sector_tags)}
Entités clés : {', '.join(entities)}

Évalue l'importance stratégique de cette information."""

    result = litellm.completion(
        model=settings.litellm_default_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        response_format=ImpactScoreOutput,
    )

    return ImpactScoreOutput.model_validate_json(
        result.choices[0].message.content
    )
