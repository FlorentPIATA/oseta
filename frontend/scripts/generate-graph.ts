#!/usr/bin/env tsx
/**
 * OSETA — Graph Generator
 * Scans backend Python modules + frontend TypeScript src/
 * Generates context/graph.md at the project root.
 *
 * Usage : cd frontend && npm run graph
 * Regen after : new route, new service, new prompt, schema change, new hook
 */

import fg from 'fast-glob'
import fs from 'fs'
import path from 'path'

const FRONTEND_DIR = process.cwd()                    // .../OSETA project/frontend
const ROOT = path.resolve(FRONTEND_DIR, '..')          // .../OSETA project
const OUT = path.join(ROOT, 'context', 'graph.md')
const TODAY = new Date().toISOString().split('T')[0]

// ── Python: extract FastAPI route decorators ───────────────────────────────
function extractRouterPrefix(content: string): string {
  const m = content.match(/APIRouter\([^)]*prefix=['"](\/[^'"]+)['"]/)
  return m ? m[1] : ''
}

function extractRoutes(content: string, prefix: string): string[] {
  const routes: string[] = []
  for (const m of content.matchAll(
    /@router\.(get|post|put|patch|delete)\(\s*['"]([^'"]+)['"]/g
  )) {
    routes.push(`[${m[1].toUpperCase()}] ${prefix}${m[2]}`)
  }
  return routes
}

// ── Python: extract public function names ──────────────────────────────────
function extractPyFunctions(content: string): string[] {
  const names: string[] = []
  for (const m of content.matchAll(/^(?:async )?def ([a-z][a-zA-Z0-9_]+)\(/gm)) {
    if (!m[1].startsWith('_')) names.push(m[1])
  }
  return names.slice(0, 6)
}

// ── Python: extract Pydantic BaseModel subclasses ─────────────────────────
function extractPydanticModels(content: string): string[] {
  const names: string[] = []
  for (const m of content.matchAll(/^class (\w+)\(BaseModel\)/gm)) names.push(m[1])
  return names
}

// ── Python: extract SQLAlchemy models (Base subclasses) ───────────────────
function extractSAModels(content: string): string[] {
  const names: string[] = []
  for (const m of content.matchAll(/^class (\w+)\(Base\)/gm)) names.push(m[1])
  return names
}

// ── Python: extract StrEnum subclasses ────────────────────────────────────
function extractEnums(content: string): string[] {
  const names: string[] = []
  for (const m of content.matchAll(/^class (\w+)\(StrEnum\)/gm)) names.push(m[1])
  return names
}

// ── Python: extract @flow / @task names ───────────────────────────────────
function extractFlowTasks(content: string): { flows: string[]; tasks: string[] } {
  const flows: string[] = []
  const tasks: string[] = []
  for (const m of content.matchAll(/@flow[\s\S]{0,200}?\nasync def (\w+)/g)) flows.push(m[1])
  for (const m of content.matchAll(/@task[\s\S]{0,200}?\nasync def (\w+)/g)) tasks.push(m[1])
  return { flows, tasks }
}

// ── TS: extract named exports (hooks first) ────────────────────────────────
function extractTsExports(content: string): string[] {
  const names: string[] = []
  for (const m of content.matchAll(/export\s+(?:async\s+)?function\s+(\w+)/g)) names.push(m[1])
  for (const m of content.matchAll(/export\s+(?:const|let)\s+(\w+)/g)) names.push(m[1])
  const hooks = names.filter(n => n.startsWith('use'))
  const rest = names.filter(n => !n.startsWith('use') && n !== 'default')
  return [...hooks, ...rest].slice(0, 6)
}

// ── TS: extract exported interface / type names ────────────────────────────
function extractTsInterfaces(content: string): string[] {
  const names: string[] = []
  for (const m of content.matchAll(/export\s+interface\s+(\w+)/g)) names.push(m[1])
  for (const m of content.matchAll(/export\s+type\s+(\w+)\s*=/g)) names.push(m[1])
  return names.slice(0, 8)
}

// ── Read helper ────────────────────────────────────────────────────────────
function read(relFromFrontend: string): string {
  return fs.readFileSync(path.join(FRONTEND_DIR, relFromFrontend), 'utf-8')
}

// ── Main ──────────────────────────────────────────────────────────────────
async function main() {
  const L: string[] = []

  // ── En-tête ───────────────────────────────────────────────────────────────
  L.push(`# OSETA — Codebase Graph`)
  L.push(`> Généré le ${TODAY} | \`cd frontend && npm run graph\` pour régénérer`)
  L.push(`> Lire EN PREMIER dans chaque session — backend + frontend en un coup d'œil.`)
  L.push('')

  // ── Invariants critiques ──────────────────────────────────────────────────
  L.push(`## INVARIANTS CRITIQUES`)
  L.push('```')
  L.push(`Config       : from config import settings  (JAMAIS os.environ directement)`)
  L.push(`Logs         : from loguru import logger  (JAMAIS print())`)
  L.push(`DB           : toutes les queries sont async (AsyncSession + await)`)
  L.push(`LLM output   : TOUJOURS via instructor + Pydantic  (ZÉRO parsing JSON manuel)`)
  L.push(`Prompts      : TOUJOURS dans prompts/*.py  (jamais inline dans les services)`)
  L.push(`Exceptions   : TOUJOURS depuis services/exceptions.py  (OsetaError hierarchy)`)
  L.push(`Migrations   : alembic revision --autogenerate  (jamais CREATE TABLE manuel)`)
  L.push(`Taille max   : 200 lignes par fichier Python  (découper si dépassé)`)
  L.push(`LLM default  : gpt-4o-mini  | premium (IS > 80) : gpt-4o  | budget : 50 USD/jour`)
  L.push(`CI publish   : CI ≥ 65  | IS alert : IS ≥ 80  | CP action : CP ≥ 80`)
  L.push('```')
  L.push('')

  // ── Architecture ─────────────────────────────────────────────────────────
  L.push(`## ARCHITECTURE`)
  L.push('```')
  L.push(`Backend  : FastAPI + Python 3.12 | SQLAlchemy 2.0 async | asyncpg | PostgreSQL 15`)
  L.push(`LLM      : LiteLLM + instructor + Pydantic v2 | Prefect 2.x | Redis TTL`)
  L.push(`Frontend : React 18 + Vite + TypeScript strict | TanStack Query | Recharts`)
  L.push(`Pipeline : collect → analyze (LLM) → score (CI/IS) → correlate → publish briefing`)
  L.push(`Cron     : correlation-weekly (lundi 04:00 UTC) | briefing-daily (06:00 UTC)`)
  L.push(`Ports    : API :8000 | Frontend :5173 | Prefect UI :4200 | Grafana :3001`)
  L.push('```')
  L.push('')

  // ── Services ──────────────────────────────────────────────────────────────
  const svcFiles = await fg('../services/**/*.py', {
    cwd: FRONTEND_DIR,
    ignore: ['**/__pycache__/**', '**/__init__.py'],
  })
  const svcFiltered = svcFiles.filter(f => !path.basename(f).startsWith('__'))
  L.push(`## SERVICES (${svcFiltered.length})`)
  for (const f of svcFiltered.sort()) {
    const fname = path.basename(f, '.py')
    const content = read(f)
    const fns = extractPyFunctions(content)
    L.push(fns.length ? `  ${fname}: { ${fns.join(', ')} }` : `  ${fname}`)
  }
  L.push('')

  // ── Routes API ────────────────────────────────────────────────────────────
  const routeFiles = await fg('../routes/**/*.py', {
    cwd: FRONTEND_DIR,
    ignore: ['**/__pycache__/**', '**/__init__.py'],
  })
  const routeFiltered = routeFiles.filter(f => !path.basename(f).startsWith('__'))
  L.push(`## ROUTES API (${routeFiltered.length})`)
  for (const f of routeFiltered.sort()) {
    const fname = path.basename(f, '.py')
    const content = read(f)
    const prefix = extractRouterPrefix(content)
    const routes = extractRoutes(content, prefix)
    L.push(`  ${fname}:`)
    if (routes.length) {
      for (const r of routes) L.push(`    ${r}`)
    } else {
      L.push(`    (aucune route détectée)`)
    }
  }
  L.push('')

  // ── Flows Prefect ─────────────────────────────────────────────────────────
  const flowFiles = await fg('../flows/**/*.py', {
    cwd: FRONTEND_DIR,
    ignore: ['**/__pycache__/**', '**/__init__.py'],
  })
  const flowFiltered = flowFiles.filter(f => !path.basename(f).startsWith('__'))
  L.push(`## FLOWS PREFECT (${flowFiltered.length})`)
  for (const f of flowFiltered.sort()) {
    const fname = path.basename(f, '.py')
    const content = read(f)
    const { flows, tasks } = extractFlowTasks(content)
    const parts: string[] = []
    if (flows.length) parts.push(`flow: ${flows.join(', ')}`)
    if (tasks.length) parts.push(`tasks: ${tasks.join(', ')}`)
    if (parts.length) L.push(`  ${fname}: { ${parts.join(' | ')} }`)
    else L.push(`  ${fname}`)
  }
  L.push('')

  // ── Prompts LLM ───────────────────────────────────────────────────────────
  const promptFiles = await fg('../prompts/**/*.py', {
    cwd: FRONTEND_DIR,
    ignore: ['**/__pycache__/**', '**/__init__.py'],
  })
  const promptFiltered = promptFiles.filter(f => !path.basename(f).startsWith('__'))
  L.push(`## PROMPTS LLM (${promptFiltered.length})`)
  for (const f of promptFiltered.sort()) {
    const fname = path.basename(f, '.py')
    const content = read(f)
    const models = extractPydanticModels(content)
    const fns = extractPyFunctions(content)
    const parts: string[] = []
    if (models.length) parts.push(`output: ${models.join(', ')}`)
    if (fns.length) parts.push(`fn: ${fns.join(', ')}`)
    L.push(`  ${fname}: { ${parts.join(' | ')} }`)
  }
  L.push('')

  // ── Models ────────────────────────────────────────────────────────────────
  const modelFiles = await fg('../models/**/*.py', {
    cwd: FRONTEND_DIR,
    ignore: ['**/__pycache__/**', '**/__init__.py'],
  })
  const modelFiltered = modelFiles.filter(f => !path.basename(f).startsWith('__'))
  L.push(`## MODELS (${modelFiltered.length})`)
  for (const f of modelFiltered.sort()) {
    const fname = path.basename(f, '.py')
    const content = read(f)
    if (fname === 'enums') {
      const enums = extractEnums(content)
      L.push(`  ${fname}: { ${enums.join(', ')} }`)
    } else if (fname === 'db') {
      const sa = extractSAModels(content)
      L.push(sa.length ? `  ${fname} (SQLAlchemy): { ${sa.join(', ')} }` : `  ${fname}`)
    } else if (fname === 'schemas') {
      const pydantic = extractPydanticModels(content)
      L.push(pydantic.length ? `  ${fname} (Pydantic): { ${pydantic.join(', ')} }` : `  ${fname}`)
    } else {
      L.push(`  ${fname}`)
    }
  }
  L.push('')

  // ── Frontend ──────────────────────────────────────────────────────────────
  const tsFiles = await fg('src/**/*.{ts,tsx}', { cwd: FRONTEND_DIR })
  L.push(`## FRONTEND (${tsFiles.length} fichiers)`)

  const hooks = tsFiles.filter(f => f.includes('/hooks/'))
  const components = tsFiles.filter(f => f.includes('/components/'))
  const types = tsFiles.filter(f => f.includes('/types/'))
  const other = tsFiles.filter(
    f => !f.includes('/hooks/') && !f.includes('/components/') && !f.includes('/types/')
  )

  if (hooks.length) {
    L.push(`  [hooks]`)
    for (const f of hooks) {
      const fname = path.basename(f, path.extname(f))
      const exports = extractTsExports(read(f))
      L.push(exports.length ? `    ${fname}: { ${exports.join(', ')} }` : `    ${fname}`)
    }
  }

  if (components.length) {
    L.push(`  [components]`)
    for (const f of components) {
      const fname = path.basename(f, path.extname(f))
      const exports = extractTsExports(read(f))
      L.push(exports.length ? `    ${fname}: { ${exports.join(', ')} }` : `    ${fname}`)
    }
  }

  if (types.length) {
    L.push(`  [types]`)
    for (const f of types) {
      const fname = path.basename(f, path.extname(f))
      const ifaces = extractTsInterfaces(read(f))
      L.push(ifaces.length ? `    ${fname}: { ${ifaces.join(', ')} }` : `    ${fname}`)
    }
  }

  for (const f of other) {
    const fname = path.basename(f, path.extname(f))
    if (['main', 'vite-env.d'].includes(fname)) continue
    const exports = extractTsExports(read(f))
    L.push(exports.length ? `  ${fname}: { ${exports.join(', ')} }` : `  ${fname}`)
  }
  L.push('')

  // ── Flows principaux ──────────────────────────────────────────────────────
  L.push(`## FLOWS`)
  L.push('')
  L.push(`**Pipeline quotidien**`)
  L.push(`daily_pipeline.py → collect → analyze (LLM) → score (CI/IS) → publish`)
  L.push('')
  L.push(`**Corrélation hebdomadaire** (lundi 04:00 UTC)`)
  L.push(`correlation_job.py → fetch ETFs Alpha Vantage (~2min, 13s/call) + FRED → compute_correlation_matrix()`)
  L.push(`→ persistence correlation_matrix_entries | GET /correlations/matrix → heatmap React`)
  L.push('')
  L.push(`**Briefing quotidien** (06:00 UTC)`)
  L.push(`briefing_job.py → top scored articles → prompts/briefing.py (BriefingOutput) → PublishedArticle`)
  L.push('')
  L.push(`**Refresh manuel**`)
  L.push(`POST /correlations/refresh + X-Master-Key header → run_correlation_job() immédiat`)
  L.push('')

  // ── DB tables ─────────────────────────────────────────────────────────────
  L.push(`## DB TABLES (PostgreSQL 15)`)
  L.push('```')
  L.push(`articles                    id, title, content, url, source_type, status, published_at, created_at`)
  L.push(`sectors                     id, code, name, level(macro|meso|micro), parent_id`)
  L.push(`sector_links                sector_a_id, sector_b_id, link_type, strength`)
  L.push(`data_streams                time, stream_type, source_label, sector_id, value, unit, is_stale`)
  L.push(`correlation_matrix_entries  sector_a_id, sector_b_id, correlation, p_value, lag_days, method, window_days, computed_at`)
  L.push(`predictions                 id, sector_id, title, predicted_at, horizon_days, status, created_at`)
  L.push('```')
  L.push('')

  // ── External APIs ─────────────────────────────────────────────────────────
  L.push(`## EXTERNAL APIS`)
  L.push('```')
  L.push(`Alpha Vantage : ETFs SPDR (XLK XLF XLE XLV XLI XLB XLU XLC XLRE) | 5 calls/min | 13s delay`)
  L.push(`FRED          : DFF / DGS10 / CPIAUCSL / UMCSENT | fredapi sync + run_in_executor`)
  L.push(`LiteLLM       : gpt-4o-mini (default) / gpt-4o (IS>80) | instructor retry ×3`)
  L.push(`Brave / Bing  : news search (brave_api_key / bing_api_key)`)
  L.push(`EventRegistry : structured news (eventregistry_api_key)`)
  L.push('```')
  L.push('')

  // ── Écriture ──────────────────────────────────────────────────────────────
  fs.mkdirSync(path.join(ROOT, 'context'), { recursive: true })
  fs.writeFileSync(OUT, L.join('\n'), 'utf-8')

  console.log(`✅  graph.md généré : ${L.length} lignes | ${tsFiles.length} fichiers TS scannés`)
  console.log(`    → ${path.relative(FRONTEND_DIR, OUT).replace(/\\/g, '/')}`)
}

main().catch(err => {
  console.error('❌ Erreur generate-graph:', err)
  process.exit(1)
})
