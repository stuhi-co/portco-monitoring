# Stuhi Portfolio Intelligence

Automated weekly news digests for PE portfolio companies. Subscribe with an email and a list of company names — the system enriches each company (industry, competitors, key topics), searches for relevant news, scores it through a PE lens, and delivers a curated email digest.

## What it does

1. **You subscribe** with your email + company names (e.g. "Datadog", "Snowflake")
2. **Exa Research API** automatically enriches each company — detects industry, finds competitors, identifies key topics
3. **Every week** (or daily), the system:
   - Searches for news about each company, their competitors, and their industry
   - Deduplicates articles (you never see the same article twice)
   - Scores each article for PE relevance using Claude
   - Generates a "So What" PE insight for each article
   - Compiles everything into a professional email digest
4. **You receive** a digest grouped by industry, with executive overview, competitor alerts, and actionable insights

## Prerequisites

You need three things installed on your computer:

- **Docker Desktop** — [download here](https://www.docker.com/products/docker-desktop/) (runs the database)
- **uv** — Python package manager. Install with:
  ```
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- **API keys** (all have free tiers):
  - [Exa](https://dashboard.exa.ai/api-keys) — for web search and company research
  - [Anthropic](https://console.anthropic.com/settings/keys) — for Claude AI analysis
  - [Resend](https://resend.com/api-keys) — for sending emails

## Setup (5 minutes)

### 1. Clone and install

```bash
git clone <repo-url>
cd stuhi-portco-monitoring
uv sync
```

### 2. Configure environment

```bash
cp .env.example .env
```

Open `.env` in any text editor and fill in your three API keys:

```
EXA_API_KEY=your-exa-key-here
ANTHROPIC_API_KEY=your-anthropic-key-here
RESEND_API_KEY=your-resend-key-here
```

Leave everything else as-is for local development.

### 3. Start the database

```bash
docker compose up -d db
```

### 4. Run database migrations

```bash
uv run alembic upgrade head
```

### 5. Start the app

```bash
uv run uvicorn backend.main:app --reload
```

The app is now running at **http://localhost:8000**. You can see the API docs at http://localhost:8000/docs.

## Testing it locally (mimicking a real user)

Here's how to test the full flow end-to-end:

### Step 1: Subscribe

```bash
curl -X POST http://localhost:8000/api/subscribe \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-real-email@example.com",
    "companies": [
      {"name": "Datadog"},
      {"name": "Snowflake"},
      {"name": "HashiCorp"}
    ],
    "fund_description": "Growth equity fund focused on B2B SaaS"
  }'
```

This returns a JSON response with your `subscriber_id`. Copy it — you'll need it below.

The system immediately starts enriching your companies in the background (takes ~30s per company). You can check progress:

### Step 2: Check enrichment

```bash
curl http://localhost:8000/api/subscriptions/YOUR_SUBSCRIBER_ID
```

Wait until all companies show `enriched_at` (not null). You should see each company now has a description, competitors list, key topics, and auto-detected industry.

### Step 3: Trigger a digest

Instead of waiting for the weekly schedule, trigger one manually:

```bash
curl -X POST http://localhost:8000/api/subscriptions/YOUR_SUBSCRIBER_ID/trigger
```

This runs the full pipeline in the background (takes 1-2 minutes):
- Searches news for each company + competitors + industry
- Deduplicates and stores articles
- Scores each article with Claude
- Generates PE insights, industry pulses, and executive overview
- Renders the HTML email
- Sends it via Resend

### Step 4: Check your inbox

You should receive a "Portfolio Intelligence" email with:
- Executive overview (top themes across your portfolio)
- Industry sections with pulse summaries
- Per-company news with category tags, Exa summaries, and Claude "So What" PE insights
- Competitor alerts highlighted
- Unsubscribe link in the footer

### Step 5: View past digests

```bash
# List all digests
curl http://localhost:8000/api/subscriptions/YOUR_SUBSCRIBER_ID/digests

# View a specific digest in your browser
open http://localhost:8000/api/digests/DIGEST_ID
```

### Step 6: Test unsubscribe

```bash
curl http://localhost:8000/api/unsubscribe/YOUR_SUBSCRIBER_ID
```

## Deploying

### Option A: Docker Compose (simplest)

For a VPS or any machine with Docker:

```bash
# Build and start everything
docker compose up -d

# Run migrations
docker compose exec app uv run alembic upgrade head
```

Make sure your `.env` has all API keys and set `APP_BASE_URL` to your public URL (for unsubscribe links to work).

### Option B: Managed Postgres (recommended for production)

Use a managed Postgres like Supabase, Neon, or RDS:

1. Create a Postgres database
2. Set `DATABASE_URL` in `.env` to your connection string (use `postgresql+asyncpg://...`)
3. Run migrations: `uv run alembic upgrade head`
4. Deploy the app to any platform that runs Docker (Railway, Fly.io, Render, etc.)

### Environment variables for production

Update these in your `.env` or hosting platform's environment settings:

| Variable | What to change |
|----------|---------------|
| `DATABASE_URL` | Your production Postgres connection string |
| `APP_BASE_URL` | Your public URL (e.g. `https://intel.yourdomain.com`) |
| `EMAIL_FROM` | Must match your Resend verified domain |
| `DIGEST_CRON_HOUR` | Hour (UTC) to send digests. Default: `8` |
| `DIGEST_CRON_DAY_OF_WEEK` | Day of week. Default: `mon` |

## API Reference

| Method | Endpoint | What it does |
|--------|----------|-------------|
| `POST` | `/api/subscribe` | Create a new subscription |
| `GET` | `/api/subscriptions/{id}` | View subscription + enriched companies |
| `PATCH` | `/api/subscriptions/{id}` | Update frequency, fund description, add/remove companies |
| `DELETE` | `/api/subscriptions/{id}` | Delete subscription |
| `GET` | `/api/unsubscribe/{id}` | One-click unsubscribe (link in email) |
| `POST` | `/api/subscriptions/{id}/trigger` | Manually trigger a digest |
| `GET` | `/api/subscriptions/{id}/digests` | List past digests |
| `GET` | `/api/digests/{id}` | View digest HTML in browser |
| `GET` | `/api/industries` | List available industry categories |
| `GET` | `/api/health` | Health check |

Full interactive docs available at `/docs` when the app is running.

## Cost estimate

For 10 companies, weekly digests, per month:

| Service | Cost |
|---------|------|
| Exa (search + enrichment) | ~$1 |
| Claude (analysis) | ~$2-3 |
| Resend (emails) | Free tier |
| Postgres | Free tier (Supabase/Neon) |
| **Total** | **~$3-4/month** |

## Project structure

```
src/backend/
  main.py              # FastAPI app + scheduler setup
  config.py            # Settings (from .env)
  schemas.py           # Request/response models + enums
  pipeline.py          # Full orchestration: search -> dedup -> analyze -> send
  scheduler.py         # Weekly cron trigger
  database/
    session.py         # Async SQLAlchemy engine + session
    models.py          # ORM models (subscribers, companies, articles, etc.)
  api/
    subscriptions.py   # Subscribe, CRUD, unsubscribe endpoints
    digests.py         # Digest history + manual trigger
  services/
    enrichment.py      # Exa Research API -> company profile
    search.py          # Exa Search API -> news articles
    analysis.py        # Claude -> PE scoring + insights
    digest.py          # Claude overview + Jinja2 HTML rendering
    email.py           # Resend email delivery
templates/
  digest.html          # Email template
```
