# AutoProspect — CLAUDE.md

## Identity

AutoProspect is a Django + React prospecting tool that discovers local businesses via Google Places, enriches them through a Celery async pipeline, scores them with Claude AI on automation readiness, and generates personalized outreach. Single-user tool (not SaaS). The owner sells automation services (CRM, scheduling, invoicing, marketing) to local businesses, primarily home services and medical/dental.

## Architecture (Do Not Deviate)

```
React (Vite) → DRF API → PostgreSQL
                 ↓
           Celery + Redis
           ↓         ↓         ↓
       Discovery  Enrichment  Scoring
      (Google     (httpx +    (Claude
       Places)    Wappalyzer)  API)
```

**Monorepo layout:**
- `backend/` — Django 5.x, DRF, Celery tasks. See `backend/CLAUDE.md`
- `frontend/` — React 18, Vite, Mapbox GL JS. See `frontend/CLAUDE.md`
- `docs/` — Architecture, prompts, data model reference

**Core pipeline flow:** Scan → Discover businesses → Enrich (website + tech stack) → Score Tier 1 (Claude) → [Manual] Promote to Lead → Score Tier 2 → Generate Outreach

## Tech Stack (Locked)

| Layer | Choice | Notes |
|-------|--------|-------|
| Backend | Django 5.x + DRF | Python 3.12+ |
| Frontend | React 18 + Vite | No Next.js |
| Map | Mapbox GL JS | NOT Google Maps JS |
| Database | PostgreSQL 16 | Use JSONField for flexible data |
| Queue | Celery 5.x + Redis 7.x | Separate queues: default, enrichment, scoring |
| AI | Claude API (Sonnet) | `claude-sonnet-4-5-20250929` for scoring |
| Business Data | Google Places API (New) | NOT legacy Places API |
| Scraping | httpx + BeautifulSoup4 | Async HTTP client |
| State Mgmt | Zustand | NOT Redux |

## Django Apps (5 apps, strict boundaries)

| App | Owns | Never touches |
|-----|------|---------------|
| `scans` | Scan model, orchestrator task | Business scoring |
| `businesses` | Business model, Google Places service | Lead status |
| `enrichment` | EnrichmentProfile model, crawlers | Scoring logic |
| `scoring` | AutomationScore model, Claude prompts | Lead management |
| `leads` | Lead, LeadList, LeadActivity models | Enrichment data |

Cross-app imports: always go through models and serializers, never import views or tasks from another app.

## Build & Run Commands

```bash
# Backend
cd backend && python manage.py runserver          # Dev server
cd backend && python manage.py test               # All tests
cd backend && python manage.py test apps.scoring   # Single app tests
cd backend && celery -A config worker -l info -Q default,enrichment,scoring  # Workers
cd backend && python manage.py makemigrations && python manage.py migrate

# Frontend
cd frontend && npm run dev       # Vite dev server
cd frontend && npm run build     # Production build
cd frontend && npm run lint      # ESLint
cd frontend && npm test          # Vitest

# Full stack (Docker)
docker compose up -d             # All services
docker compose logs -f worker    # Watch Celery logs
```

## Coding Standards (Universal)

- **Python**: Follow PEP 8. Use type hints on all function signatures. Use `pathlib` over `os.path`.
- **JavaScript/React**: Functional components only. Hooks for state. Named exports except for page-level default exports. Destructure props.
- **Never do**: Inline API keys. Print statements in committed code. Wildcard imports. Circular imports between Django apps.
- **Always do**: Write a docstring on every Django model and service method. Handle errors explicitly in Celery tasks (try/except with retry). Use `select_related`/`prefetch_related` on querysets with foreign keys.
- **Formatting**: Use `black` and `isort` for Python. Use `prettier` for JS/JSX. Don't fight with the formatter.

## Two-Tier Enrichment Model (Critical Business Logic)

**Tier 1** — Runs automatically on every business in a scan:
- Google Places data + website crawl + tech stack detection
- Claude quick-score (cheap, ~$0.01-0.03/business)
- Produces: overall_score (0-100), 4 sub-scores, key signals, summary

**Tier 2** — Triggered manually on promising leads only:
- Full dossier with competitor analysis and pitch strategy
- More expensive Claude call (~$0.05-0.10/business)
- Also generates: cold email + call script

Never auto-trigger Tier 2. It's always a deliberate user action.

## API Cost Awareness

Every Claude API call MUST track `prompt_tokens`, `completion_tokens`, and `api_cost_cents`. Every Scan model tracks cumulative `api_cost_cents`. The frontend shows cost per scan and monthly totals. Budget target: $150-300/mo.

## Key Reference Docs

For detailed specs beyond this file, read:
- `docs/DATA_MODELS.md` — Full Django model definitions with every field
- `docs/API_ENDPOINTS.md` — All REST endpoints with request/response examples
- `docs/CELERY_PIPELINE.md` — Task chain architecture, retry logic, rate limits
- `docs/AI_PROMPTS.md` — All Claude system prompts and prompt builders
- `docs/FRONTEND_COMPONENTS.md` — React component tree and Zustand stores

## When Compacting

When compacting context, always preserve:
- The full list of Django apps and their boundaries
- The two-tier enrichment model
- The current task/feature being worked on
- Any file paths that were modified in this session
- Test commands and how to verify changes
