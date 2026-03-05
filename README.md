# AutoProspect

I sell automation services to local businesses. CRM setup, scheduling, invoicing, marketing automations. The problem is finding the right businesses to talk to. Most prospecting tools give you a list of names and phone numbers and call it a day. That's not enough.

AutoProspect is a tool I built to actually think about prospects. You draw a radius on a map, pick a business category, and it runs a full pipeline: discovers every matching business via Google Places, crawls each website, detects what software they're running (or not running), pulls their reviews, and then sends all of that context to Claude to score each business on automation readiness across four dimensions: CRM, scheduling, marketing, and invoicing.

By the time you open the leads dashboard, you're not looking at a cold list. You're looking at businesses ranked by how much they need what you're selling.

## What it does

The pipeline runs fully in the background once you kick off a scan.

**Discovery** pulls businesses from Google Places, captures contact info, ratings, review data, and business type.

**Enrichment** crawls each business's website. It detects the CMS they're using, whether they have online booking or a contact form, what CRM or payment processor shows up in their page source, whether their site is even reachable. This all happens in parallel across a Celery worker fleet.

**Scoring** takes everything enrichment found and builds a structured prompt for Claude. The model scores 0-100 on each automation category, flags key signals ("no CRM detected", "reviews mention slow response times", "manual scheduling visible"), writes a two-sentence summary, recommends a pitch angle, and estimates deal value. That whole call costs about a cent or two per business.

**Lead management** is where you work the pipeline. Businesses with high scores show up as green dots on the map. You add the ones you want, track status through the sales stages, edit notes, and view the full score breakdown with the AI's reasoning.

## Stack

```
React (Vite) + Mapbox GL JS
         |
    Django + DRF
         |
   Celery + Redis
    /         \
Enrichment   Scoring
(httpx +     (Claude
BeautifulSoup) API)
         |
    PostgreSQL
```

- **Backend**: Django 5, Django REST Framework, Python 3.12
- **Frontend**: React 18, Vite, Tailwind CSS v4, Mapbox GL JS, Zustand
- **Queue**: Celery 5 with three named queues (default, enrichment, scoring)
- **AI**: Claude Sonnet via the Anthropic SDK. Tier 1 runs on every business automatically. Tier 2 is a deeper dossier you trigger manually on high-potential leads.
- **Business data**: Google Places API (New)
- **Scraping**: httpx + BeautifulSoup4

## Running it

Copy `.env.example` to `.env` and fill in your API keys.

```bash
cp .env.example .env
# Add GOOGLE_PLACES_API_KEY and ANTHROPIC_API_KEY
```

Start everything with Docker:

```bash
docker compose up -d
```

That runs Postgres, Redis, the Django API server, the Celery worker, and the Vite dev server. Frontend is at `http://localhost:5173`. Backend API is at `http://localhost:8000/api`.

If you want to run the backend outside Docker:

```bash
cd backend
python manage.py migrate
python manage.py runserver

# In another terminal
celery -A config worker -l info -Q default,enrichment,scoring
```

## Running tests

```bash
# From the backend directory, or via Docker
docker exec autoprospect-backend-1 python -m pytest -v
```

64 tests. All pass.

## How scoring works

The Tier 1 score is a 0-100 integer across four categories. The rubric:

- **High (70-100)**: No tools detected, manual processes implied, reviews mention missed calls or slow response, no online booking. This is a strong target.
- **Medium (40-69)**: Some tools present but obvious gaps. Maybe they have a website but no booking, or Stripe but no CRM.
- **Low (0-39)**: Already well automated, or too small to be worth pursuing, or no web presence at all.

The model also returns key signals as a list, a two to three sentence summary, a recommended pitch angle, and a deal value estimate. All of that shows up in the hover card on the map and in the lead detail view.

Claude's responses are JSON-only. The client strips markdown fences if present, validates every field is in range, and saves cost tracking (prompt tokens, completion tokens, cents spent) to the database on every call.

## Cost

Scoring runs at roughly $0.01-0.03 per business. A scan of 20 plumbers in a mid-size city costs less than fifty cents. Monthly budget tracking is built in and visible on the dashboard.

## Project status

Phases 1 through 4 are done. The full pipeline runs end to end: scan, enrich, score, manage leads. Phase 5 (AI-generated cold emails and call scripts per lead) is next.

This is a personal tool. Not a SaaS, not open for signups. I use it to find my own clients.
