"""OSETA — Exceptions custom du domaine.

Toutes les erreurs métier dérivent de OsetaError.
Ne jamais lever Exception directement dans les services.
"""


class OsetaError(Exception):
    """Base exception pour toutes les erreurs OSETA."""


class ArticleNotFoundError(OsetaError):
    """Article introuvable en base."""


class SectorNotFoundError(OsetaError):
    """Secteur introuvable en base."""


class AnalysisError(OsetaError):
    """Erreur lors de l'analyse LLM (après 3 retries instructor)."""


class ScoringError(OsetaError):
    """Erreur lors du calcul CI ou IS."""


class CorrelationError(OsetaError):
    """Erreur lors du calcul de corrélation (séries trop courtes, NaN, etc.)."""


class DataFetchError(OsetaError):
    """Erreur lors de la collecte de données externes (API down, rate limit)."""


class CostGuardError(OsetaError):
    """Budget LLM journalier dépassé — hard limit atteinte."""


class CacheError(OsetaError):
    """Erreur Redis non critique (log + fallback silencieux)."""
