import asyncio
import os
import uuid
from datetime import datetime
from ad_machine.schemas.brief import CreativeBrief
from ad_machine.schemas.copy_pack import CopyPack, CopyVariation
from ad_machine.schemas.creative_pack import VisualAsset
from ad_machine.storage.asset_store import AssetStore

# Verify this model ID against https://ai.google.dev/gemini-api/docs/image-generation at build time
GEMINI_MODEL = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.0-flash-preview-image-generation")

PLATFORM_IMAGE_SPECS = {
    "x": [
        {"name": "wide", "width": 1600, "height": 900, "ratio": "16:9"},
        {"name": "square", "width": 1200, "height": 1200, "ratio": "1:1"},
    ],
    "linkedin": [
        {"name": "feed", "width": 1200, "height": 627, "ratio": "1.91:1"},
        {"name": "square", "width": 1200, "height": 1200, "ratio": "1:1"},
    ],
    "meta": [
        {"name": "square", "width": 1080, "height": 1080, "ratio": "1:1"},
        {"name": "portrait", "width": 1080, "height": 1350, "ratio": "4:5"},
        {"name": "story", "width": 1080, "height": 1920, "ratio": "9:16"},
    ],
}

TOP_VARIATIONS_PER_PLATFORM = 3
BATCH_SIZE = int(os.getenv("IMAGE_GEN_BATCH_SIZE", "5"))
BATCH_DELAY_S = float(os.getenv("IMAGE_GEN_BATCH_DELAY_S", "1.0"))


class ImageGenerator:

    def __init__(self, asset_store: AssetStore):
        self.asset_store = asset_store
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        return self._client

    async def generate_for_pack(
        self, brief: CreativeBrief, copy_pack: CopyPack, project_id: str
    ) -> dict[str, list[VisualAsset]]:
        jobs = []
        for platform, copies in copy_pack.variations.items():
            specs = PLATFORM_IMAGE_SPECS.get(platform)
            if not specs:
                continue
            for spec in specs:
                for copy_var in copies[:TOP_VARIATIONS_PER_PLATFORM]:
                    prompt = self._build_prompt(brief, platform, spec, copy_var)
                    jobs.append((prompt, spec, platform, project_id))

        results = []
        for i in range(0, len(jobs), BATCH_SIZE):
            batch = jobs[i:i + BATCH_SIZE]
            batch_tasks = [self._generate_one(*j) for j in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            for r in batch_results:
                if isinstance(r, Exception):
                    print(f"Image gen failed: {r}")
                    continue
                results.append(r)
            if i + BATCH_SIZE < len(jobs):
                await asyncio.sleep(BATCH_DELAY_S)

        return _organize_by_platform(results)

    async def regenerate_one(
        self,
        brief: CreativeBrief,
        platform: str,
        spec_name: str,
        copy_variation: CopyVariation,
        project_id: str,
    ) -> VisualAsset:
        spec = next(s for s in PLATFORM_IMAGE_SPECS[platform] if s["name"] == spec_name)
        prompt = self._build_prompt(brief, platform, spec, copy_variation)
        return await self._generate_one(prompt, spec, platform, project_id)

    async def _generate_one(
        self, prompt: str, spec: dict, platform: str, project_id: str
    ) -> VisualAsset:
        from google.genai import types

        client = self._get_client()
        response = await client.aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(aspect_ratio=spec["ratio"]),
            ),
        )

        image_part = next(
            p for p in response.candidates[0].content.parts if p.inline_data is not None
        )
        image_bytes = image_part.inline_data.data
        asset_id = str(uuid.uuid4())

        url = await self.asset_store.upload(
            image_bytes,
            key=f"projects/{project_id}/visuals/{platform}_{spec['name']}_{asset_id}.png",
            content_type="image/png",
        )

        return VisualAsset(
            asset_id=asset_id,
            url=url,
            platform=platform,
            spec_name=spec["name"],
            width=spec["width"],
            height=spec["height"],
            prompt_used=prompt,
            model=GEMINI_MODEL,
            created_at=datetime.utcnow(),
        )

    def _build_prompt(
        self, brief: CreativeBrief, platform: str, spec: dict, copy_var: CopyVariation
    ) -> str:
        vd = brief.visual_direction
        theme = _select_imagery_theme(vd.imagery_themes, copy_var.angle_used)
        composition = _composition_for_ratio(spec["ratio"])
        text_zone = _text_overlay_zone(platform, spec)
        per_platform_note = vd.per_platform_visual_notes.get(platform, "")

        return f"""{vd.aesthetic}

Subject: {theme}

Color palette: {', '.join(vd.color_palette)}

Typography feel: {vd.typography_feel}

Platform-specific note: {per_platform_note}

Composition: {composition}

Avoid: {', '.join(vd.imagery_to_avoid)}, generic crypto imagery, stock-photo aesthetic, generic gradients, AI-art look, hands holding phones with Bitcoin logos, robot imagery

Image must work as an ad creative: clear focal point, room for {text_zone} text overlay if needed, scroll-stopping at thumbnail size.

Brand context: This is for an ad about a Web3 protocol.""".strip()


def _select_imagery_theme(themes: list[str], angle: str) -> str:
    if not themes:
        return "abstract editorial illustration related to decentralized finance"
    idx = hash(angle) % len(themes)
    return themes[idx]


def _composition_for_ratio(ratio: str) -> str:
    return {
        "16:9": "horizontal, hero subject left or center, negative space right for text",
        "1:1": "centered subject, room around edges",
        "1.91:1": "horizontal banner, subject offset, room for text",
        "4:5": "portrait, subject centered, vertical flow",
        "9:16": "vertical story, subject top or center, room for caption at bottom",
    }.get(ratio, "balanced composition")


def _text_overlay_zone(platform: str, spec: dict) -> str:
    if spec["ratio"] == "9:16":
        return "lower third"
    return "right side or bottom"


def _organize_by_platform(assets: list[VisualAsset]) -> dict[str, list[VisualAsset]]:
    out: dict[str, list[VisualAsset]] = {}
    for a in assets:
        out.setdefault(a.platform, []).append(a)
    return out
