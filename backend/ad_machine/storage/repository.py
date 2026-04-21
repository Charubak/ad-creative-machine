"""
Postgres repository for all ad machine state.
Uses asyncpg directly for simplicity; swap to SQLAlchemy async if ORM is preferred.
"""
import json
import uuid
from datetime import datetime
from typing import Any
import asyncpg

from ad_machine.schemas.project_input import ProjectInput
from ad_machine.schemas.brief import CreativeBrief
from ad_machine.schemas.copy_pack import CopyPack
from ad_machine.schemas.creative_pack import CreativePack, VisualAsset


class Repository:

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    # ── Projects ──────────────────────────────────────────────────────────────

    async def create_project(self, project_input: ProjectInput, user_id: str) -> str:
        project_id = str(uuid.uuid4())
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO ad_projects (project_id, user_id, protocol_name, inputs)
                VALUES ($1, $2, $3, $4)
                """,
                project_id, user_id,
                project_input.protocol_name,
                project_input.model_dump_json(),
            )
        return project_id

    async def get_project_input(self, project_id: str) -> ProjectInput:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT inputs FROM ad_projects WHERE project_id = $1", project_id
            )
        if not row:
            raise KeyError(f"Project {project_id} not found")
        return ProjectInput(**json.loads(row["inputs"]))

    async def get_project(self, project_id: str) -> dict:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM ad_projects WHERE project_id = $1", project_id
            )
        if not row:
            raise KeyError(f"Project {project_id} not found")
        return dict(row)

    # ── Jobs ──────────────────────────────────────────────────────────────────

    async def create_job(self, project_id: str) -> str:
        job_id = str(uuid.uuid4())
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO ad_jobs (job_id, project_id, status, started_at)
                VALUES ($1, $2, 'queued', NOW())
                """,
                job_id, project_id,
            )
        return job_id

    async def update_job(self, job_id: str, **kwargs) -> None:
        allowed = {"status", "current_stage", "error", "completed_at"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return
        set_clauses = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(updates))
        values = list(updates.values())
        async with self.pool.acquire() as conn:
            await conn.execute(
                f"UPDATE ad_jobs SET {set_clauses} WHERE job_id = $1",
                job_id, *values,
            )

    async def append_job_event(self, job_id: str, event: dict) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE ad_jobs
                SET progress_events = progress_events || $2::jsonb
                WHERE job_id = $1
                """,
                job_id, json.dumps([event]),
            )

    async def get_job(self, job_id: str) -> dict:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM ad_jobs WHERE job_id = $1", job_id
            )
        if not row:
            raise KeyError(f"Job {job_id} not found")
        return dict(row)

    # ── Briefs ────────────────────────────────────────────────────────────────

    async def save_brief(self, brief: CreativeBrief) -> str:
        brief_id = str(uuid.uuid4())
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO ad_briefs
                  (brief_id, project_id, round_number, parent_brief_id, brief_json, opus_model)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                brief_id,
                brief.project_id,
                brief.round_number,
                brief.parent_brief_id,
                brief.model_dump_json(),
                "claude-opus-4-7",
            )
        return brief_id

    async def get_brief(self, brief_id: str) -> CreativeBrief:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT brief_json FROM ad_briefs WHERE brief_id = $1", brief_id
            )
        if not row:
            raise KeyError(f"Brief {brief_id} not found")
        return CreativeBrief(**json.loads(row["brief_json"]))

    # ── Copy Packs ────────────────────────────────────────────────────────────

    async def save_copy_pack(self, pack: CopyPack) -> str:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO ad_copy_packs
                  (pack_id, brief_id, pack_json, sonnet_model, voice_score, slop_score)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                pack.pack_id,
                pack.brief_id,
                pack.model_dump_json(),
                "claude-sonnet-4-6",
                pack.overall_voice_score,
                pack.overall_slop_score,
            )
        return pack.pack_id

    async def get_copy_pack(self, pack_id: str) -> CopyPack:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT pack_json FROM ad_copy_packs WHERE pack_id = $1", pack_id
            )
        if not row:
            raise KeyError(f"CopyPack {pack_id} not found")
        return CopyPack(**json.loads(row["pack_json"]))

    async def update_copy_variation(self, pack_id: str, variation_id: str, new_payload: dict) -> None:
        pack = await self.get_copy_pack(pack_id)
        for platform, variations in pack.variations.items():
            for i, v in enumerate(variations):
                if v.variation_id == variation_id:
                    pack.variations[platform][i].payload = new_payload
                    break
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE ad_copy_packs SET pack_json = $2 WHERE pack_id = $1",
                pack_id, pack.model_dump_json(),
            )

    # ── Visual Assets ─────────────────────────────────────────────────────────

    async def save_visual_assets(
        self, visuals_by_platform: dict[str, list[VisualAsset]], project_id: str, brief_id: str
    ) -> None:
        async with self.pool.acquire() as conn:
            for platform, assets in visuals_by_platform.items():
                for a in assets:
                    await conn.execute(
                        """
                        INSERT INTO ad_visual_assets
                          (asset_id, project_id, brief_id, storage_url, platform,
                           spec_name, width, height, prompt_used, model)
                        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                        """,
                        a.asset_id, project_id, brief_id, a.url, a.platform,
                        a.spec_name, a.width, a.height, a.prompt_used, a.model,
                    )

    # ── Creative Packs ────────────────────────────────────────────────────────

    async def save_creative_pack(self, pack: CreativePack) -> str:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO ad_creative_packs
                  (pack_id, project_id, brief_id, copy_pack_id, pack_json)
                VALUES ($1, $2, $3, $4, $5)
                """,
                pack.pack_id,
                pack.project_id,
                pack.brief_id,
                pack.copy_pack_id,
                pack.model_dump_json(),
            )
        return pack.pack_id

    async def get_creative_pack(self, pack_id: str) -> CreativePack:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT pack_json FROM ad_creative_packs WHERE pack_id = $1", pack_id
            )
        if not row:
            raise KeyError(f"CreativePack {pack_id} not found")
        return CreativePack(**json.loads(row["pack_json"]))

    async def update_pairing(self, pack_id: str, pairing_id: str, updates: dict) -> None:
        pack = await self.get_creative_pack(pack_id)
        for i, p in enumerate(pack.pairings):
            if p.pairing_id == pairing_id:
                for k, v in updates.items():
                    setattr(pack.pairings[i], k, v)
                break
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE ad_creative_packs SET pack_json = $2 WHERE pack_id = $1",
                pack_id, pack.model_dump_json(),
            )

    async def update_export_manifest(self, pack_id: str, manifest: dict) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE ad_creative_packs SET export_manifest = $2 WHERE pack_id = $1",
                pack_id, json.dumps(manifest),
            )

    # ── Performance ───────────────────────────────────────────────────────────

    async def save_performance_rows(self, rows: list[dict], creative_pack_id: str) -> list[str]:
        ids = []
        async with self.pool.acquire() as conn:
            for row in rows:
                perf_id = str(uuid.uuid4())
                await conn.execute(
                    """
                    INSERT INTO ad_pairing_performance
                      (performance_id, pairing_id, creative_pack_id, platform,
                       impressions, clicks, ctr, conversions, cpa, spend, days_running)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
                    """,
                    perf_id,
                    row.get("pairing_id", ""),
                    creative_pack_id,
                    row.get("platform", ""),
                    row.get("impressions", 0),
                    row.get("clicks", 0),
                    row.get("ctr", 0.0),
                    row.get("conversions"),
                    row.get("cpa"),
                    row.get("spend", 0.0),
                    row.get("days_running", 0),
                )
                ids.append(perf_id)
        return ids

    async def update_performance(self, performance_id: str, label: str | None, notes: str | None) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE ad_pairing_performance
                SET user_label = COALESCE($2, user_label),
                    user_notes = COALESCE($3, user_notes)
                WHERE performance_id = $1
                """,
                performance_id, label, notes,
            )

    async def get_performance_for_pack(self, creative_pack_id: str) -> list[dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM ad_pairing_performance WHERE creative_pack_id = $1",
                creative_pack_id,
            )
        return [dict(r) for r in rows]
