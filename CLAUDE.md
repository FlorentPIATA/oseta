# OSETA — Contexte pour Claude

Observatory for Strategic Emerging Technologies & Analytics  
Version : 2.1 (Annexe B — stack optimisé vibe coding)

---

## Stack technique — NE JAMAIS proposer de migration

| Couche | Technologie | Jamais remplacer par |
|--------|-------------|----------------------|
| Backend | FastAPI + Python 3.12 | Flask, Django |
| DB relationnelle | PostgreSQL 15 (async via asyncpg) | SQLite, MySQL |
| ORM | SQLAlchemy 2.0 async | Tortoise, Peewee |
| Migrations | Alembic | migration manuelle |
| LLM abstraction | LiteLLM | SDK OpenAI/Gemini directs |
| LLM structured output | instructor + Pydantic v2 | parsing JSON manuel |
| Orchestration | Prefect 2.x | Celery, Airflow |
| Cache | Redis (TTL simple) | pub/sub, Redis Cluster |
| Frontend | React 18 + Vite + TypeScript strict | Next.js, CRA |
| Styling | Tailwind CSS (core utils only) | CSS-in-JS, styled-components |
| State | Zustand | Redux, Recoil |
| API client | TanStack Query (React Query) | SWR, Apollo |
| Graphes | Cytoscape.js | D3 pour les graphes |
| Charts | Recharts | Chart.js |
| Contenerisation | Docker Compose | Kubernetes (prévu V3 uniquement) |
| CI/CD | GitHub Actions | Jenkins, CircleCI |

---

## Conventions impératives (à respecter sur TOUS les fichiers)

### Python
- **Max 200 lignes par fichier** — si ça dépasse, découper en sous-module
- Toutes les fonctions ont des type hints complets (aucune exception)
- Return type toujours explicite
- Docstring sur toutes les fonctions publiques (format Google style)
- Pas de `print()` — utiliser `loguru` uniquement
- Toutes les opérations DB sont `async`
- Les erreurs sont des exceptions custom définies dans `services/exceptions.py`

### LLM calls (règle absolue)
- **ZÉRO parsing JSON manuel** — toutes les sorties LLM passent par `instructor`
- Chaque call LLM a un modèle Pydantic de sortie dans `prompts/`
- Budget hard limit : COST_GUARD vérifie le token count avant chaque call
- Retry automatique via `instructor` (max 3 tentatives)

### Base de données
- Toutes les queries sont async
- Les modèles SQLAlchemy sont dans `models/db.py`
- Les schémas Pydantic (API) sont dans `models/schemas.py`
- Migrations Alembic obligatoires — jamais de `CREATE TABLE` manuel

### Frontend
- TypeScript strict mode — `noImplicitAny: true`
- Pas de `any` — utiliser `unknown` + type guards
- Composants fonctionnels uniquement
- Props typées avec interfaces explicites

---

## Architecture des modules

```
services/collector.py    → Ingestion sources → retourne List[RawArticle]
services/analyzer.py     → Analyse LLM → retourne AnalyzedArticle
services/scorer.py       → Scores CI/IS → retourne ScoredArticle
services/correlator.py   → Pearson/Spearman entre secteurs → CorrelationResult
services/publisher.py    → Génération articles/briefings → PublishedArticle
services/exceptions.py   → Exceptions custom du domaine

prompts/analyze.py       → Prompt analyse article + ArticleAnalysisOutput
prompts/score_impact.py  → Prompt scoring IS + ImpactScoreOutput
prompts/signals.py       → Prompt détection signaux faibles + SignalOutput
prompts/briefing.py      → Prompt génération briefing + BriefingOutput

models/db.py             → Modèles SQLAlchemy (DB)
models/schemas.py        → Modèles Pydantic (API in/out)
models/enums.py          → Enums partagés

routes/articles.py       → /articles CRUD + /articles/{id}/analyze
routes/sectors.py        → /sectors + /sectors/{id}/correlations
routes/predictions.py    → /predictions + track record
routes/health.py         → /health (détaillé pour monitoring)

flows/daily_pipeline.py  → Flow Prefect principal (collect→analyze→score→publish)
flows/correlation_job.py → Flow recalcul matrice corrélation (hebdo)
flows/briefing_job.py    → Flow génération Executive Brief (06:00 UTC)
```

---

## Variables d'environnement disponibles

Voir `.env.example` pour la liste complète.  
Toujours utiliser `settings.py` (Pydantic BaseSettings) — jamais `os.environ` directement.

---

## Ce que ce projet NE fait PAS (MVP + V1)

- ❌ Granger Causality, Transfer Entropy, CCM (Phase 2+ seulement)
- ❌ Kubernetes (Docker Compose uniquement)
- ❌ Redis pub/sub (TTL simple uniquement)
- ❌ Scraping illégal (yfinance unofficial, pytrends) — sources licites uniquement
- ❌ SQLite (PostgreSQL dès J1)
- ❌ Parsing JSON LLM manuel
- ❌ Prompts LLM inline dans le code (tout dans `prompts/`)
- ❌ Fichiers > 200 lignes

---

## Commandes utiles

```bash
# Démarrer la stack complète
docker compose up -d

# Appliquer les migrations
docker compose exec api alembic upgrade head

# Lancer les tests
docker compose exec api pytest tests/ -v

# Voir les logs API en temps réel
docker compose logs -f api

# Accéder à Prefect UI
open http://localhost:4200

# Accéder à Grafana
open http://localhost:3001  # admin/admin
```

---

## Comment demander de l'aide à Claude

Pour chaque nouveau fichier, donne ce contexte :
1. "Lis CLAUDE.md" (ou colle le contenu)
2. "Lis models/schemas.py" (les types que le fichier utilise)
3. "Génère [fichier cible]"

Exemple : "Lis CLAUDE.md et models/schemas.py, génère services/analyzer.py complet"

## Skill routing

When the user's request matches an available skill, invoke it via the Skill tool. When in doubt, invoke the skill.

Key routing rules:
- Product ideas/brainstorming → invoke /office-hours
- Strategy/scope → invoke /plan-ceo-review
- Architecture → invoke /plan-eng-review
- Design system/plan review → invoke /design-consultation or /plan-design-review
- Full review pipeline → invoke /autoplan
- Bugs/errors → invoke /investigate
- QA/testing site behavior → invoke /qa or /qa-only
- Code review/diff check → invoke /review
- Visual polish → invoke /design-review
- Ship/deploy/PR → invoke /ship or /land-and-deploy
- Save progress → invoke /context-save
- Resume context → invoke /context-restore
