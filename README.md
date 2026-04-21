# Ad Creative Machine

Multi-model AI pipeline that generates platform-ready ad copy and visuals for Web3 protocols.

**Stack:** Claude Opus 4.7 (brief) → Claude Sonnet 4.6 (copy) → Gemini 2.5 Flash Image (visuals) → FastAPI + React

---

## 5-Minute Local Setup

### Prerequisites
- Python 3.12+
- Node 18+
- Docker (for Postgres, or bring your own)
- Anthropic API key
- Google AI (Gemini) API key

### 1. Clone & configure

```bash
git clone https://github.com/Charubak/ad-creative-machine
cd ad-creative-machine
cp backend/.env.example backend/.env
# Edit backend/.env — set ANTHROPIC_API_KEY and GEMINI_API_KEY at minimum
```

### 2. Start Postgres

```bash
docker compose up db -d
# Creates DB and runs migrations automatically
```

Or point `DATABASE_URL` at an existing Postgres instance and run:
```bash
psql $DATABASE_URL < backend/migrations/0001_ad_machine_tables.sql
```

### 3. Start the backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
# Runs on http://localhost:8000
```

### 4. Start the frontend

```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:5173
```

Open **http://localhost:5173** and fill in the project form.

---

## End-to-End CLI Test (no browser)

```bash
cd backend
python tests/ad_machine/test_pipeline_cli.py
```

Runs a minimal pipeline with a sample Web3 project input and prints each stage result. Requires `ANTHROPIC_API_KEY` and `GEMINI_API_KEY` in environment.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key |
| `GEMINI_API_KEY` | Yes | Google AI Studio key |
| `DATABASE_URL` | No | Postgres connection string (optional — skips persistence) |
| `ASSET_STORE_PROVIDER` | No | `local` (default), `r2`, or `s3` |
| `BUFFER_ACCESS_TOKEN` | No | Buffer API token for direct publishing |
| `GEMINI_IMAGE_MODEL` | No | Defaults to `gemini-2.5-flash-image` |

---

## Pipeline Stages

```
ProjectInput (form)
  → Opus Planner       — strategic brief, angles, segments
  → Copy Generator     — 5 variations × 4 platforms, compliance + slop scoring
  → Image Generator    — Gemini visuals per platform spec
  → Assembly           — CreativePack with pairings
  → OutputGallery      — review, select, export
  → PerformanceUpload  — CSV feedback → Round 2
```

---

## Export Options

- **ZIP bundle** — markdown copy + all images + `manifest.json` + `compliance_report.json`
- **Google RSA CSV** — 15 headlines + 4 descriptions, Ads Editor compatible
- **Buffer push** — direct publish via Buffer API

---

## Docker (full stack)

```bash
docker compose up --build
# Backend: http://localhost:8000
# Frontend: npm run dev separately (hot-reload not in Docker)
```
