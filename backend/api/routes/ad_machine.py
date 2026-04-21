"""
FastAPI router for the Ad Creative Machine.
Mount at /api/ad-machine in main.py.
"""
import asyncio
import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse, Response
from pydantic import BaseModel

from ad_machine.orchestrator import AdMachineOrchestrator
from ad_machine.schemas.project_input import ProjectInput
from ad_machine.feedback.csv_ingest import parse_csv, save_column_mapping
from ad_machine.feedback.iteration_loop import build_iteration_context
from ad_machine.exporters import zip_bundle, google_rsa_csv, buffer_push

router = APIRouter(prefix="/api/ad-machine", tags=["ad-machine"])

# ── In-memory SSE event bus ────────────────────────────────────────────────────
# For production, swap this with Redis pub/sub.
_sse_queues: dict[str, list[asyncio.Queue]] = {}


async def _emit_event(job_id: str, event_type: str, payload: dict) -> None:
    event_str = f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"
    for q in _sse_queues.get(job_id, []):
        await q.put(event_str)


def _get_orchestrator(request) -> AdMachineOrchestrator:
    return request.app.state.orchestrator


def _get_repo(request):
    return request.app.state.repo


def _get_asset_store(request):
    return request.app.state.asset_store


def _get_copy_pack_store(request):
    return request.app.state.repo


# ── Request/Response models ────────────────────────────────────────────────────

class RunRequest(BaseModel):
    voice_profile_id: str = "demo"


class EditCopyRequest(BaseModel):
    payload: dict


class RepairPairingRequest(BaseModel):
    visual_asset_ids: list[str]


class ExportRsaCsvRequest(BaseModel):
    campaign_name: str = "Ad Machine Campaign"
    ad_group_name: str = "Ad Machine Ad Group"
    final_url: str = ""
    path1: str = ""
    path2: str = ""


class BufferPushRequest(BaseModel):
    pairing_ids: list[str]
    profile_map: dict[str, str]


class IterateRequest(BaseModel):
    user_notes: str = ""


class PerformanceLabelRequest(BaseModel):
    user_label: str | None = None
    user_notes: str | None = None


class ColumnMappingRequest(BaseModel):
    platform: str
    mapping: dict[str, str]


# ── Projects ───────────────────────────────────────────────────────────────────

@router.post("/projects")
async def create_project(project_input: ProjectInput, request=None):
    repo = _get_repo(request)
    user_id = str(uuid.uuid4())  # replace with real auth user_id
    project_id = await repo.create_project(project_input, user_id)
    return {"project_id": project_id}


