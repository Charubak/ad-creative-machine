from pydantic import BaseModel
from typing import Literal


class ComplianceFlag(BaseModel):
    severity: Literal["block", "warn", "info"]
    rule: str
    matched_text: str
    suggestion: str | None = None


class CopyVariation(BaseModel):
    variation_id: str
    platform: str
    angle_used: str
    payload: dict
    char_count: int | None = None
    voice_score: float | None = None
    slop_score: float | None = None
    compliance_flags: list[ComplianceFlag] = []


class CopyPack(BaseModel):
    pack_id: str
    brief_id: str
    variations: dict[str, list[CopyVariation]]
    overall_voice_score: float
    overall_slop_score: float
    overall_compliance_flags: list[ComplianceFlag]
