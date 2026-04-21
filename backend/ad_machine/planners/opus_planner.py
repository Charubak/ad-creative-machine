import json
from anthropic import AsyncAnthropic
from ad_machine.schemas.brief import CreativeBrief
from ad_machine.schemas.project_input import ProjectInput

OPUS_MODEL = "claude-opus-4-7"

OPUS_SYSTEM_PROMPT = """You are a senior Web3/DeFi growth strategist with 10+ years of paid acquisition experience across crypto-native and tradfi audiences. You plan ad campaigns that ship: every output you produce must be specific enough for a junior marketer to execute without asking follow-up questions.

You are the PLANNING layer of a multi-agent ad creative system. A copywriting agent and an image generation agent will consume your output downstream. They cannot read minds. Be concrete.

Your operating principles:

1. Crypto-native first. You understand TVL, APR vs APY, points farming, airdrop mechanics, restaking, intent-based architectures, MEV, account abstraction, and the cultural difference between CT-native users and tradfi crossover audiences. You write angles that respect this.

2. Compliance-aware. You never recommend "guaranteed yield," "risk-free," "guaranteed returns," or "passive income guaranteed" framing. You flag any borderline claims for the compliance linter to catch downstream.

3. Platform-native voice mapping:
- X: punchy, declarative, ticker-aware, replies-bait when appropriate, lowercase acceptable
- LinkedIn: institutional, data-led, frames protocols as infrastructure, case-study tone
- Meta (FB/IG): outcome-focused, benefit-led, accessible language, assumes no prior crypto knowledge for retail acquisition campaigns
- Google RSA: intent-matching, problem-solution, keyword-dense without being spammy

4. Angle library you draw from (pick the 3-5 strongest for THIS project, do not force all of them):
- Trustless/self-custody identity ("your keys, your protocol")
- Yield/APR hook (when numbers are competitive and current)
- TVL/volume social proof ("$X locked, Y traders")
- Narrative urgency (mainnet live, v2 launch, points season, airdrop window)
- Community belonging (early-user identity, DAO membership)
- Technical superiority (latency, gas, composability) for dev-targeted plays
- Counter-positioning (vs a named or implied competitor)

5. Output format is strict JSON matching the provided schema. No prose outside the JSON. No markdown fences.

You do not write final ad copy. You produce the strategic brief. The copywriting agent does the writing.
"""

USER_PROMPT_TEMPLATE = """PROJECT INPUT
=============
Protocol name: {protocol_name}
Protocol type: {protocol_type}
Chain(s): {chains}
Token (if applicable): {token_symbol} | live: {token_live}
Stage: {stage}
Live metrics:
  TVL: {tvl}
  24h volume: {volume_24h}
  Current APR/APY: {apr}
  Active users (30d): {active_users}
  Other: {other_metrics}
Target audience (user-defined): {target_audience_raw}
Competitive positioning (user-defined): {competitive_positioning}
Key differentiators: {differentiators}
Campaign goal: {campaign_goal}
Budget tier: {budget_tier}
Geographic focus: {geo}
Excluded geos (compliance): {excluded_geos}
Brand voice notes from user: {brand_voice_notes}
Existing brand assets / references: {brand_refs}
{iteration_context}

OUTPUT
======
Return a JSON object matching this exact schema. No additional fields. No prose outside the JSON.

{{
  "angles": [
    {{
      "name": "string, max 6 words",
      "thesis": "1-2 sentences explaining why this angle works for this specific project and audience",
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
      "platforms_to_reach_them": ["x", "linkedin", "meta", "google_rsa", "coinzilla", "bitmedia", "reddit"],
      "best_angles_for_this_segment": ["angle name from above"],
      "objections_to_overcome": ["string"]
    }}
  ],
  "platform_strategy": {{
    "x": {{
      "primary_angle": "angle name",
      "tone_directive": "specific tone instruction for the copy agent",
      "format_recommendation": "single tweet | thread | quote-bait | reply-bait",
      "creative_format": "static image | meme | chart",
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
    "imagery_to_avoid": ["generic crypto coins floating, robot hands, cliché blockchain visuals"],
    "typography_feel": "string",
    "per_platform_visual_notes": {{ "x": "...", "linkedin": "...", "meta": "...", "google_rsa": "N/A - text only" }}
  }},
  "compliance_constraints": ["specific phrases or claims to avoid for this project's jurisdiction/stage"],
  "recommended_extra_platforms": [
    {{ "platform": "coinzilla | bitmedia | reddit", "recommend": true, "rationale": "1-2 sentences", "suggested_budget_split_pct": 15 }}
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
            protocol_type=project_input.protocol_type,
            chains=", ".join(project_input.chains),
            token_symbol=project_input.token_symbol or "N/A",
            token_live=project_input.token_live,
            stage=project_input.stage,
            tvl=project_input.tvl or "N/A",
            volume_24h=project_input.volume_24h or "N/A",
            apr=project_input.apr or "N/A",
            active_users=project_input.active_users or "N/A",
            other_metrics=project_input.other_metrics or "N/A",
            target_audience_raw=project_input.target_audience_raw,
            competitive_positioning=project_input.competitive_positioning,
            differentiators="; ".join(project_input.differentiators),
            campaign_goal=project_input.campaign_goal,
            budget_tier=project_input.budget_tier,
            geo=project_input.geo,
            excluded_geos=", ".join(project_input.excluded_geos) or "none specified",
            brand_voice_notes=project_input.brand_voice_notes or "none",
            brand_refs="; ".join(project_input.brand_refs) if project_input.brand_refs else "none",
            iteration_context=iteration_context,
        )

        response = await self.client.messages.create(
            model=OPUS_MODEL,
            max_tokens=8000,
            system=OPUS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=0.7,
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
