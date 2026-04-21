"""
CLI end-to-end test — runs the full pipeline without a database or browser.
Usage:
    cd backend
    python tests/ad_machine/test_pipeline_cli.py [--stage brief|copy|images|all]

Requires: ANTHROPIC_API_KEY, GEMINI_API_KEY in environment.
"""
import asyncio
import json
import os
import sys
import argparse
from pathlib import Path

# Allow imports from backend root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from anthropic import AsyncAnthropic
from ad_machine.schemas.project_input import ProjectInput
from ad_machine.planners.opus_planner import OpusPlanner
from ad_machine.generators.copy_generator import CopyGenerator
from ad_machine.storage.asset_store import AssetStore


def _load_fixture(fixture_id: str = "sample_defi_v1") -> dict:
    fixtures_path = Path(__file__).parent / "fixtures" / "sample_projects.json"
    fixtures = json.loads(fixtures_path.read_text())
    for f in fixtures:
        if f["id"] == fixture_id:
            return f["input"]
    raise ValueError(f"Fixture {fixture_id!r} not found")


def _make_input(raw: dict) -> ProjectInput:
    # Map fixture keys → ProjectInput fields
    return ProjectInput(
        protocol_name=raw["protocol_name"],
        protocol_type=raw.get("protocol_type", "yield_aggregator"),
        chains=raw["chains"],
        token_symbol=raw.get("token_ticker"),
        token_live=bool(raw.get("token_ticker")),
        stage=raw.get("stage", "mainnet_growth"),
        tvl=str(raw["tvl"]) if raw.get("tvl") else None,
        active_users=str(raw.get("monthly_active_users")) if raw.get("monthly_active_users") else None,
        target_audience_raw=raw["target_audience_raw"],
        competitive_positioning=raw.get("extra_context", "N/A"),
        differentiators=[raw["differentiators"]] if isinstance(raw["differentiators"], str) else raw["differentiators"],
        campaign_goal=raw.get("campaign_goal", "awareness"),
        budget_tier=raw.get("budget_tier", "5k_25k"),
        voice_profile_id=raw.get("voice_profile_id") or "demo",
    )


async def test_brief(project_input: ProjectInput) -> None:
    print("\n=== STAGE 1: Opus Brief ===")
    client = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    planner = OpusPlanner(client)
    brief = await planner.plan(project_input)
    print(f"  Protocol: {brief.protocol_name}")
    print(f"  Angles generated: {len(brief.angles)}")
    for a in brief.angles:
        print(f"    [{a.angle_id}] {a.headline} — {a.core_tension}")
    print(f"  Segments: {[s.segment_id for s in brief.segments]}")
    print(f"  Platform plans: {list(brief.platform_plans.keys())}")
    print("  BRIEF OK")
    return brief


async def test_copy(brief, project_input: ProjectInput) -> None:
    print("\n=== STAGE 2: Sonnet Copy Generation ===")
    client = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    generator = CopyGenerator(client)
    copy_pack = await generator.generate(brief, project_input)
    print(f"  Platforms: {list(copy_pack.variations.keys())}")
    for platform, variations in copy_pack.variations.items():
        print(f"  {platform}: {len(variations)} variations")
        for v in variations[:1]:
            flags = len(v.compliance_flags)
            print(f"    v{v.variation_id[:8]} slop={v.slop_score:.1f} voice={v.voice_score:.1f} flags={flags}")
    print(f"  Overall voice: {copy_pack.overall_voice_score:.1f}")
    print(f"  Overall slop: {copy_pack.overall_slop_score:.1f}")
    print("  COPY OK")
    return copy_pack


async def test_images(brief, copy_pack) -> None:
    print("\n=== STAGE 3: Gemini Image Generation ===")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        print("  SKIP — GEMINI_API_KEY not set")
        return
    try:
        import google.generativeai  # noqa: F401
    except ImportError:
        print("  SKIP — google-genai not installed")
        return

    store = AssetStore(provider="local")
    from ad_machine.generators.image_generator import ImageGenerator
    generator = ImageGenerator(store)
    assets = await generator.generate(brief, copy_pack, project_id="cli-test")
    print(f"  Assets generated: {len(assets)}")
    for a in assets[:3]:
        print(f"    {a.platform} {a.spec_name} → {a.url}")
    print("  IMAGES OK")
    return assets


async def main(stage: str) -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set")
        sys.exit(1)

    raw = _load_fixture("sample_defi_v1")
    project_input = _make_input(raw)
    print(f"Running pipeline for: {project_input.protocol_name}")

    brief = None
    copy_pack = None

    if stage in ("brief", "copy", "images", "all"):
        brief = await test_brief(project_input)

    if stage in ("copy", "images", "all") and brief:
        copy_pack = await test_copy(brief, project_input)

    if stage in ("images", "all") and brief and copy_pack:
        await test_images(brief, copy_pack)

    print("\nAll requested stages passed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", default="copy", choices=["brief", "copy", "images", "all"])
    args = parser.parse_args()
    asyncio.run(main(args.stage))
