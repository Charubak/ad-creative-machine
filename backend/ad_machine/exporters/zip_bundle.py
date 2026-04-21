"""
Builds a ZIP bundle: per-platform markdown copy file + all images + manifest.json
"""
import io
import json
import os
import zipfile
from datetime import datetime, timezone

import httpx

from ad_machine.schemas.creative_pack import CreativePack
from ad_machine.schemas.copy_pack import CopyPack
from ad_machine.schemas.brief import CreativeBrief
from ad_machine.storage.asset_store import AssetStore


async def build_zip(
    creative_pack: CreativePack,
    copy_pack: CopyPack,
    brief: CreativeBrief,
    asset_store: AssetStore,
) -> bytes:
    buf = io.BytesIO()

    async with httpx.AsyncClient(timeout=30) as http:
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            # manifest.json
            manifest = {
                "pack_id": creative_pack.pack_id,
                "project_id": creative_pack.project_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "pairings": [p.model_dump() for p in creative_pack.pairings],
            }
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))

            # compliance_report.json
            flag_report = [f.model_dump() for f in copy_pack.overall_compliance_flags]
            zf.writestr("compliance_report.json", json.dumps(flag_report, indent=2))

            # brief_summary.md
            brief_md = _render_brief_md(brief)
            zf.writestr("brief_summary.md", brief_md)

            # Per-platform copy files
            for platform, variations in copy_pack.variations.items():
                lines = [f"# {platform.upper()} Copy Pack\n\n"]
                for i, v in enumerate(variations, 1):
                    lines.append(f"## Variation {i} — {v.angle_used}\n")
                    lines.append(_render_copy_variation(v))
                    if v.compliance_flags:
                        lines.append("\n**Compliance flags:**\n")
                        for f in v.compliance_flags:
                            lines.append(f"- [{f.severity.upper()}] {f.rule}: `{f.matched_text}`\n")
                    lines.append("\n---\n\n")
                zf.writestr(f"copy/{platform}.md", "".join(lines))

            # Images
            for asset_id, asset in creative_pack.visual_assets.items():
                if asset.url.startswith("file://"):
                    local_path = asset.url[7:]
                    if os.path.exists(local_path):
                        with open(local_path, "rb") as f:
                            img_bytes = f.read()
                        zf.writestr(
                            f"images/{asset.platform}/{asset.spec_name}_{asset_id[:8]}.png",
                            img_bytes,
                        )
                else:
                    try:
                        resp = await http.get(asset.url)
                        resp.raise_for_status()
                        zf.writestr(
                            f"images/{asset.platform}/{asset.spec_name}_{asset_id[:8]}.png",
                            resp.content,
                        )
                    except Exception as e:
                        zf.writestr(
                            f"images/{asset.platform}/{asset.spec_name}_{asset_id[:8]}.error.txt",
                            str(e),
                        )

    buf.seek(0)
    return buf.read()


def _render_brief_md(brief: CreativeBrief) -> str:
    lines = [f"# Strategic Brief — {brief.project_id}\n\n"]
    lines.append(f"**Round:** {brief.round_number}\n\n")
    lines.append("## Angles\n\n")
    for a in brief.angles:
        lines.append(f"### {a.rank}. {a.name}\n")
        lines.append(f"{a.thesis}\n\n")
        lines.append(f"**Emotion:** {a.primary_emotion}  \n")
        lines.append(f"**Evidence:** {', '.join(a.evidence_to_use)}\n\n")
    lines.append("## Summary for Copy Agent\n\n")
    lines.append(brief.brief_summary_for_copy_agent + "\n")
    return "".join(lines)


def _render_copy_variation(v) -> str:
    payload = v.payload
    parts = []
    for key, val in payload.items():
        if isinstance(val, str):
            parts.append(f"**{key}:** {val}")
        elif isinstance(val, list):
            items = ", ".join(str(x) for x in val)
            parts.append(f"**{key}:** {items}")
    return "\n".join(parts) + "\n"
