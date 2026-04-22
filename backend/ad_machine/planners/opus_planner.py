import json
from anthropic import AsyncAnthropic
from ad_machine.schemas.brief import CreativeBrief
from ad_machine.schemas.project_input import ProjectInput

OPUS_MODEL = "claude-sonnet-4-5"

OPUS_SYSTEM_PROMPT = """You are a senior growth strategist and performance marketer with 10+ years of paid acquisition experience across every major industry: SaaS, e-commerce, fintech, health/wellness, crypto/DeFi, consumer apps, and B2B platforms.

You are the PLANNING layer of a multi-agent ad creative system. A copywriting agent and an image generation agent will consume your output downstream. They cannot read minds. Be concrete and specific.

Your operating principles:

1. Industry-aware strategy. You adapt your approach based on the product's industry:
   - SaaS/Tech: feature benefits, time-to-value, ROI framing, social proof from logos
   - E-commerce/D2C: product photography vibes, lifestyle, urgency, social proof from reviews
   - Fintech: trust, security, simplicity, numbers/savings, regulatory compliance awareness
   - Health/Wellness: transformation, credibility, before/after, expert endorsement
   - Crypto/DeFi: trustless ownership, yield numbers, TVL social proof, community belonging, narrative urgency
   - Consumer apps: outcome-focused, accessible language, app store social proof
   - B2B: ROI/efficiency, case studies, peer credibility, stakeholder-specific messaging

2. Compliance-aware. You never recommend "guaranteed returns," "risk-free," "guaranteed results," or misleading superlatives. Flag any borderline claims in compliance_constraints.

3. Platform-native voice mapping:
   - X/Twitter: punchy, declarative, lowercase acceptable, hook-first, replies-bait when appropriate
   - LinkedIn: institutional, data-led, case-study tone, frames products as professional infrastructure
   - Meta (FB/IG): outcome-focused, benefit-led, accessible language, assumes minimal prior knowledge
   - Google RSA: intent-matching, problem-solution, keyword-dense without being spammy

4. Angle library (pick the 3-5 strongest for THIS project and audience):
   - Problem-agitate-solve: amplify the pain, then present solution
   - Social proof / numbers: impressive metric, user count, revenue saved
   - Narrative urgency: launch, limited time, new version, seasonal hook
   - Identity / belonging: "people like you use this"
   - Counter-positioning: vs named or implied competitor ("unlike X, we...")
   - Outcome hook: focus on the specific transformation/result
   - Trust / credibility: audits, awards, press mentions, team credentials
   - Curiosity gap: tease insight or reveal without full context

5. Output format is strict JSON matching the provided schema. No prose outside the JSON. No markdown fences.

You do not write final ad copy. You produce the strategic brief. The copywriting agent does the writing.
"""

