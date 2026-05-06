"""OSETA — Prompt d'analyse d'article.

Utilise instructor pour garantir une sortie Pydantic valide.
Modifier le SYSTEM_PROMPT ici pour itérer sur la qualité.
"""

import instructor
import litellm
from pydantic import BaseModel, Field
from typing import Literal

from config import settings


# ─────────────────────── Schéma de sortie LLM ────────────────────────────

class ArticleAnalysisOutput(BaseModel):
    """Sortie structurée de l'analyse LLM — validée par instructor."""

    summary_micro: str = Field(
        description="Résumé en 1 phrase max, 20 mots max"
    )
    summary_meso: str = Field(
        description="Résumé en 3-5 phrases, factuel, sans opinion"
    )
    key_entities: list[str] = Field(
        description="Entreprises, personnes, technologies citées (noms exacts du texte)"
    )
    sector_tags: list[str] = Field(
        description="Secteurs économiques impactés (ex: 'Energy Storage', 'Automotive', 'Grid Infrastructure')",
        min_length=1,
        max_length=5,
    )
    sentiment: float = Field(
        ge=-1, le=1,
        description="Sentiment global: -1 très négatif, 0 neutre, 1 très positif"
    )
    disruption_level: Literal["low", "medium", "high", "critical"] = Field(
        description="Niveau de disruption potentielle pour les secteurs identifiés"
    )
    leading_indicators: list[str] = Field(
        default=[],
        description="Indicateurs avancés détectés (ex: 'hausse des offres d'emploi ML', 'dépôts de brevets')"
    )
    weak_signals: list[str] = Field(
        default=[],
        description="Signaux faibles ou mentions inattendues cross-secteur"
    )
    confidence: float = Field(
        ge=0, le=1,
        description="Confiance dans l'analyse (0=incertain, 1=très confiant)"
    )
    manipulation_warning: bool = Field(
        default=False,
        description="True si le texte présente des marqueurs de manipulation (hyperbole, urgence artificielle)"
    )


# ─────────────────────── Prompt templates ────────────────────────────────

SYSTEM_PROMPT = """Tu es un analyste stratégique senior spécialisé dans les technologies émergentes.
Tu analyses des articles pour détecter leur impact trans-sectoriel.

Règles strictes :
- Sois factuel, cite uniquement ce qui est dans le texte
- Ne pas inventer d'informations, d'entités ou de chiffres absents du texte
- Pour les sector_tags, utilise des termes en anglais standardisés (GICS-like)
- Pour leading_indicators, ne citer que des signaux mesurables et vérifiables
- Si le texte est vide, court ou de mauvaise qualité, retourne confidence=0
"""

# ─────────────────────── Client instructor ───────────────────────────────

def _get_client() -> instructor.Instructor:
    """Crée un client instructor via LiteLLM."""
    litellm_client = litellm.LiteLLM()
    return instructor.from_litellm(litellm.completion)


# ─────────────────────── Fonction principale ─────────────────────────────

def analyze_article(
    content: str,
    title: str = "",
    use_premium: bool = False,
) -> ArticleAnalysisOutput:
    """Analyse un article via LLM et retourne une sortie Pydantic validée.

    Args:
        content: Contenu textuel de l'article.
        title: Titre de l'article (contexte additionnel).
        use_premium: Si True, utilise le modèle premium (IS > 80 attendu).

    Returns:
        ArticleAnalysisOutput validé par instructor (max 3 retries auto).

    Raises:
        instructor.exceptions.InstructorRetryException: Après 3 échecs.
    """
    model = (
        settings.litellm_premium_model
        if use_premium
        else settings.litellm_default_model
    )

    user_content = f"Titre : {title}\n\nContenu :\n{content[:4000]}"

    result = litellm.completion(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        response_format=ArticleAnalysisOutput,
    )

    return ArticleAnalysisOutput.model_validate_json(
        result.choices[0].message.content
    )