@router.get("/projects/{project_id}")
async def get_project(project_id: str, request=None):
    repo = _get_repo(request)
    try:
        project = await repo.get_project(project_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/projects/{project_id}/run")
async def run_project(
    project_id: str,
    run_req: RunRequest,
    background_tasks: BackgroundTasks,
    request=None,
):
    repo = _get_repo(request)
    orchestrator = _get_orchestrator(request)

    try:
        await repo.get_project(project_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")

    job_id = await repo.create_job(project_id)

    async def _run():
        await orchestrator.run_job(project_id, job_id, run_req.voice_profile_id)

    background_tasks.add_task(_run)
    return {"job_id": job_id, "project_id": project_id}


@router.post("/projects/{project_id}/iterate")
async def iterate_project(
    project_id: str,
    iter_req: IterateRequest,
    background_tasks: BackgroundTasks,
    request=None,
):
    repo = _get_repo(request)
    orchestrator = _get_orchestrator(request)

    # Find latest brief for this project
    async with repo.pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT b.brief_id, b.brief_json, cp.pack_id as creative_pack_id
            FROM ad_briefs b
            JOIN ad_creative_packs cp ON cp.brief_id = b.brief_id
            WHERE b.project_id = $1
            ORDER BY b.round_number DESC LIMIT 1
            """,
            project_id,
        )

    if not row:
        raise HTTPException(status_code=404, detail="No previous run found for this project")

    import json as _json
    from ad_machine.schemas.brief import CreativeBrief
    brief = CreativeBrief(**_json.loads(row["brief_json"]))

    # Build iteration context from performance data
    perf_rows = await repo.get_performance_for_pack(row["creative_pack_id"])
    creative_pack = await repo.get_creative_pack(row["creative_pack_id"])
    iteration_context = build_iteration_context(perf_rows, creative_pack.pairings, iter_req.user_notes)

    job_id = await repo.create_job(project_id)

    async def _run():
        await orchestrator.run_iteration(
            project_id, job_id, "demo",
            row["brief_id"], iteration_context,
        )

    background_tasks.add_task(_run)
    return {"job_id": job_id, "project_id": project_id}


# ── Jobs ───────────────────────────────────────────────────────────────────────

@router.get("/jobs/{job_id}")
async def get_job(job_id: str, request=None):
    repo = _get_repo(request)
    try:
        return await repo.get_job(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")


@router.get("/jobs/{job_id}/stream")
async def stream_job(job_id: str, request=None):
    q: asyncio.Queue = asyncio.Queue()
    _sse_queues.setdefault(job_id, []).append(q)

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=30)
                    yield event
                    if '"pack_ready"' in event or '"job_failed"' in event:
                        break
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            queues = _sse_queues.get(job_id, [])
            if q in queues:
                queues.remove(q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── Briefs ────────────────────────────────────────────────────────────────────

@router.get("/briefs/{brief_id}")
async def get_brief(brief_id: str, request=None):
    repo = _get_repo(request)
    try:
        brief = await repo.get_brief(brief_id)
        return brief.model_dump()
    except KeyError:
        raise HTTPException(status_code=404, detail="Brief not found")


# ── Copy Packs ────────────────────────────────────────────────────────────────

@router.get("/copy-packs/{pack_id}")
async def get_copy_pack(pack_id: str, request=None):
    repo = _get_repo(request)
    try:
        pack = await repo.get_copy_pack(pack_id)
        return pack.model_dump()
    except KeyError:
        raise HTTPException(status_code=404, detail="Copy pack not found")


@router.patch("/copy-variations/{variation_id}")
async def edit_copy_variation(variation_id: str, edit_req: EditCopyRequest, request=None):
    repo = _get_repo(request)
    # Find which pack owns this variation
    async with repo.pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT pack_id FROM ad_copy_packs
            WHERE pack_json::text LIKE $1
            ORDER BY created_at DESC LIMIT 1
            """,
            f"%{variation_id}%",
        )
    if not row:
        raise HTTPException(status_code=404, detail="Variation not found")

    await repo.update_copy_variation(row["pack_id"], variation_id, edit_req.payload)
    return {"variation_id": variation_id, "updated": True}


@router.post("/copy-variations/{variation_id}/regenerate")
async def regenerate_copy(variation_id: str, request=None):
    # TODO: find the variation's pack + brief, regenerate just that variation
    raise HTTPException(status_code=501, detail="Single variation regeneration coming in v1.1")


# ── Visual Assets ─────────────────────────────────────────────────────────────

@router.post("/visual-assets/{asset_id}/regenerate")
async def regenerate_visual(asset_id: str, background_tasks: BackgroundTasks, request=None):
    raise HTTPException(status_code=501, detail="Single visual regeneration coming in v1.1")


# ── Creative Packs ────────────────────────────────────────────────────────────

@router.get("/creative-packs/{pack_id}")
async def get_creative_pack(pack_id: str, request=None):
    repo = _get_repo(request)
    try:
        pack = await repo.get_creative_pack(pack_id)
        return pack.model_dump()
    except KeyError:
        raise HTTPException(status_code=404, detail="Creative pack not found")


@router.patch("/pairings/{pairing_id}")
async def repair_pairing(pairing_id: str, repair_req: RepairPairingRequest, request=None):
    repo = _get_repo(request)
    # Find pack owning this pairing
    async with repo.pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT pack_id FROM ad_creative_packs WHERE pack_json::text LIKE $1 LIMIT 1",
            f"%{pairing_id}%",
        )
    if not row:
        raise HTTPException(status_code=404, detail="Pairing not found")

    await repo.update_pairing(row["pack_id"], pairing_id, {
        "visual_asset_ids": repair_req.visual_asset_ids
    })
    return {"pairing_id": pairing_id, "updated": True}


