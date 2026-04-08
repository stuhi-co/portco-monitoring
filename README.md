# Stuhi Portfolio Intelligence

Automated news digests for PE portfolio companies. Subscribe with your email and a list of company names — the system enriches each company (industry, competitors, key topics), searches for relevant news, scores it through a PE lens, and delivers a curated email digest.

## How it works

1. **You subscribe** with your email + portfolio company names (e.g. "Datadog", "Snowflake")
2. **The system enriches** each company — detects industry, finds competitors, identifies key topics
3. **On a schedule** (by default weekly 8am PT), the system:
   - Searches for news about each company, their competitors, and their industry
   - Deduplicates articles so you never see the same one twice
   - Compiles everything into a professional email digest
4. **You receive** a digest grouped by industry, with an executive overview, competitor alerts, and actionable insights

---

## Use the hosted app

Go to **[news.stuhi.co](https://news.stuhi.co)** and subscribe — no setup needed.

1. Enter your email and add your portfolio companies
2. Optionally describe your fund's focus for more relevant insights
3. Hit **Subscribe**

You'll land on your dashboard where you can watch companies get enriched in real-time, trigger a digest on demand, browse past digests, and manage your settings.

If you clear your browser data, use the **Sign In** tab on the home page to recover your account by email.

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
git clone https://github.com/stuhi-co/portco-monitoring.git
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

## Deploy to production

The recommended setup splits frontend and backend:

- **Frontend** (Next.js) on **Vercel** — free tier, automatic SSL, edge CDN
- **Backend** (FastAPI + PostgreSQL) on a **VPS** — any provider (GCP, Hetzner, DigitalOcean, etc.)

Architecture: `yourdomain.com` → Vercel → (rewrites `/api/*`) → `api.yourdomain.com` → VPS

### 1. DNS setup (your domain registrar)

Add two records pointing to your domain (e.g. on GoDaddy, Cloudflare, etc.):

| Type | Name | Value |
|------|------|-------|
| CNAME | `news` | `cname.vercel-dns.com` |
| A | `api.news` | `<your VPS IP>` |

### 2. Deploy the backend (VPS)

**Provision a server** — a small VM works (e.g. GCP e2-small, Hetzner CX22). Make sure you allow HTTP and HTTPS traffic in Network settings. SSH in, then:

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in for group to take effect
exit

# Clone the repo
git clone https://github.com/stuhi-co/portco-monitoring.git
cd portco-monitoring

# Configure
cp .env.example .env
sudo nano .env
```

**Edit `.env`** with your production values:

| Variable | What to set |
|----------|-------------|
| `EXA_API_KEY` | Your Exa key |
| `ANTHROPIC_API_KEY` | Your Anthropic key |
| `RESEND_API_KEY` | Your Resend key |
| `POSTGRES_PASSWORD` | A strong random password |
| `DATABASE_URL` | `postgresql+asyncpg://portco:YOUR_PASSWORD@db:5432/portco_monitoring` |
| `APP_BASE_URL` | `https://news.yourdomain.com` (used in unsubscribe links) |
| `ALLOWED_ORIGINS` | `["https://news.yourdomain.com"]` |
| `EMAIL_FROM` | Must match your Resend verified domain |

**Install Caddy** as a reverse proxy (auto-HTTPS, zero config):

```bash
sudo apt install -y caddy
# Then edit the Caddyfile
sudo nano /etc/caddy/Caddyfile
```

Replace Caddyfile's content with your domain for reverse proxy:

```
api.news.yourdomain.com {
    reverse_proxy localhost:8000
}
```

```bash
sudo systemctl restart caddy
```

**Start the backend** (only db + backend, not the frontend container):

```bash
docker compose up -d db backend
# Wait for db, then run migrations
docker compose exec backend uv run alembic upgrade head
```

Verify it works: `curl https://api.news.yourdomain.com/api/health`

**Updating the code / env variables**
After a change in the code, env variables, or pulling the changes from the public repo, to build the VPS, use"
```bash
# Rebuild and restart only backend (db volume is preserved)
docker compose up -d --build backend
docker compose exec backend uv run alembic upgrade head # If any migration is to run
# Restart without rebuilding (e.g. just changed .env)
docker compose restart backend
# Check db data is still there
docker compose exec db psql -U portco -d portco_monitoring -c "SELECT count(*) FROM subscribers;"
```

WARNING: The only thing that would delete data is docker compose down -v (the -v flag removes volumes). Never use -v unless you intentionally want to wipe the database.

### 3. Deploy the frontend (Vercel)

1. Push your repo to GitHub
2. Go to [vercel.com/new](https://vercel.com/new), import the repo
3. Set **Root Directory** to `src/frontend`
4. Add one environment variable:
   - `BACKEND_URL` = `https://api.news.yourdomain.com`
5. Deploy
6. In Vercel project settings → **Domains**, add `news.yourdomain.com`

The `next.config.ts` rewrite rule (`/api/*` → `BACKEND_URL/api/*`) means all API calls are proxied server-side through Vercel. The browser never talks to the backend directly, so CORS doesn't even come into play in this setup.

### Important: CORS

CORS is configured via the `ALLOWED_ORIGINS` environment variable (defaults to `["http://localhost:3000"]`).

- **With Vercel rewrites** (recommended): CORS headers are technically not needed since Vercel proxies API calls server-side. But `ALLOWED_ORIGINS` is set as defense-in-depth.
- **Without Vercel** (e.g. frontend served directly from a CDN or different host): CORS is **required**. Set `ALLOWED_ORIGINS` to your frontend's origin, e.g. `["https://news.yourdomain.com"]`. Without this, the browser will block all API calls.

### 4. Verify

- `https://news.yourdomain.com` — should load the frontend
- Sign in / subscribe should work (API calls proxied through Vercel to the VPS)
- Trigger a digest and confirm it generates

### Cost estimate

For 10 companies with weekly digests, per month:

| Service | Cost |
|---------|------|
| Vercel (frontend) | Free |
| VPS (e.g. GCP e2-small) | ~$7 |
| Exa (search + enrichment) | ~$1 |
| Claude (analysis) | ~$2-3 |
| Resend (emails) | Free tier |
| **Total** | **~$10-11/month** |

### Alternative: all-in-one VPS

If you don't want Vercel, run everything on the VPS with `./start.sh` (uses Docker Compose for db + backend + frontend). Point your domain to the VPS IP and configure Caddy to reverse-proxy port `3000`. In this case, set `ALLOWED_ORIGINS` to your frontend's public URL.

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
