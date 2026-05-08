# OSETA — TODO

## Deployment (Next — 48-hour plan)

- [x] **AUDIT GATE** — GO ✅. 5/6 findings pass. Hero: XLF→XLI +0.82 lag=21d. Also: XLK→XLRE +0.72 lag=24d, XLE→XLRE -0.61 lag=18d. Reddit hook: "Financial stocks have been leading industrials by ~3 weeks (r=0.82, p<0.0001)".
- [x] `render.yaml` — Render deployment config: web service (oseta-api) + cron service (oseta-daily-pipeline, 0 5 * * *)
- [x] `main.py` — remove `Base.metadata.create_all` from lifespan (Alembic is sole schema authority)
- [x] `services/database.py` — explicit pool: `pool_size=3, max_overflow=2, pool_timeout=30, pool_recycle=1800`
- [x] `models/schemas.py` — add `p_value: float | None` and `computed_at: datetime` to `CorrelationResult`
- [x] `scripts/run_pipeline.py` — thin script calling service layer directly (no Prefect), used by Render cron
- [x] `scripts/smoke_test.py` — deployed API verification (hits /health, /correlations/matrix, asserts ≥3 significant lag correlations)
- [x] `tests/test_run_pipeline.py` — subprocess test: exits 0 + ≥1 CorrelationMatrixEntry written
- [x] Frontend: insight card component above heatmap (top is_significant=true, lag_days>0 result; shows p_value, computed_at; empty state: "Correlations updating — check back after 05:00 UTC")
- [ ] Register `/health` on cron-job.org (free) — keep Render free tier warm between cron runs
- [ ] Seed 90 days ETF data for 6 sectors (XLK, XLF, XLE, XLV, XLI, XLB)
- [x] Run `scripts/smoke_test.py` against deployed URL — all assertions pass before Reddit post

## Deferred (after first user signal)

- [ ] **TODO: Insight card empty state** — `if (!data || data.length === 0)` → show "Correlations updating — check back after 05:00 UTC". Build during Hour 16-24 with the component.
- [ ] **TODO: Pipeline failure alerting** — if Alpha Vantage key expires, cron job silently produces 0 articles. Add Render email alert on service failure or log-stream monitoring.
- [ ] **TODO: HTTP cache headers on /correlations/matrix** — `Cache-Control: public, max-age=3600` + ETag on computed_at. Prevents Neon connection exhaustion under Reddit traffic spike.

## UX Fixes — Frontend (audit 2026-05-07)

### P0 — Bloqueurs hiérarchie / navigation

- [x] **[UX-P0-1]** Déplacer `<PipelinePanel />` en bas de page (après TrackRecord) ou en drawer depuis une icône gear dans le header — admin ne doit pas s'afficher avant Signal of the Day
- [x] **[UX-P0-2]** Ajouter nav sticky par ancres de section (Top Signal · Graph · Heatmap · Signals · Predictions) avec scroll-spy — sur mobile : pill nav horizontale sous le header

### P1 — Friction mesurable

- [x] **[UX-P1-3]** Réécrire App.tsx en Tailwind responsive — remplacer l'objet `S` + inline styles par classes (`grid grid-cols-1 md:grid-cols-2`, `max-w-4xl mx-auto px-5 md:px-10`, etc.)
- [x] **[UX-P1-4]** LeadGraph : remplacer les 6 hex hardcodés par CSS vars via `getComputedStyle` + ajouter listener `matchMedia` pour re-render sur changement de thème
- [x] **[UX-P1-5]** Différencier visuellement les section labels — Primary (Top Signal, Predictions) : `text-sm font-semibold text-[var(--text-1)]` + bordure accent gauche 2px · Secondary : style actuel conservé
- [x] **[UX-P1-6]** Empty states actionnables : si master key connue → `"No data — [Run pipeline →]"` ouvre PipelinePanel · Sinon → `"Last run: [date]"` depuis l'API au lieu de l'heure UTC statique

### P2 — Polish

- [x] **[UX-P2-7]** LeadGraph : remplacer `<div>Loading…</div>` par `<div className="animate-pulse rounded-lg bg-[var(--bg-3)]" style={{height:260}} />` (cohérence avec tous les autres composants)
- [x] **[UX-P2-8]** SignalFeed : ajouter bouton "Load more" (5 → 10 → 20) au lieu du cap fixe à 5
- [x] **[UX-P2-9]** SignalCard "↓ Details" : ajouter `underline` ou `opacity-70` au repos pour rendre l'affordance cliquable visible sans hover
- [x] **[UX-P2-10]** Supprimer le badge version `v0.1.0` du header ou le lier au CHANGELOG

## In Progress

_(none)_

## Done

- [x] tests/conftest.py — fixed pytest-asyncio loop conflict (NullPool + function-scoped loop + sync session hooks)
- [x] pyproject.toml — `asyncio_default_fixture_loop_scope = "function"` (was "session")
- [x] models/schemas.py — added `realized_at: datetime | None` to PredictionRead
- [x] Brave API key rotation verified (new key → 200 OK, 18 articles collected for Utilities)
- [x] 51/51 tests passing

- [x] services/collector_sources.py (extracted from collector.py — HTTP clients Brave + EventRegistry)
- [x] services/collector.py (refactored, 116 lines — within limit)
- [x] routes/sectors.py (GET /sectors, POST /sectors, GET /{id}, GET /{id}/correlations)
- [x] routes/predictions.py (GET /predictions, GET /track-record, GET /{id}, PATCH /{id}/realize)
- [x] services/publisher.py (generate_daily_briefing + detect_daily_signals)
- [x] prompts/signals.py (WeakSignal, SignalOutput, detect_signals via LiteLLM)
- [x] flows/daily_pipeline.py (collect → analyze batch, schedule 05:00 UTC daily)
- [x] flows/briefing_job.py (briefing + signals, schedule 06:00 UTC daily)
- [x] services/analyzer.py
- [x] services/scorer.py
- [x] services/correlator.py
- [x] services/correlation_store.py
- [x] services/data_fetcher.py
- [x] services/database.py
- [x] services/cache.py
- [x] services/exceptions.py
- [x] prompts/analyze.py
- [x] prompts/score_impact.py
- [x] prompts/briefing.py
- [x] models/db.py
- [x] models/schemas.py
- [x] models/enums.py
- [x] routes/articles.py
- [x] routes/correlations.py
- [x] routes/health.py
- [x] flows/correlation_job.py
- [x] Frontend heatmap (CorrelationHeatmap, HeatmapControls, useCorrelationMatrix)
