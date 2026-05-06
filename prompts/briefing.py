"""OSETA — Prompt génération Executive Brief.

Généré quotidiennement à 06:00 UTC par flows/briefing_job.py.
Format : 400 mots, 3-5 bullets d'implication stratégique.
"""

import litellm
from pydantic import BaseModel, Field

from config import settings


class BriefingOutput(BaseModel):
    """Structure du briefing exécutif quotidien."""

    headline: str = Field(
        description="Titre du briefing (max 10 mots, orienté décision)"
    )
    executive_summary: str = Field(
        description="Résumé exécutif en 3-4 phrases, langage orienté décision, ~150 mots"
    )
    key_implications: list[str] = Field(
        min_length=3,
        max_length=5,
        description="3 à 5 implications stratégiques actionnables pour les décideurs IT"
    )
    top_technologies: list[str] = Field(
        max_length=5,
        description="Top 3-5 technologies à surveiller cette semaine"
    )
    risk_alert: str | None = Field(
        default=None,
        description="Alerte de risque si IS >= 80 détecté, sinon None"
    )
    recommended_reading: list[str] = Field(
        default=[],
        description="Titres des 2-3 articles les plus importants à lire en priorité"
    )


SYSTEM_PROMPT = """Tu es l'assistant stratégique d'un CTO.
Tu produis des briefings exécutifs concis et actionnables sur les technologies émergentes.

Style obligatoire :
- Langage direct, orienté décision ("Il faut surveiller...", "Opportunité à saisir...", "Risque identifié...")
- Pas de jargon marketing, pas de superlatifs sans données
- Chaque implication doit suggérer une action concrète
- Le public : DSI, CTO, architectes systèmes seniors
"""


def generate_briefing(
    top_articles: list[dict],
    date_str: str,
    sector_focus: str | None = None,
) -> BriefingOutput:
    """Génère le briefing exécutif à partir des articles du jour.

    Args:
        top_articles: Liste des articles triés par IS décroissant.
                      Chaque article : {title, summary_meso, sector_tags, is_score}
        date_str: Date du briefing au format "YYYY-MM-DD".
        sector_focus: Secteur spécifique à mettre en avant (optionnel).

    Returns:
        BriefingOutput structuré et validé.
    """
    articles_text = "\n\n".join(
        f"[IS={a.get('is_score', 0):.0f}] {a['title']}\n{a.get('summary_meso', '')}"
        for a in top_articles[:10]
    )

    focus_instruction = (
        f"\nMets particulièrement en avant le secteur : {sector_focus}"
        if sector_focus else ""
    )

    user_content = f"""Date : {date_str}{focus_instruction}

Articles du jour (classés par importance décroissante) :

{articles_text}

Génère le briefing exécutif."""

    result = litellm.completion(
        model=settings.litellm_default_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        response_format=BriefingOutput,
    )

    return BriefingOutput.model_validate_json(
        result.choices[0].message.content
    )
