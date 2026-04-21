"""
Pushes selected creative pairings to Buffer as drafts.
"""
import os
import httpx
from ad_machine.schemas.creative_pack import CreativePack, CreativePairing
from ad_machine.schemas.copy_pack import CopyPack

BUFFER_API_BASE = "https://api.bufferapp.com/1"

PLATFORM_PROFILE_MAP = {
    "x": "twitter",
    "linkedin": "linkedin",
    "meta": "facebook",
}


async def push_to_buffer(
    creative_pack: CreativePack,
    copy_pack: CopyPack,
    pairing_ids: list[str],
    profile_map: dict[str, str],  # platform -> buffer profile_id
    access_token: str | None = None,
) -> dict:
    token = access_token or os.environ.get("BUFFER_ACCESS_TOKEN", "")
    if not token:
        raise ValueError("BUFFER_ACCESS_TOKEN not configured")

    selected_pairings = [p for p in creative_pack.pairings if p.pairing_id in pairing_ids]
    all_variations = {
        v.variation_id: v
        for variations in copy_pack.variations.values()
        for v in variations
    }

    results = {"pushed": [], "skipped": [], "errors": []}

    async with httpx.AsyncClient(timeout=30) as http:
        for pairing in selected_pairings:
            profile_id = profile_map.get(pairing.platform)
            if not profile_id:
                results["skipped"].append({
                    "pairing_id": pairing.pairing_id,
                    "reason": f"No Buffer profile mapped for {pairing.platform}",
                })
                continue

            copy_var = all_variations.get(pairing.copy_variation_id)
            if not copy_var:
                results["skipped"].append({
                    "pairing_id": pairing.pairing_id,
                    "reason": "Copy variation not found",
                })
                continue

            text = _extract_post_text(copy_var.platform, copy_var.payload)
            if not text:
                results["skipped"].append({
                    "pairing_id": pairing.pairing_id,
                    "reason": "Could not extract text from copy variation",
                })
                continue

            image_urls = [
                creative_pack.visual_assets[aid].url
                for aid in pairing.visual_asset_ids
                if aid in creative_pack.visual_assets
                and not creative_pack.visual_assets[aid].url.startswith("file://")
            ]

            payload: dict = {
                "profile_ids[]": profile_id,
                "text": text,
                "now": "false",
            }
            for i, url in enumerate(image_urls[:4]):
                payload[f"media[photo][{i}]"] = url

            try:
                resp = await http.post(
                    f"{BUFFER_API_BASE}/updates/create.json",
                    data=payload,
                    headers={"Authorization": f"Bearer {token}"},
                )
                resp.raise_for_status()
                results["pushed"].append({
                    "pairing_id": pairing.pairing_id,
                    "platform": pairing.platform,
                    "buffer_update_id": resp.json().get("id"),
                })
            except Exception as e:
                results["errors"].append({
                    "pairing_id": pairing.pairing_id,
                    "error": str(e),
                })

    return results


def _extract_post_text(platform: str, payload: dict) -> str:
    if platform == "x":
        return payload.get("primary_text", "")
    elif platform == "linkedin":
        hook = payload.get("intro_hook", "")
        body = payload.get("body", "")
        cta = payload.get("cta_line", "")
        parts = [p for p in [hook, body, cta] if p]
        return "\n\n".join(parts)
    elif platform == "meta":
        return payload.get("primary_text", "")
    return ""
