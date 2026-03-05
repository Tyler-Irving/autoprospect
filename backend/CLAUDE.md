# Backend — CLAUDE.md

## Django Project Structure

```
backend/
├── config/              # Project config (settings, urls, celery, wsgi)
│   └── settings/        # Split settings: base.py, local.py, production.py
├── apps/
│   ├── scans/           # Scan jobs — models, views, orchestrator task
│   ├── businesses/      # Business records + Google Places service
│   ├── enrichment/      # EnrichmentProfile + crawler/detector services
│   ├── scoring/         # AutomationScore + Claude client + prompts
│   └── leads/           # Lead management, outreach generation
└── requirements.txt
```

## Settings

- Settings module: `config.settings.local` (dev), `config.settings.production` (prod)
- Env vars loaded via `django-environ`. Never hardcode secrets.
- Celery config lives in `config/celery.py` with `config.settings` namespace `CELERY_`

## Model Relationships (Quick Reference)

```
Scan  ──1:N──  Business
Business  ──1:1──  EnrichmentProfile
Business  ──1:N──  AutomationScore (one per tier)
Business  ──1:1──  Lead
Lead  ──N:N──  LeadList
Lead  ──1:N──  LeadActivity
```

For full field definitions: `docs/DATA_MODELS.md`

## Celery Task Patterns

- All tasks use `@shared_task(bind=True, max_retries=N)`
- Rate limits: enrichment `5/s`, scoring `3/s`, discovery `10/s`
- Task routing: `apps.scoring.tasks.*` → `scoring` queue, `apps.enrichment.tasks.*` → `enrichment` queue
- Orchestrator uses `chain()` and `group()` from celery.canvas — never nested chains
- Always update `Scan.status` at each pipeline phase transition
- Always wrap task body in try/except, save error to model's `error_message` or `error_log`

## Service Layer Pattern

Business logic lives in `apps/<app>/services/`, NOT in views or tasks.
- Tasks call services. Views call services. Services call external APIs.
- Services are plain Python classes, no Django dependencies beyond models.
- Example: `Tier1Scorer.score(business, enrichment) → dict`

## API Conventions (DRF)

- ViewSets for CRUD, `@action` decorators for custom endpoints
- Serializers: separate `List` and `Detail` serializers when payloads differ
- Filtering: `django-filter` with `FilterSet` classes in `filters.py`
- Pagination: `LimitOffsetPagination`, default 50
- All responses JSON. No HTML rendering from DRF.
- URL prefix: `/api/` for all endpoints

## Testing Patterns

- Use `pytest-django` with `@pytest.fixture` for factories
- Mock external APIs (Google Places, Claude) with `unittest.mock.patch`
- Test Celery tasks with `CELERY_ALWAYS_EAGER=True` in test settings
- Minimum: test every service method and every API endpoint
- Name pattern: `test_<service>_<scenario>.py`

## Common Gotchas

- Google Places API (New) uses different field names than legacy. Always reference the New API docs.
- Claude API responses need JSON extraction — strip markdown fences before `json.loads()`
- `EnrichmentProfile` has many nullable booleans — always check for `None` vs `False`
- Use `F()` expressions for atomic counter updates (e.g., `businesses_scored`)
- `select_related("enrichment")` when loading businesses for scoring — avoids N+1
