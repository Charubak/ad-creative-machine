"""
AI Ad Creative Machine — FastAPI entrypoint.
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

import asyncpg
from anthropic import AsyncAnthropic
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)

from ad_machine.orchestrator import AdMachineOrchestrator
from ad_machine.storage.repository import Repository
from ad_machine.storage.asset_store import AssetStore
from api.routes.ad_machine import router as ad_machine_router, _emit_event


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_url = os.environ.get("DATABASE_URL", "")
    if db_url:
        pool = await asyncpg.create_pool(db_url, min_size=2, max_size=10)
    else:
        # Allow startup without Postgres for local development / testing
        pool = None

    anthropic_client = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    asset_store = AssetStore()

    if pool:
        repo = Repository(pool)
    else:
        repo = None

    orchestrator = AdMachineOrchestrator(
        repo=repo,
        asset_store=asset_store,
        anthropic_client=anthropic_client,
        event_emitter=_emit_event,
    )

    app.state.repo = repo
    app.state.asset_store = asset_store
    app.state.orchestrator = orchestrator

    yield

    if pool:
        await pool.close()


app = FastAPI(
    title="AI Ad Creative Machine",
    description="Web3/DeFi end-to-end ad production: Opus planning, Sonnet copy, Gemini visuals.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ad_machine_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"service": "AI Ad Creative Machine", "version": "1.0.0"}
