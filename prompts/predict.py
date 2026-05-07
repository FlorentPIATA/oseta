"""OSETA — Prompt génération prédictions depuis corrélations significatives."""

import litellm
from pydantic import BaseModel, Field

from config import settings


class PredictionItem(BaseModel):
    """Une prédiction actionnable dérivée d'une corrélation avec lag."""

    sector_code: str = Field(description="Code ETF du secteur cible (ex: XLI)")
    linked_sector_code: str | None = Field(
        default=None,
        description="Code ETF du secteur leadeur — à renseigner pour les lag_signal",
    )
    prediction_type: str = Field(
        description=(
            "'lag_signal' (leadeur prédit suiveur via lag connu), "
            "'trend_reversal' (inversion probable), "
            "'impact_propagation' (propagation d'un choc)"
        )
    )
    horizon_days: int = Field(
        ge=1,
        le=90,
        description="Horizon en jours — doit être ≈ lag_days pour les lag_signal",
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Confiance basée sur |r| et p-value : |r|≥0.8 et p<0.001 → ≥0.85",
    )
    predicted_direction: str = Field(
        description="'positive', 'negative', ou 'neutral'",
    )
    predicted_magnitude: str = Field(
        description="'low' (|r|<0.5), 'moderate' (0.5≤|r|<0.7), 'high' (|r|≥0.7)",
    )
    rationale: str = Field(
        description="Justification en 1-2 phrases — doit citer r= et lag= explicitement",
    )


class PredictionListOutput(BaseModel):
    """Liste structurée de prédictions actionnables."""

    predictions: list[PredictionItem] = Field(
        min_length=1,
        max_length=5,
        description="1 à 5 prédictions triées par confidence_score décroissant",
    )


_SYSTEM_PROMPT = """Tu es un analyste quantitatif spécialisé en relations inter-sectorielles ETF.
Tu génères des prédictions courtes et actionnables, directement dérivées des données de corrélation.

Règles absolues :
- Chaque prédiction DOIT être justifiable par une corrélation listée (cite r= et lag=)
- horizon_days ≈ lag_days pour les lag_signal (± 3 jours)
- confidence_score suit |r| et p-value : |r|≥0.8 → ≥0.80, |r|<0.5 → ≤0.55
- predicted_magnitude : low (|r|<0.5), moderate (0.5≤|r|<0.7), high (|r|≥0.7)
- Si les données sont insuffisantes, génère moins de prédictions mais ne spécule pas
- Maximum 5 prédictions — qualité > quantité
"""


def generate_predictions(
    correlations: list[dict],
    date_str: str,
) -> PredictionListOutput:
    """Génère des prédictions actionnables depuis les corrélations significatives.

    Args:
        correlations: Corrélations sig. triées par |r| desc.
                      Chaque item: {sector_a_code, sector_b_code, r, lag_days, p_value, window_days}
        date_str: Date d'analyse (YYYY-MM-DD).

    Returns:
        PredictionListOutput avec 1-5 prédictions structurées.
    """
    corr_lines = "\n".join(
        f"  {c['sector_a_code']} → {c['sector_b_code']}: "
        f"r={c['r']:+.3f}  lag={c['lag_days']}d  "
        f"p={c['p_value']:.4f if c['p_value'] is not None else 'n/a'}  "
        f"window={c.get('window_days', 90)}d"
        for c in correlations[:10]
    )

    result = litellm.completion(
        model=settings.litellm_default_model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Date : {date_str}\n\n"
                    f"Corrélations significatives (|r| ≥ 0.5, lag ≥ 3j, p < 0.05) :\n"
                    f"{corr_lines}\n\n"
                    "Génère les prédictions."
                ),
            },
        ],
        response_format=PredictionListOutput,
    )

    return PredictionListOutput.model_validate_json(
        result.choices[0].message.content
    )
