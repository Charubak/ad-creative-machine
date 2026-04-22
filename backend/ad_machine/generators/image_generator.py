import asyncio
import os
import uuid
from datetime import datetime
from ad_machine.schemas.brief import CreativeBrief
from ad_machine.schemas.copy_pack import CopyPack, CopyVariation
from ad_machine.schemas.creative_pack import VisualAsset
from ad_machine.storage.asset_store import AssetStore

# Primary: gemini-2.5-flash-image ("Nano Banana") — native image generation
# Fallback: imagen-4.0-fast-generate-001 — dedicated Imagen 4 model
IMAGEN_MODEL = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
IMAGEN_FALLBACK = "imagen-4.0-fast-generate-001"

RATIO_MAP = {
    "16:9":   "16:9",
    "1:1":    "1:1",
    "1.91:1": "16:9",
    "4:5":    "4:5",
    "9:16":   "9:16",
    "4:3":    "4:3",
    "3:4":    "3:4",
}

PLATFORM_IMAGE_SPECS = {
    "x": [
        {"name": "wide",   "width": 1600, "height": 900,  "ratio": "16:9"},
        {"name": "square", "width": 1200, "height": 1200, "ratio": "1:1"},
    ],
    "linkedin": [
        {"name": "feed",   "width": 1200, "height": 627,  "ratio": "1.91:1"},
        {"name": "square", "width": 1200, "height": 1200, "ratio": "1:1"},
    ],
    "meta": [
        {"name": "square",   "width": 1080, "height": 1080, "ratio": "1:1"},
        {"name": "portrait", "width": 1080, "height": 1350, "ratio": "4:5"},
        {"name": "story",    "width": 1080, "height": 1920, "ratio": "9:16"},
    ],
}

TOP_VARIATIONS_PER_PLATFORM = 1  # 1 image per platform = 3 total (cost control)
BATCH_SIZE = int(os.getenv("IMAGE_GEN_BATCH_SIZE", "3"))
BATCH_DELAY_S = float(os.getenv("IMAGE_GEN_BATCH_DELAY_S", "2.0"))


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
        self, brief: CreativeBrief, copy_pack: CopyPack, project_id: str,
        brand_assets: list[dict] | None = None,
    ) -> dict[str, list[VisualAsset]]:
        brand_context = _load_brand_context(brand_assets or [])
        jobs = []
        for platform, copies in copy_pack.variations.items():
            specs = PLATFORM_IMAGE_SPECS.get(platform)
            if not specs:
                continue
            for spec in specs[:1]:  # 1 spec per platform to keep it fast
                for copy_var in copies[:TOP_VARIATIONS_PER_PLATFORM]:
                    prompt = self._build_prompt(brief, platform, spec, copy_var, brand_context)
                    jobs.append((prompt, spec, platform, project_id, brand_context))

        results = []
        for i in range(0, len(jobs), BATCH_SIZE):
            batch = jobs[i:i + BATCH_SIZE]
            batch_tasks = [self._generate_one(prompt, spec, platform, project_id, brand_context) for prompt, spec, platform, project_id, brand_context in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            for r in batch_results:
                if isinstance(r, Exception):
                    print(f"[image_gen] FAILED {type(r).__name__}: {r}")
                    continue
                if r is not None:
                    results.append(r)
            if i + BATCH_SIZE < len(jobs):
                await asyncio.sleep(BATCH_DELAY_S)

        print(f"[image_gen] Generated {len(results)} images from {len(jobs)} jobs")
        return _organize_by_platform(results)

    async def regenerate_one(
        self,
        brief: CreativeBrief,
        platform: str,
        spec_name: str,
        copy_variation: CopyVariation,
        project_id: str,
        brand_assets: list[dict] | None = None,
    ) -> VisualAsset:
        brand_context = _load_brand_context(brand_assets or [])
        spec = next(s for s in PLATFORM_IMAGE_SPECS[platform] if s["name"] == spec_name)
        prompt = self._build_prompt(brief, platform, spec, copy_variation, brand_context)
        return await self._generate_one(prompt, spec, platform, project_id, brand_context)

    async def _generate_one(
        self, prompt: str, spec: dict, platform: str, project_id: str,
        brand_context: dict | None = None,
    ) -> VisualAsset | None:
        client = self._get_client()
        model_used = IMAGEN_MODEL

        image_bytes = await _try_generate_content(client, model_used, prompt, brand_context)

        # Fallback: Imagen 4 generate_images API (no multimodal, text-only prompt)
        if image_bytes is None:
            print(f"[image_gen] Primary model failed, trying Imagen 4 fallback: {IMAGEN_FALLBACK}")
            model_used = IMAGEN_FALLBACK
            image_bytes = await _try_imagen_generate(client, model_used, prompt, spec)

        if not image_bytes:
            print(f"[image_gen] No image data returned for {platform}/{spec['name']}")
            return None

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
            model=model_used,
            created_at=datetime.utcnow(),
        )

    def _build_prompt(
        self, brief: CreativeBrief, platform: str, spec: dict, copy_var: CopyVariation,
        brand_context: dict | None = None,
    ) -> str:
        vd = brief.visual_direction
        theme = _select_imagery_theme(vd.imagery_themes, copy_var.angle_used)
        composition = _composition_for_ratio(spec["ratio"])
        text_zone = _text_overlay_zone(platform, spec)
        per_platform_note = vd.per_platform_visual_notes.get(platform, "")
        avoid_list = ', '.join(vd.imagery_to_avoid) if vd.imagery_to_avoid else "stock-photo aesthetic, generic gradients"

        base = f"""{vd.aesthetic}. {theme}. Color palette: {', '.join(vd.color_palette[:4])}. {vd.typography_feel} typography feel. {composition} composition. {per_platform_note}. Ad creative with clear focal point, room for {text_zone} text overlay, scroll-stopping at thumbnail size. No text, no words, no logos in the image. Avoid: {avoid_list}, stock photos, generic gradients, AI-art look."""

        # Append brand notes if provided
        if brand_context and brand_context.get("notes"):
            base += f" Brand style requirements: {brand_context['notes']}."

        return base.strip()


