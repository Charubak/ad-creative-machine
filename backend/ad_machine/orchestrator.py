import asyncio
import uuid
from datetime import datetime, timezone
from typing import Callable, Awaitable

from anthropic import AsyncAnthropic

from ad_machine.planners.opus_planner import OpusPlanner
from ad_machine.generators.copy_generator import CopyGenerator
from ad_machine.generators.image_generator import ImageGenerator
from ad_machine.recommenders.platform_picker import recommend_extra_platforms
from ad_machine.storage.repository import Repository
from ad_machine.storage.asset_store import AssetStore
from ad_machine.schemas.brief import CreativeBrief
from ad_machine.schemas.copy_pack import CopyPack
from ad_machine.schemas.creative_pack import CreativePack, CreativePairing

EventEmitter = Callable[[str, str, dict], Awaitable[None]]


class AdMachineOrchestrator:

    def __init__(
        self,
        repo: Repository,
        asset_store: AssetStore,
        anthropic_client: AsyncAnthropic,
        event_emitter: EventEmitter,
    ):
        self.repo = repo
        self.asset_store = asset_store
        self.client = anthropic_client
        self.emit = event_emitter

    async def run_job(self, project_id: str, job_id: str, voice_profile_id: str) -> None:
        try:
            await self.repo.update_job(job_id, status="running", current_stage="opus_planning")
            await self.emit(job_id, "stage_started", {
                "stage": "opus_planning",
                "started_at": _now(),
            })

            project_input = await self.repo.get_project_input(project_id)
            planner = OpusPlanner(self.client)
            brief = await planner.plan(project_input, project_id)
            brief_id = await self.repo.save_brief(brief)

            await self.emit(job_id, "stage_completed", {
                "stage": "opus_planning",
                "brief_id": brief_id,
                "angles_count": len(brief.angles),
                "output_summary": f"Brief generated with {len(brief.angles)} angles",
            })

            await self.repo.update_job(job_id, current_stage="copy_generation")
            await self.emit(job_id, "stage_started", {
                "stage": "copy_generation",
                "started_at": _now(),
            })

            copy_gen = CopyGenerator(self.client, voice_profile_id)
            copy_pack = await copy_gen.generate_pack(brief, brief_id)
            copy_pack_id = await self.repo.save_copy_pack(copy_pack)

            for platform in copy_pack.variations:
                await self.emit(job_id, "substage_progress", {
                    "stage": "copy_generation",
                    "platform": platform,
                    "status": "completed",
                    "variations": len(copy_pack.variations[platform]),
                })

            await self.emit(job_id, "stage_completed", {
                "stage": "copy_generation",
                "copy_pack_id": copy_pack_id,
                "voice_score": copy_pack.overall_voice_score,
                "slop_score": copy_pack.overall_slop_score,
                "compliance_flag_count": len(copy_pack.overall_compliance_flags),
                "output_summary": f"Copy generated for {len(copy_pack.variations)} platforms",
            })

            await self.repo.update_job(job_id, current_stage="image_generation")
            await self.emit(job_id, "stage_started", {
                "stage": "image_generation",
                "started_at": _now(),
            })

            brand_assets = await self.repo.get_brand_assets(project_id) if hasattr(self.repo, "get_brand_assets") else []
            image_gen = ImageGenerator(self.asset_store)
            visuals_by_platform = await image_gen.generate_for_pack(brief, copy_pack, project_id, brand_assets=brand_assets)
            await self.repo.save_visual_assets(visuals_by_platform, project_id, brief_id)
            asset_count = sum(len(v) for v in visuals_by_platform.values())

            await self.emit(job_id, "stage_completed", {
                "stage": "image_generation",
                "asset_count": asset_count,
                "output_summary": f"{asset_count} visuals generated",
            })

            await self.repo.update_job(job_id, current_stage="assembly")
            await self.emit(job_id, "stage_started", {
                "stage": "assembly",
                "started_at": _now(),
            })

            pairings = self._build_pairings(copy_pack, visuals_by_platform)
            visuals_flat = {a.asset_id: a for vs in visuals_by_platform.values() for a in vs}

            creative_pack = CreativePack(
                pack_id=str(uuid.uuid4()),
                project_id=project_id,
                brief_id=brief_id,
                copy_pack_id=copy_pack_id,
                pairings=pairings,
                visual_assets=visuals_flat,
                created_at=datetime.now(timezone.utc),
            )

            pack_id = await self.repo.save_creative_pack(creative_pack)

            await self.emit(job_id, "stage_completed", {
                "stage": "assembly",
                "pairing_count": len(pairings),
                "output_summary": f"Assembly complete: {len(pairings)} pairings",
            })

            await self.emit(job_id, "pack_ready", {"creative_pack_id": pack_id})
            await self.repo.update_job(
                job_id,
                status="succeeded",
                current_stage=None,
                completed_at=datetime.now(timezone.utc),
            )

        except Exception as e:
            await self.repo.update_job(job_id, status="failed", error=str(e))
            await self.emit(job_id, "job_failed", {"error": str(e)})
            raise

    async def run_iteration(
        self,
        project_id: str,
        job_id: str,
        voice_profile_id: str,
        parent_brief_id: str,
        iteration_context: str,
    ) -> None:
        try:
            await self.repo.update_job(job_id, status="running", current_stage="opus_planning")
            await self.emit(job_id, "stage_started", {
                "stage": "opus_planning",
                "started_at": _now(),
                "round": "iteration",
            })

            project_input = await self.repo.get_project_input(project_id)
            parent_brief = await self.repo.get_brief(parent_brief_id)

            planner = OpusPlanner(self.client)
            brief = await planner.plan(
                project_input,
                project_id,
                round_number=parent_brief.round_number + 1,
                parent_brief_id=parent_brief_id,
                iteration_context=iteration_context,
            )
            brief_id = await self.repo.save_brief(brief)

            await self.emit(job_id, "stage_completed", {
                "stage": "opus_planning",
                "brief_id": brief_id,
                "round_number": brief.round_number,
            })

            # Reuse copy + image pipeline
            copy_gen = CopyGenerator(self.client, voice_profile_id)
            copy_pack = await copy_gen.generate_pack(brief, brief_id)
            copy_pack_id = await self.repo.save_copy_pack(copy_pack)

            brand_assets = await self.repo.get_brand_assets(project_id) if hasattr(self.repo, "get_brand_assets") else []
            image_gen = ImageGenerator(self.asset_store)
            visuals_by_platform = await image_gen.generate_for_pack(brief, copy_pack, project_id, brand_assets=brand_assets)
            await self.repo.save_visual_assets(visuals_by_platform, project_id, brief_id)

            pairings = self._build_pairings(copy_pack, visuals_by_platform)
            visuals_flat = {a.asset_id: a for vs in visuals_by_platform.values() for a in vs}

            creative_pack = CreativePack(
                pack_id=str(uuid.uuid4()),
                project_id=project_id,
                brief_id=brief_id,
                copy_pack_id=copy_pack_id,
                pairings=pairings,
                visual_assets=visuals_flat,
                created_at=datetime.now(timezone.utc),
            )
            pack_id = await self.repo.save_creative_pack(creative_pack)

            await self.emit(job_id, "pack_ready", {"creative_pack_id": pack_id})
            await self.repo.update_job(
                job_id,
                status="succeeded",
                completed_at=datetime.now(timezone.utc),
            )

        except Exception as e:
            await self.repo.update_job(job_id, status="failed", error=str(e))
            await self.emit(job_id, "job_failed", {"error": str(e)})
            raise

    def _build_pairings(self, copy_pack: CopyPack, visuals: dict) -> list[CreativePairing]:
        pairings = []
        for platform, copies in copy_pack.variations.items():
            platform_visuals = visuals.get(platform, [])
            specs_map: dict[str, list] = {}
            for v in platform_visuals:
                specs_map.setdefault(v.spec_name, []).append(v)

            for i, copy_var in enumerate(copies):
                visual_ids = []
                for spec_name, spec_visuals in specs_map.items():
                    if i < len(spec_visuals):
                        visual_ids.append(spec_visuals[i].asset_id)
                    elif spec_visuals:
                        visual_ids.append(spec_visuals[i % len(spec_visuals)].asset_id)

                pairings.append(CreativePairing(
                    pairing_id=str(uuid.uuid4()),
                    platform=platform,
                    copy_variation_id=copy_var.variation_id,
                    visual_asset_ids=visual_ids,
                ))
        return pairings


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
