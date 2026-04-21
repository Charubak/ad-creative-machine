from pydantic import BaseModel, Field
from typing import Literal

Platform = Literal["x", "linkedin", "meta", "google_rsa"]
ExtraPlatformName = Literal["coinzilla", "bitmedia", "reddit"]


class Angle(BaseModel):
    name: str = Field(..., max_length=60)
    thesis: str
    primary_emotion: Literal[
        "greed", "fear", "belonging", "status",
        "curiosity", "frustration", "fomo", "trust"
    ]
    evidence_to_use: list[str]
    rank: int


class Segment(BaseModel):
    name: str
    description: str
    platforms_to_reach_them: list[str]
    best_angles_for_this_segment: list[str]
    objections_to_overcome: list[str]


class PlatformPlan(BaseModel):
    primary_angle: str
    tone_directive: str
    format_recommendation: str | None = None
    creative_format: str | None = None
    cta: str
    headline_themes: list[str] | None = None
    description_themes: list[str] | None = None
    keyword_intent_buckets: list[str] | None = None


class Hook(BaseModel):
    hook: str
    use_for_platforms: list[Platform]
    rationale: str


class VisualDirection(BaseModel):
    aesthetic: str
    color_palette: list[str]
    imagery_themes: list[str]
    imagery_to_avoid: list[str]
    typography_feel: str
    per_platform_visual_notes: dict[str, str]


class ExtraPlatform(BaseModel):
    platform: ExtraPlatformName
    recommend: bool
    rationale: str
    suggested_budget_split_pct: int


class KilledAngle(BaseModel):
    name: str
    reason: str


class CreativeBrief(BaseModel):
    project_id: str
    round_number: int = 1
    parent_brief_id: str | None = None
    angles: list[Angle]
    killed_angles: list[KilledAngle] = []
    audience_segments: list[Segment]
    platform_strategy: dict[str, PlatformPlan]
    narrative_hooks: list[Hook]
    visual_direction: VisualDirection
    compliance_constraints: list[str]
    recommended_extra_platforms: list[ExtraPlatform]
    brief_summary_for_copy_agent: str
    iteration_notes: str | None = None
