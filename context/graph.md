# OSETA — Codebase Graph
> Généré le 2026-05-06 | `cd frontend && npm run graph` pour régénérer
> Lire EN PREMIER dans chaque session — backend + frontend en un coup d'œil.

## INVARIANTS CRITIQUES
```
Config       : from config import settings  (JAMAIS os.environ directement)
Logs         : from loguru import logger  (JAMAIS print())
DB           : toutes les queries sont async (AsyncSession + await)
LLM output   : TOUJOURS via instructor + Pydantic  (ZÉRO parsing JSON manuel)
Prompts      : TOUJOURS dans prompts/*.py  (jamais inline dans les services)
Exceptions   : TOUJOURS depuis services/exceptions.py  (OsetaError hierarchy)
Migrations   : alembic revision --autogenerate  (jamais CREATE TABLE manuel)
Taille max   : 200 lignes par fichier Python  (découper si dépassé)
LLM default  : gpt-4o-mini  | premium (IS > 80) : gpt-4o  | budget : 50 USD/jour
CI publish   : CI ≥ 65  | IS alert : IS ≥ 80  | CP action : CP ≥ 80
```

## ARCHITECTURE
```
Backend  : FastAPI + Python 3.12 | SQLAlchemy 2.0 async | asyncpg | PostgreSQL 15
LLM      : LiteLLM + instructor + Pydantic v2 | Prefect 2.x | Redis TTL
Frontend : React 18 + Vite + TypeScript strict | TanStack Query | Recharts
Pipeline : collect → analyze (LLM) → score (CI/IS) → correlate → publish briefing
Cron     : correlation-weekly (lundi 04:00 UTC) | briefing-daily (06:00 UTC)
Ports    : API :8000 | Frontend :5173 | Prefect UI :4200 | Grafana :3001
```

## SERVICES (9)
  analyzer: { analyze_article }
  cache: { get_redis, cache_get, cache_set, cache_delete, key_correlation_matrix, key_sector_graph }
  collector: { collect_sector_articles }
  correlation_store: { load_sector_series, get_latest_matrix, run_correlation_job }
  correlator: { compute_correlation, find_optimal_lag, compute_correlation_matrix }
  data_fetcher: { fetch_and_store_etfs, fetch_and_store_fred }
  database: { get_session }
  exceptions
  scorer: { compute_ci, compute_is }

## ROUTES API (5)
  articles:
    (aucune route détectée)
  correlations:
    [GET] /correlations/matrix
    [POST] /correlations/refresh
  health:
    [GET] /health
  predictions:
    (aucune route détectée)
  sectors:
    (aucune route détectée)

## FLOWS PREFECT (2)
  correlation_job: { flow: correlation_flow | tasks: task_fetch_etfs, task_fetch_fred, task_compute_matrix }
  runner

## PROMPTS LLM (3)
  analyze: { output: ArticleAnalysisOutput | fn: analyze_article }
  briefing: { output: BriefingOutput | fn: generate_briefing }
  score_impact: { output: ImpactScoreOutput | fn: score_impact }

## MODELS (3)
  db (SQLAlchemy): { Source, Article, Sector, SectorLink, Prediction, DataStream, CorrelationMatrixEntry }
  enums: { RiskLevel, DisruptionLevel, ArticleStatus, SectorLevel, LinkType, PredictionStatus, CorrelationMethod, SourceType }
  schemas (Pydantic): { ArticleBase, ArticleListResponse, SectorBase, CorrelationResult, CIScore, ISScore, PredictionRead, ComponentStatus, HealthResponse }

## FRONTEND (8 fichiers)
  [hooks]
    useCorrelationMatrix: { useCorrelationMatrix, buildMatrixLookup }
  [components]
    CorrelationHeatmap: { CorrelationHeatmap }
    HeatmapControls: { HeatmapControls }
  [types]
    correlation: { HeatmapCell, HeatmapResponse, MatrixFilters, CorrelationMethod }
  App
  correlations: { fetchCorrelationMatrix }

## FLOWS

**Pipeline quotidien**
daily_pipeline.py → collect → analyze (LLM) → score (CI/IS) → publish

**Corrélation hebdomadaire** (lundi 04:00 UTC)
correlation_job.py → fetch ETFs Alpha Vantage (~2min, 13s/call) + FRED → compute_correlation_matrix()
→ persistence correlation_matrix_entries | GET /correlations/matrix → heatmap React

**Briefing quotidien** (06:00 UTC)
briefing_job.py → top scored articles → prompts/briefing.py (BriefingOutput) → PublishedArticle

**Refresh manuel**
POST /correlations/refresh + X-Master-Key header → run_correlation_job() immédiat

## DB TABLES (PostgreSQL 15)
```
articles                    id, title, content, url, source_type, status, published_at, created_at
sectors                     id, code, name, level(macro|meso|micro), parent_id
sector_links                sector_a_id, sector_b_id, link_type, strength
data_streams                time, stream_type, source_label, sector_id, value, unit, is_stale
correlation_matrix_entries  sector_a_id, sector_b_id, correlation, p_value, lag_days, method, window_days, computed_at
predictions                 id, sector_id, title, predicted_at, horizon_days, status, created_at
```

## EXTERNAL APIS
```
Alpha Vantage : ETFs SPDR (XLK XLF XLE XLV XLI XLB XLU XLC XLRE) | 5 calls/min | 13s delay
FRED          : DFF / DGS10 / CPIAUCSL / UMCSENT | fredapi sync + run_in_executor
LiteLLM       : gpt-4o-mini (default) / gpt-4o (IS>80) | instructor retry ×3
Brave / Bing  : news search (brave_api_key / bing_api_key)
EventRegistry : structured news (eventregistry_api_key)
```