# ── Exports ───────────────────────────────────────────────────────────────────

@router.post("/creative-packs/{pack_id}/export/zip")
async def export_zip(pack_id: str, request=None):
    repo = _get_repo(request)
    asset_store = _get_asset_store(request)

    try:
        pack = await repo.get_creative_pack(pack_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Creative pack not found")

    copy_pack = await repo.get_copy_pack(pack.copy_pack_id)
    brief = await repo.get_brief(pack.brief_id)

    zip_bytes = await zip_bundle.build_zip(pack, copy_pack, brief, asset_store)

    key = f"exports/{pack_id}/bundle.zip"
    url = await asset_store.upload(zip_bytes, key, content_type="application/zip")

    await repo.update_export_manifest(pack_id, {"zip_url": url})
    return {"zip_url": url}


@router.post("/creative-packs/{pack_id}/export/google-rsa-csv")
async def export_rsa_csv(pack_id: str, export_req: ExportRsaCsvRequest, request=None):
    repo = _get_repo(request)
    asset_store = _get_asset_store(request)

    try:
        pack = await repo.get_creative_pack(pack_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Creative pack not found")

    copy_pack = await repo.get_copy_pack(pack.copy_pack_id)
    csv_content = google_rsa_csv.build_rsa_csv(
        copy_pack,
        campaign_name=export_req.campaign_name,
        ad_group_name=export_req.ad_group_name,
        final_url=export_req.final_url,
        path1=export_req.path1,
        path2=export_req.path2,
    )

    key = f"exports/{pack_id}/google_rsa.csv"
    url = await asset_store.upload(csv_content.encode(), key, content_type="text/csv")

    return {"csv_url": url}


@router.post("/creative-packs/{pack_id}/export/buffer")
async def export_buffer(pack_id: str, push_req: BufferPushRequest, request=None):
    repo = _get_repo(request)

    try:
        pack = await repo.get_creative_pack(pack_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Creative pack not found")

    copy_pack = await repo.get_copy_pack(pack.copy_pack_id)

    result = await buffer_push.push_to_buffer(
        pack, copy_pack, push_req.pairing_ids, push_req.profile_map
    )
    return result


# ── Performance ───────────────────────────────────────────────────────────────

@router.post("/creative-packs/{pack_id}/performance/upload")
async def upload_performance(
    pack_id: str,
    platform: str,
    file: UploadFile = File(...),
    pairing_id_column: str | None = None,
    request=None,
):
    repo = _get_repo(request)

    try:
        await repo.get_creative_pack(pack_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Creative pack not found")

    content = await file.read()
    rows = parse_csv(content, platform, pairing_id_column=pairing_id_column)
    saved_ids = await repo.save_performance_rows(rows, pack_id)

    return {"rows_parsed": len(rows), "performance_ids": saved_ids, "rows": rows}


@router.post("/performance/column-mapping")
async def save_mapping(mapping_req: ColumnMappingRequest):
    save_column_mapping(mapping_req.platform, mapping_req.mapping)
    return {"saved": True, "platform": mapping_req.platform}


@router.patch("/performance/{performance_id}")
async def label_performance(
    performance_id: str,
    label_req: PerformanceLabelRequest,
    request=None,
):
    repo = _get_repo(request)
    await repo.update_performance(performance_id, label_req.user_label, label_req.user_notes)
    return {"performance_id": performance_id, "updated": True}
