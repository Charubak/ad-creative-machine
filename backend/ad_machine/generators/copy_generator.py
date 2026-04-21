import asyncio
import json
import uuid
from anthropic import AsyncAnthropic
from ad_machine.schemas.brief import CreativeBrief
from ad_machine.schemas.copy_pack import CopyPack, CopyVariation
from ad_machine.validators import platform_specs, compliance, slop_check

SONNET_MODEL = "claude-sonnet-4-6"

PLATFORM_SCHEMAS = {
    "x": '''{
  "variations": [
    {
      "primary_text": "string, max 280 chars",
      "char_count": 247,
      "angle_used": "angle name from brief",
      "format": "single | thread_starter",
      "thread_continuation": ["string"],
      "cta_type": "link_click | reply | follow | quote",
      "hashtags": ["#string"],
      "mentions": ["@string"]
    }
  ]
}''',
    "linkedin": '''{
  "variations": [
    {
      "intro_hook": "string, max 150 chars",
      "body": "string, max 1200 chars",
      "cta_line": "string",
      "angle_used": "string",
      "tone_check": "institutional | thought-leadership | case-study"
    }
  ]
}''',
    "meta": '''{
  "variations": [
    {
      "primary_text": "string, max 125 visible chars",
      "headline": "string, max 40 chars",
      "description": "string, max 30 chars",
      "cta_button": "Learn More | Sign Up | Get Started | Trade Now",
      "angle_used": "string"
    }
  ]
}''',
    "google_rsa": '''{
  "headlines": [{"text": "string, max 30 chars", "theme": "string"}],
  "descriptions": [{"text": "string, max 90 chars", "theme": "string"}],
  "path1": "string, max 15 chars",
  "path2": "string, max 15 chars"
}''',
}

VARIATIONS_PER_PLATFORM = {"x": 5, "linkedin": 5, "meta": 5, "google_rsa": 1}

SONNET_SYSTEM_TEMPLATE = """You are a Web3 ad copywriter generating production-ready ad variations for a {platform} campaign. You are part of a pipeline: your output will be voice-calibrated and slop-checked downstream, but your job is to get it 80% of the way there in the writer's actual voice on the first pass.

Writer voice profile:
- Direct, plain-spoken, no fluff, no hedging
- Crypto-native: assumes audience knows TVL, APR, mainnet, points
- NEVER uses em dashes. Use commas, colons, or rewrite the sentence.
- No corporate marketing speak ("unlock," "leverage," "empower," "revolutionize")
- No false urgency unless backed by a real deadline
- Confident, not promotional. Skin in the game tone.

Voice samples for reference:
{voice_samples}

Platform constraints for {platform}:
{platform_constraints}

Compliance constraints (HARD):
- Never use: "guaranteed returns," "risk-free yield," "guaranteed APR," "passive income guaranteed," "no risk," "100% safe"
- Never make forward-looking price predictions
- Avoid "investment advice" framing
- Project-specific constraints: {project_compliance_constraints}

Output format: strict JSON matching the schema below. No prose. No markdown.
"""

SONNET_USER_TEMPLATE = """STRATEGIC BRIEF
===============
{brief_summary}

Primary angle for this platform: {primary_angle}
Tone directive: {tone_directive}
CTA: {cta}
Audience segments to address: {relevant_segments}
Narrative hooks available: {relevant_hooks}
Evidence to draw on: {evidence_facts}

GENERATE
========
Produce {n_variations} variations matching the schema below. Each variation must be distinct in angle execution, not just word swaps.

{platform_schema}
"""


