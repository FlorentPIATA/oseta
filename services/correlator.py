"""OSETA — Moteur de corrélation inter-sectorielle.

MVP : Pearson + Spearman avec lag detection.
Phase 2+ : Granger Causality, Transfer Entropy (voir TODO).

Règle : fonctions courtes, types explicites, testables unitairement.
"""

import math
from dataclasses import dataclass

import numpy as np
from scipy.stats import pearsonr, spearmanr
from loguru import logger

from models.enums import CorrelationMethod


# ─────────────────────── Types internes ──────────────────────────────────

@dataclass
class LagResult:
    """Résultat du calcul de lag optimal entre deux séries."""
    optimal_lag_days: int
    max_correlation: float
    confidence: float   # stabilité du lag


@dataclass
class RawCorrelation:
    """Corrélation brute avant enrichissement avec métadonnées secteur."""
    coefficient: float
    p_value: float
    method: CorrelationMethod
    is_significant: bool
    lag_days: int


# ─────────────────────── Fonctions core ──────────────────────────────────

MIN_SERIES_LENGTH = 30  # minimum pour une corrélation valide


def compute_correlation(
    series_a: list[float],
    series_b: list[float],
    method: CorrelationMethod = CorrelationMethod.PEARSON,
) -> RawCorrelation:
    """Calcule la corrélation entre deux séries temporelles alignées.

    Args:
        series_a: Série temporelle du secteur A (quotidienne, index 0=J-N).
        series_b: Série temporelle du secteur B (même longueur que A).
        method: Méthode de corrélation (Pearson ou Spearman).

    Returns:
        RawCorrelation avec coefficient, p-value et significativité.
    """
    n = min(len(series_a), len(series_b))

    if n < MIN_SERIES_LENGTH:
        logger.warning(f"Series too short ({n} < {MIN_SERIES_LENGTH}), returning null correlation")
        return RawCorrelation(
            coefficient=0.0,
            p_value=1.0,
            method=method,
            is_significant=False,
            lag_days=0,
        )

    a = np.array(series_a[:n])
    b = np.array(series_b[:n])

    # Supprimer les NaN par paires
    mask = ~(np.isnan(a) | np.isnan(b))
    a, b = a[mask], b[mask]

    if len(a) < MIN_SERIES_LENGTH:
        return RawCorrelation(0.0, 1.0, method, False, 0)

    if method == CorrelationMethod.PEARSON:
        coeff, p_value = pearsonr(a, b)
    else:
        coeff, p_value = spearmanr(a, b)

    return RawCorrelation(
        coefficient=float(coeff),
        p_value=float(p_value),
        method=method,
        is_significant=float(p_value) < 0.05,
        lag_days=0,
    )


def find_optimal_lag(
    series_leading: list[float],
    series_lagging: list[float],
    max_lag_days: int = 90,
) -> LagResult:
    """Identifie le décalage temporel optimal entre deux séries.

    Le 'leading sector' est celui dont les mouvements anticipent ceux du 'lagging'.
    Exemple : Semiconductor Equipment → Data Center Construction (lag ~90 jours).

    Args:
        series_leading: Série du secteur leader (observé en premier).
        series_lagging: Série du secteur suiveur (réagit après).
        max_lag_days: Lag maximum à tester (ne pas dépasser 180 pour MVP).

    Returns:
        LagResult avec lag optimal et confiance.
    """
    a = np.array(series_leading)
    b = np.array(series_lagging)

    best_lag = 0
    best_corr = 0.0
    correlations_by_lag: dict[int, float] = {}

    for lag in range(0, min(max_lag_days, len(a) - MIN_SERIES_LENGTH)):
        a_shifted = a[lag:]
        b_aligned = b[:len(a_shifted)]

        if len(a_shifted) < MIN_SERIES_LENGTH:
            break

        try:
            coeff, p_value = pearsonr(a_shifted, b_aligned)
            if p_value < 0.05:  # garder seulement les corrélations significatives
                correlations_by_lag[lag] = abs(float(coeff))
                if abs(float(coeff)) > best_corr:
                    best_corr = abs(float(coeff))
                    best_lag = lag
        except Exception:
            continue

    # Confiance = stabilité du lag (faible variance autour du lag optimal)
    lags_above_threshold = [
        lag for lag, corr in correlations_by_lag.items()
        if corr >= best_corr * 0.9
    ]
    confidence = 1.0 - (len(lags_above_threshold) / max(max_lag_days, 1))
    confidence = max(0.0, min(1.0, confidence))

    return LagResult(
        optimal_lag_days=best_lag,
        max_correlation=best_corr,
        confidence=confidence,
    )


def compute_correlation_matrix(
    sector_series: dict[str, list[float]],
    method: CorrelationMethod = CorrelationMethod.PEARSON,
) -> dict[tuple[str, str], RawCorrelation]:
    """Calcule la matrice de corrélation pour N secteurs.

    Complexité : O(n²) — utilisé en batch hebdomadaire, pas en temps réel.

    Args:
        sector_series: Dict {sector_code: [valeurs quotidiennes]}.
        method: Méthode de corrélation.

    Returns:
        Dict {(sector_a, sector_b): RawCorrelation} pour toutes les paires.
    """
    codes = list(sector_series.keys())
    results: dict[tuple[str, str], RawCorrelation] = {}

    for i, code_a in enumerate(codes):
        for code_b in codes[i + 1:]:
            result = compute_correlation(
                sector_series[code_a],
                sector_series[code_b],
                method,
            )
            results[(code_a, code_b)] = result
            logger.debug(f"Correlation {code_a}↔{code_b}: r={result.coefficient:.3f} p={result.p_value:.4f}")

    return results

    # TODO Phase 2+ : ajouter Granger Causality ici
    # from statsmodels.tsa.stattools import grangercausalitytests
    # Nécessite 6+ mois de données et stationnarité des séries
