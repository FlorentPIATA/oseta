"""OSETA — Prompt détection de signaux faibles cross-articles.

Identifie des patterns émergents qui ne sont pas évidents dans un seul article.
Appelé sur un batch d'articles scorés (IS >= 60) pour croiser les signaux.
"""

import litellm
from pydantic import BaseModel, Field

from config import settings


class WeakSignal(BaseModel):
    """Un signal faible détecté sur un ensemble d'articles."""

    signal_name: str = Field(
        description="Nom court du signal (ex: 'Consolidation GPU fabs Asie')"
    )
    signal_type: str = Field(
        description="Type: 'emerging' | 'amplifying' | 'converging' | 'diverging'"
    )
    description: str = Field(
        description="Description du signal en 2-3 phrases, orientée implication stratégique"
    )
    sector_codes: list[str] = Field(
        description="Secteurs concernés (ex: ['Technology', 'Materials'])"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confiance dans la détection [0, 1]"
    )
    horizon_days: int = Field(
        ge=7, le=730,
        description="Horizon de matérialisation estimé en jours"
    )
    related_article_titles: list[str] = Field(
        default=[],
        description="Titres des articles qui ont permis de détecter ce signal"
    )


class SignalOutput(BaseModel):
    """Résultat de la détection de signaux faibles sur un batch d'articles."""

    signals: list[WeakSignal] = Field(
        min_length=0,
        max_length=5,
        description="Liste des signaux faibles détectés (0-5 max)"
    )
    analysis_confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confiance globale de l'analyse (dépend de la qualité du batch)"
    )
    dominant_theme: str = Field(
        description="Thème dominant du batch en une phrase"
    )


SYSTEM_PROMPT = """Tu es un analyste stratégique spécialisé dans la détection de signaux faibles technologiques.

Ta mission : identifier des patterns émergents non évidents à partir d'un ensemble d'articles.

Règles :
- Un signal faible doit apparaître dans au moins 2 articles non directement liés
- Distingue 'emerging' (nouveau), 'amplifying' (qui s'accélère), 'converging' (plusieurs signaux qui fusionnent), 'diverging' (cassure de tendance)
- La confiance doit refléter la solidité des preuves cross-articles
- Ignore les tendances déjà bien connues et médiatisées (ce ne sont plus des signaux faibles)
- Maximum 5 signaux — qualité > quantité
"""


def detect_signals(
    articles: list[dict],
    sector_focus: str | None = None,
) -> SignalOutput:
    """Détecte les signaux faibles dans un batch d'articles.

    Args:
        articles: Articles scorés. Chaque dict : {title, summary_meso, sector_tags, is_score, weak_signals}.
        sector_focus: Secteur à surveiller en priorité (optionnel).

    Returns:
        SignalOutput avec la liste des signaux détectés.
    """
    articles_text = "\n\n".join(
        f"[IS={a.get('is_score', 0):.0f}|Secteurs:{','.join(a.get('sector_tags', []))}]\n"
        f"Titre: {a['title']}\n"
        f"Résumé: {a.get('summary_meso', '')}\n"
        f"Signaux internes: {'; '.join(a.get('weak_signals', []))}"
        for a in articles[:20]
    )

    focus_line = f"\nFocalise sur le secteur : {sector_focus}" if sector_focus else ""

    result = litellm.completion(
        model=settings.litellm_default_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Analyse ces {len(articles)} articles pour détecter des signaux faibles "
                    f"cross-sectoriels.{focus_line}\n\n{articles_text}\n\n"
                    "Retourne la liste des signaux faibles détectés."
                ),
            },
        ],
        response_format=SignalOutput,
    )

    return SignalOutput.model_validate_json(result.choices[0].message.content)