class CopyGenerator:

    def __init__(self, anthropic_client: AsyncAnthropic, voice_profile_id: str):
        self.client = anthropic_client
        self.voice_profile_id = voice_profile_id

    async def generate_pack(self, brief: CreativeBrief, brief_id: str) -> CopyPack:
        platforms = list(brief.platform_strategy.keys())
        tasks = [self._generate_for_platform(brief, p) for p in platforms]
        raw_results = await asyncio.gather(*tasks)
        per_platform = dict(zip(platforms, raw_results))

        calibrated = {}
        for platform, variations in per_platform.items():
            processed = []
            for var in variations:
                var = platform_specs.validate_and_trim(var, platform)
                flags = compliance.lint(var, brief.compliance_constraints)
                var.compliance_flags = flags
                var.slop_score = slop_check.score_slop(_extract_text_from_variation(var))
                var.voice_score = 7.5  # placeholder; real scoring requires voice doc
                processed.append(var)
            calibrated[platform] = processed

        all_vars = [v for vs in calibrated.values() for v in vs]
        overall_voice = sum(v.voice_score or 0 for v in all_vars) / max(len(all_vars), 1)
        overall_slop = sum(v.slop_score or 0 for v in all_vars) / max(len(all_vars), 1)
        overall_flags = [f for v in all_vars for f in v.compliance_flags]

        return CopyPack(
            pack_id=str(uuid.uuid4()),
            brief_id=brief_id,
            variations=calibrated,
            overall_voice_score=round(overall_voice, 2),
            overall_slop_score=round(overall_slop, 2),
            overall_compliance_flags=overall_flags,
        )

    async def _generate_for_platform(self, brief: CreativeBrief, platform: str) -> list[CopyVariation]:
        plan = brief.platform_strategy[platform]
        relevant_hooks = [h for h in brief.narrative_hooks if platform in h.use_for_platforms]
        evidence = [e for a in brief.angles for e in a.evidence_to_use]
        voice_samples = await self._fetch_voice_samples(self.voice_profile_id)
        platform_constraints = platform_specs.constraints_text(platform)

        system = SONNET_SYSTEM_TEMPLATE.format(
            platform=platform,
            voice_samples=voice_samples,
            platform_constraints=platform_constraints,
            project_compliance_constraints="; ".join(brief.compliance_constraints),
        )

        user = SONNET_USER_TEMPLATE.format(
            brief_summary=brief.brief_summary_for_copy_agent,
            primary_angle=plan.primary_angle,
            tone_directive=plan.tone_directive,
            cta=plan.cta,
            relevant_segments="; ".join(s.name for s in brief.audience_segments),
            relevant_hooks="\n".join(f"- {h.hook}" for h in relevant_hooks) or "none",
            evidence_facts="; ".join(evidence[:10]) or "see brief",
            n_variations=VARIATIONS_PER_PLATFORM.get(platform, 5),
            platform_schema=PLATFORM_SCHEMAS[platform],
        )

        response = await self.client.messages.create(
            model=SONNET_MODEL,
            max_tokens=4000,
            system=system,
            messages=[{"role": "user", "content": user}],
            temperature=0.85,
        )

        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1].lstrip("json\n")
        if raw.endswith("```"):
            raw = raw.rsplit("```", 1)[0]

        data = json.loads(raw)
        return self._to_variations(data, platform)

    def _to_variations(self, raw_data: dict, platform: str) -> list[CopyVariation]:
        if platform == "google_rsa":
            return [CopyVariation(
                variation_id=str(uuid.uuid4()),
                platform=platform,
                angle_used="rsa_assembly",
                payload=raw_data,
            )]

        out = []
        for v in raw_data.get("variations", []):
            out.append(CopyVariation(
                variation_id=str(uuid.uuid4()),
                platform=platform,
                angle_used=v.get("angle_used", ""),
                payload=v,
                char_count=v.get("char_count"),
            ))
        return out

    async def _fetch_voice_samples(self, voice_profile_id: str) -> str:
        try:
            import sys
            import os
            content_machine_path = os.getenv("AI_CONTENT_MACHINE_PATH", "")
            if content_machine_path:
                sys.path.insert(0, content_machine_path)
            from agents.voice_builder import load_voice_document
            voices_path = os.getenv("VOICES_PATH", "voices")
            doc = load_voice_document(voice_profile_id, base_path=voices_path)
            return doc[:1500]
        except Exception:
            return "Direct. Crypto-native. No fluff. Skin in the game tone. No em dashes."


def _extract_text_from_variation(var: CopyVariation) -> str:
    parts = []
    payload = var.payload
    for key, val in payload.items():
        if isinstance(val, str):
            parts.append(val)
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    for v in item.values():
                        if isinstance(v, str):
                            parts.append(v)
    return " ".join(parts)
