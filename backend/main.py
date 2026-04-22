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
import api.routes.ad_machine as _ad_machine_routes
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
        from ad_machine.storage.memory_repository import MemoryRepository
        repo = MemoryRepository()

    orchestrator = AdMachineOrchestrator(
        repo=repo,
        asset_store=asset_store,
        anthropic_client=anthropic_client,
        event_emitter=_emit_event,
    )

    app.state.repo = repo
    app.state.asset_store = asset_store
    app.state.orchestrator = orchestrator

    # Populate module-level singletons so route handlers work without Request typing
    _ad_machine_routes._repo = repo
    _ad_machine_routes._orchestrator_instance = orchestrator
    _ad_machine_routes._asset_store_instance = asset_store

    yield

    if pool:
        await pool.close()


app = FastAPI(
    title="AI Ad Creative Machine",
    description="End-to-end AI ad production for any industry: Opus planning, Sonnet copy, Gemini visuals.",
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


@app.get("/debug/gemini-models")
async def list_gemini_models():
    """Temp diagnostic — remove before production."""
    try:
        from google import genai
        key = os.environ.get("GEMINI_API_KEY", "")
        if not key:
            return {"error": "No GEMINI_API_KEY set"}
        client = genai.Client(api_key=key)
        models = list(client.models.list())
        return {
            "count": len(models),
            "models": [
                {"name": m.name, "display": getattr(m, "display_name", ""), 
                 "methods": [str(x) for x in getattr(m, "supported_actions", [])]}
                for m in models
            ]
        }
    except Exception as e:
        return {"error": str(e)}