USER_PROMPT_TEMPLATE = """PROJECT INPUT
=============
Product/Brand name: {protocol_name}
Industry: {industry}
Product category: {protocol_type}
Stage: {stage}
Campaign goal: {campaign_goal}

Key differentiators: {differentiators}
Competitive positioning: {competitive_positioning}
Target audience (user-defined): {target_audience_raw}

Live metrics (if any):
  - {other_metrics}
  - Active users: {active_users}
  - Key metric 1: {tvl}
  - Key metric 2: {volume_24h}
  - Key metric 3: {apr}

Geographic focus: {geo}
Excluded geos (compliance): {excluded_geos}
Brand voice notes: {brand_voice_notes}
Existing brand assets / references: {brand_refs}
Budget tier: {budget_tier}
{iteration_context}

OUTPUT
======
Return a JSON object matching this exact schema. No additional fields. No prose outside the JSON.

{{
  "angles": [
    {{
      "name": "string, max 6 words",
      "thesis": "1-2 sentences explaining why this angle works for this specific product and audience",
      "primary_emotion": "one of: greed, fear, belonging, status, curiosity, frustration, fomo, trust",
      "evidence_to_use": ["specific metric or fact from the input"],
      "rank": 1
    }}
  ],
  "killed_angles": [
    {{ "name": "string", "reason": "why this was considered and rejected" }}
  ],
  "audience_segments": [
    {{
      "name": "string",
      "description": "who they are in 1 sentence",
      "platforms_to_reach_them": ["x", "linkedin", "meta", "google_rsa"],
      "best_angles_for_this_segment": ["angle name from above"],
      "objections_to_overcome": ["string"]
    }}
  ],
  "platform_strategy": {{
    "x": {{
      "primary_angle": "angle name",
      "tone_directive": "specific tone instruction for the copy agent",
      "format_recommendation": "single tweet | thread | quote-bait | reply-bait",
      "creative_format": "static image | meme | chart | product screenshot",
      "cta": "specific CTA text suggestion"
    }},
    "linkedin": {{ "primary_angle": "...", "tone_directive": "...", "format_recommendation": "...", "creative_format": "...", "cta": "..." }},
    "meta": {{ "primary_angle": "...", "tone_directive": "...", "format_recommendation": "...", "creative_format": "...", "cta": "..." }},
    "google_rsa": {{
      "primary_angle": "angle name",
      "tone_directive": "string",
      "cta": "...",
      "headline_themes": ["3-5 themes for headline rotation"],
      "description_themes": ["2-3 themes for description rotation"],
      "keyword_intent_buckets": ["informational | comparison | branded | problem-aware"]
    }}
  }},
  "narrative_hooks": [
    {{ "hook": "specific opening line concept", "use_for_platforms": ["x", "meta"], "rationale": "1 sentence" }}
  ],
  "visual_direction": {{
    "aesthetic": "string describing visual style",
    "color_palette": ["hex codes or named colors"],
    "imagery_themes": ["concrete things to depict"],
    "imagery_to_avoid": ["generic stock photos, cliché visuals, overused tropes for this industry"],
    "typography_feel": "string",
    "per_platform_visual_notes": {{ "x": "...", "linkedin": "...", "meta": "...", "google_rsa": "N/A - text only" }}
  }},
  "compliance_constraints": ["specific phrases or claims to avoid for this product/industry/jurisdiction"],
  "recommended_extra_platforms": [
    {{ "platform": "reddit | tiktok | pinterest | youtube", "recommend": true, "rationale": "1-2 sentences", "suggested_budget_split_pct": 15 }}
  ],
  "brief_summary_for_copy_agent": "3-4 sentences the copy agent should read before generating anything"
}}
"""


class OpusPlanner:

    def __init__(self, anthropic_client: AsyncAnthropic):
        self.client = anthropic_client

    async def plan(
        self,
        project_input: ProjectInput,
        project_id: str,
        round_number: int = 1,
        parent_brief_id: str | None = None,
        iteration_context: str = "",
    ) -> CreativeBrief:
        user_prompt = USER_PROMPT_TEMPLATE.format(
            protocol_name=project_input.protocol_name,
            industry=getattr(project_input, "industry", "other"),
            protocol_type=project_input.protocol_type,
            stage=project_input.stage,
            campaign_goal=project_input.campaign_goal,
            differentiators="; ".join(project_input.differentiators),
            competitive_positioning=project_input.competitive_positioning,
            target_audience_raw=project_input.target_audience_raw,
            other_metrics=project_input.other_metrics or "N/A",
            active_users=project_input.active_users or "N/A",
            tvl=project_input.tvl or "N/A",
            volume_24h=project_input.volume_24h or "N/A",
            apr=project_input.apr or "N/A",
            geo=project_input.geo,
            excluded_geos=", ".join(project_input.excluded_geos) or "none specified",
            brand_voice_notes=project_input.brand_voice_notes or "none",
            brand_refs="; ".join(project_input.brand_refs) if project_input.brand_refs else "none",
            budget_tier=project_input.budget_tier,
            iteration_context=iteration_context,
        )

        response = await self.client.messages.create(
            model=OPUS_MODEL,
            max_tokens=8000,
            system=OPUS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw = response.content[0].text.strip()

        if raw.startswith("```"):
            raw = raw.split("```", 2)[1].lstrip("json\n")
        if raw.endswith("```"):
            raw = raw.rsplit("```", 1)[0]

        data = json.loads(raw)
        data["project_id"] = project_id
        data["round_number"] = round_number
        if parent_brief_id:
            data["parent_brief_id"] = parent_brief_id

        return CreativeBrief(**data)
