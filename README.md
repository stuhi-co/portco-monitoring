# Stuhi Portfolio Intelligence

Automated news digests for PE portfolio companies. Subscribe with your email and a list of company names — the system enriches each company (industry, competitors, key topics), searches for relevant news, scores it through a PE lens, and delivers a curated email digest.

## How it works

1. **You subscribe** with your email + company names (e.g. "Datadog", "Snowflake")
2. **The system enriches** each company — detects industry, finds competitors, identifies key topics
3. **On a schedule** (weekly or daily), the system:
   - Searches for news about each company, their competitors, and their industry
   - Deduplicates articles so you never see the same one twice
   - Scores each article for PE relevance using Claude
   - Generates a "So What" PE insight for each article
   - Compiles everything into a professional email digest
4. **You receive** a digest grouped by industry, with an executive overview, competitor alerts, and actionable insights

---

## Use the hosted app

Go to **[news.stuhi.co](https://news.stuhi.co)** and subscribe — no setup needed.

1. Enter your email and add your portfolio companies
2. Pick a digest frequency (weekly or daily)
3. Optionally describe your fund's focus for more relevant insights
4. Hit **Subscribe**

You'll land on your dashboard where you can watch companies get enriched in real-time, trigger a digest on demand, browse past digests, and manage your settings.

If you clear your browser data, use the **"Already subscribed?"** field on the home page to recover your account by email.

---

## Run it yourself

If you prefer to self-host (your own data, your own API keys), there are two options below.

### Prerequisites

- **Docker Desktop** — [download here](https://www.docker.com/products/docker-desktop/)
- **API keys** (all have free tiers):
  - [Exa](https://dashboard.exa.ai/api-keys) — web search and company enrichment
  - [Anthropic](https://console.anthropic.com/settings/keys) — Claude AI analysis
  - [Resend](https://resend.com/api-keys) — email delivery

### 1. Clone and configure

```bash
git clone <repo-url>
cd portco-monitoring
cp .env.example .env
```

Open `.env` and fill in your three API keys:

```
EXA_API_KEY=your-exa-key-here
ANTHROPIC_API_KEY=your-anthropic-key-here
RESEND_API_KEY=your-resend-key-here
```

### 2. Start

```bash
./start.sh
```

This builds and starts everything (database, backend, frontend). Once ready:

```
  App is running at http://localhost:3000
```

Open that URL in your browser and subscribe.

### 3. Stop

```bash
docker compose down
```

### Local development (hot reload)

If you want to modify the code, run backend and frontend outside of Docker for instant feedback on changes.

**Extra prerequisites:** [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python) and [pnpm](https://pnpm.io/installation) (Node.js).

```bash
# Install dependencies
uv sync
cd src/frontend && pnpm install && cd ../..

# Start everything (DB in Docker, backend + frontend locally with hot reload)
./start.sh local
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API docs: http://localhost:8000/docs

---

## Deploy on a VPS

For running your own persistent instance on a server.

### 1. Provision a server

Any VPS with Docker installed works (Hetzner, DigitalOcean, AWS EC2, etc.). Clone the repo and copy your `.env` file onto the server.

### 2. Update `.env` for production

On top of the three API keys, update these:

| Variable | What to set |
|----------|-------------|
| `POSTGRES_PASSWORD` | A strong, random password |
| `DATABASE_URL` | Must match — `postgresql+asyncpg://portco:YOUR_PASSWORD@localhost:5432/portco_monitoring` |
| `APP_BASE_URL` | Your public URL, e.g. `https://intel.yourdomain.com` (used in unsubscribe links) |
| `EMAIL_FROM` | Must match your Resend verified domain |

Optional scheduling overrides:

| Variable | Default | Description |
|----------|---------|-------------|
| `DIGEST_CRON_HOUR` | `8` | Hour (UTC) to send digests |
| `DIGEST_CRON_DAY_OF_WEEK` | `mon` | Day of week for weekly digests |

### 3. Start

```bash
./start.sh
```

Point your domain to the server's IP and set up a reverse proxy (nginx/Caddy) to forward traffic to port `3000`.

### Cost estimate (self-hosted)

For 10 companies with weekly digests, per month:

| Service | Cost |
|---------|------|
| Exa (search + enrichment) | ~$1 |
| Claude (analysis) | ~$2-3 |
| Resend (emails) | Free tier |
| VPS (e.g. Hetzner CX22) | ~$4 |
| **Total** | **~$7-8/month** |

---

## Project structure

```
src/
  backend/
    main.py              # FastAPI app + scheduler
    config.py            # Settings (from .env)
    schemas.py           # Request/response models
    pipeline.py          # Orchestration: search -> analyze -> send
    database/            # SQLAlchemy models + session
    api/                 # REST endpoints
    services/            # Exa search, Claude analysis, email delivery
  frontend/
    app/                 # Next.js pages (subscribe, dashboard, digest viewer)
    components/          # UI components (company cards, digest list, etc.)
    lib/                 # API client, React Query hooks, helpers
templates/
  digest.html            # Email template
```
