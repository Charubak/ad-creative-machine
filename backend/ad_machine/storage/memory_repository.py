"""
In-memory repository — same interface as Repository but no Postgres.
Used when DATABASE_URL is not configured (local dev, demos, Fly.io without attached DB).
Data is ephemeral and lost on restart. Perfect for demo/hobby deployments.
"""
import json
import uuid
from datetime import datetime, timezone

from ad_machine.schemas.project_input import ProjectInput
from ad_machine.schemas.brief import CreativeBrief
from ad_machine.schemas.copy_pack import CopyPack
from ad_machine.schemas.creative_pack import CreativePack, VisualAsset


class MemoryRepository:

    def __init__(self):
        self._projects: dict[str, dict] = {}
        self._jobs: dict[str, dict] = {}
        self._briefs: dict[str, str] = {}
        self._copy_packs: dict[str, str] = {}
        self._visual_assets: list[dict] = []
        self._creative_packs: dict[str, str] = {}
        self._performance: dict[str, dict] = {}
        self._brand_assets: dict[str, list[dict]] = {}  # project_id → list of {path, mime_type, filename}
        self.pool = None  # not supported in memory mode

    # ── Projects ──────────────────────────────────────────────────────────────

    async def create_project(self, project_input: ProjectInput, user_id: str) -> str:
        project_id = str(uuid.uuid4())
        self._projects[project_id] = {
            "project_id": project_id,
            "user_id": user_id,
            "protocol_name": project_input.protocol_name,
            "inputs": project_input.model_dump_json(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        return project_id

    async def get_project_input(self, project_id: str) -> ProjectInput:
        if project_id not in self._projects:
            raise KeyError(f"Project {project_id} not found")
        return ProjectInput(**json.loads(self._projects[project_id]["inputs"]))

    async def get_project(self, project_id: str) -> dict:
        if project_id not in self._projects:
            raise KeyError(f"Project {project_id} not found")
        return self._projects[project_id]

    # ── Jobs ──────────────────────────────────────────────────────────────────

    async def create_job(self, project_id: str) -> str:
        job_id = str(uuid.uuid4())
        self._jobs[job_id] = {
            "job_id": job_id,
            "project_id": project_id,
            "status": "queued",
            "current_stage": None,
            "error": None,
            "progress_events": [],
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
        }
        return job_id

    async def update_job(self, job_id: str, **kwargs) -> None:
        if job_id not in self._jobs:
            return
        allowed = {"status", "current_stage", "error", "completed_at"}
        for k, v in kwargs.items():
            if k in allowed:
                self._jobs[job_id][k] = v.isoformat() if hasattr(v, "isoformat") else v

    async def append_job_event(self, job_id: str, event: dict) -> None:
        if job_id in self._jobs:
            self._jobs[job_id]["progress_events"].append(event)

    async def get_job(self, job_id: str) -> dict:
        if job_id not in self._jobs:
            raise KeyError(f"Job {job_id} not found")
        return self._jobs[job_id]

    # ── Briefs ────────────────────────────────────────────────────────────────

    async def save_brief(self, brief: CreativeBrief) -> str:
        brief_id = str(uuid.uuid4())
        self._briefs[brief_id] = brief.model_dump_json()
        return brief_id

    async def get_brief(self, brief_id: str) -> CreativeBrief:
        if brief_id not in self._briefs:
            raise KeyError(f"Brief {brief_id} not found")
        return CreativeBrief(**json.loads(self._briefs[brief_id]))

    # ── Copy Packs ────────────────────────────────────────────────────────────

    async def save_copy_pack(self, pack: CopyPack) -> str:
        self._copy_packs[pack.pack_id] = pack.model_dump_json()
        return pack.pack_id

    async def get_copy_pack(self, pack_id: str) -> CopyPack:
        if pack_id not in self._copy_packs:
            raise KeyError(f"CopyPack {pack_id} not found")
        return CopyPack(**json.loads(self._copy_packs[pack_id]))

    async def update_copy_variation(self, pack_id: str, variation_id: str, new_payload: dict) -> None:
        pack = await self.get_copy_pack(pack_id)
        for platform, variations in pack.variations.items():
            for i, v in enumerate(variations):
                if v.variation_id == variation_id:
                    pack.variations[platform][i].payload = new_payload
                    break
        self._copy_packs[pack_id] = pack.model_dump_json()

    # ── Visual Assets ─────────────────────────────────────────────────────────

    async def save_visual_assets(
        self, visuals_by_platform: dict[str, list[VisualAsset]], project_id: str, brief_id: str
    ) -> None:
        for platform, assets in visuals_by_platform.items():
            for a in assets:
                self._visual_assets.append({
                    "asset_id": a.asset_id,
                    "project_id": project_id,
                    "brief_id": brief_id,
                    "storage_url": a.url,
                    "platform": a.platform,
                    "spec_name": a.spec_name,
                    "width": a.width,
                    "height": a.height,
                    "prompt_used": a.prompt_used,
                    "model": a.model,
                })

    # ── Creative Packs ────────────────────────────────────────────────────────

    async def save_creative_pack(self, pack: CreativePack) -> str:
        self._creative_packs[pack.pack_id] = pack.model_dump_json()
        return pack.pack_id

    async def get_creative_pack(self, pack_id: str) -> CreativePack:
        if pack_id not in self._creative_packs:
            raise KeyError(f"CreativePack {pack_id} not found")
        return CreativePack(**json.loads(self._creative_packs[pack_id]))

    async def update_pairing(self, pack_id: str, pairing_id: str, updates: dict) -> None:
        pack = await self.get_creative_pack(pack_id)
        for i, p in enumerate(pack.pairings):
            if p.pairing_id == pairing_id:
                for k, v in updates.items():
                    setattr(pack.pairings[i], k, v)
                break
        self._creative_packs[pack_id] = pack.model_dump_json()

    async def update_export_manifest(self, pack_id: str, manifest: dict) -> None:
        pass  # no-op in memory mode

    # ── Brand Assets ─────────────────────────────────────────────────────────

    async def save_brand_asset(self, project_id: str, path: str, filename: str, mime_type: str) -> None:
        self._brand_assets.setdefault(project_id, []).append({
            "path": path,
            "filename": filename,
            "mime_type": mime_type,
        })

    async def get_brand_assets(self, project_id: str) -> list[dict]:
        return self._brand_assets.get(project_id, [])

    # ── Performance ───────────────────────────────────────────────────────────

    async def save_performance_rows(self, rows: list[dict], creative_pack_id: str) -> list[str]:
        ids = []
        for row in rows:
            perf_id = str(uuid.uuid4())
            self._performance[perf_id] = {
                "performance_id": perf_id,
                "creative_pack_id": creative_pack_id,
                **row,
            }
            ids.append(perf_id)
        return ids

    async def update_performance(self, performance_id: str, label: str | None, notes: str | None) -> None:
        if performance_id in self._performance:
            if label is not None:
                self._performance[performance_id]["user_label"] = label
            if notes is not None:
                self._performance[performance_id]["user_notes"] = notes

    async def get_performance_for_pack(self, creative_pack_id: str) -> list[dict]:
        return [
            v for v in self._performance.values()
            if v.get("creative_pack_id") == creative_pack_id
        ]