def _load_brand_context(brand_assets: list[dict]) -> dict:
    """Load brand asset files into memory for use in generation. Returns {notes, images: [{bytes, mime}]}."""
    import base64
    context = {"notes": "", "images": []}
    for asset in brand_assets:
        mime = asset.get("mime_type", "")
        path = asset.get("path", "")
        if not path:
            continue
        # Text notes embedded in filenames aren't useful — only load actual image files
        if mime.startswith("image/") or path.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
            try:
                with open(path, "rb") as f:
                    data = f.read()
                actual_mime = mime if mime.startswith("image/") else "image/png"
                context["images"].append({"bytes": data, "mime": actual_mime, "filename": asset.get("filename", "")})
                print(f"[image_gen] Loaded brand image: {asset.get('filename')} ({len(data)} bytes)")
            except Exception as e:
                print(f"[image_gen] Could not load brand file {path}: {e}")
    return context


async def _try_generate_content(client, model: str, prompt: str, brand_context: dict | None = None):
    """Try generate_content with IMAGE modality; return PNG bytes or None.
    If brand_context has reference images, include them as multimodal input."""
    from google.genai import types
    try:
        # Build contents — text prompt + optional brand reference images
        contents = []
        if brand_context and brand_context.get("images"):
            for img in brand_context["images"][:3]:  # max 3 reference images
                contents.append(types.Part.from_bytes(data=img["bytes"], mime_type=img["mime"]))
            contents.append(types.Part.from_text(
                f"Use the above brand reference image(s) as style/colour/aesthetic guidance ONLY. "
                f"Do NOT copy them literally. Now generate: {prompt}"
            ))
        else:
            contents = prompt

        response = await client.aio.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                return part.inline_data.data
        print(f"[image_gen] generate_content returned no inline_data for model={model}")
        return None
    except Exception as e:
        print(f"[image_gen] generate_content failed for model={model}: {type(e).__name__}: {e}")
        return None


async def _try_imagen_generate(client, model: str, prompt: str, spec: dict):
    """Try Imagen 4 generate_images API and return PNG bytes or None."""
    from google.genai import types
    try:
        ratio = RATIO_MAP.get(spec["ratio"], "1:1")
        response = await client.aio.models.generate_images(
            model=model,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio=ratio,
                output_mime_type="image/png",
            ),
        )
        if response.generated_images:
            img = response.generated_images[0]
            return img.image.image_bytes
        print(f"[image_gen] imagen generate_images returned no images for model={model}")
        return None
    except Exception as e:
        print(f"[image_gen] imagen generate_images failed for model={model}: {type(e).__name__}: {e}")
        return None


def _select_imagery_theme(themes: list[str], angle: str) -> str:
    if not themes:
        return "Clean editorial product illustration"
    idx = hash(angle) % len(themes)
    return themes[idx]


def _composition_for_ratio(ratio: str) -> str:
    return {
        "16:9":   "horizontal hero with subject left-center, negative space right",
        "1:1":    "centered subject with breathing room around edges",
        "1.91:1": "horizontal banner with subject offset left",
        "4:5":    "portrait with subject centered, vertical flow",
        "9:16":   "vertical story with subject top-center, space at bottom for caption",
    }.get(ratio, "balanced")


def _text_overlay_zone(platform: str, spec: dict) -> str:
    if spec["ratio"] == "9:16":
        return "lower third"
    return "right side or bottom"


def _organize_by_platform(assets: list[VisualAsset]) -> dict[str, list[VisualAsset]]:
    out: dict[str, list[VisualAsset]] = {}
    for a in assets:
        out.setdefault(a.platform, []).append(a)
    return out
