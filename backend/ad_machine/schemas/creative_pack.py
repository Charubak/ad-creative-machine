from pydantic import BaseModel
from datetime import datetime
from typing import Literal


class VisualAsset(BaseModel):
    asset_id: str
    url: str
    platform: str
    spec_name: str
    width: int
    height: int
    prompt_used: str
    model: str
    created_at: datetime


class CreativePairing(BaseModel):
    pairing_id: str
    platform: str
    copy_variation_id: str
    visual_asset_ids: list[str]
    pairing_rationale: str | None = None
    user_label: Literal["winner", "loser", "neutral"] | None = None
    user_notes: str | None = None


class ExportManifest(BaseModel):
    zip_url: str | None = None
    google_rsa_csv_url: str | None = None
    buffer_push_status: dict | None = None


class CreativePack(BaseModel):
    pack_id: str
    project_id: str
    brief_id: str
    copy_pack_id: str
    pairings: list[CreativePairing]
    visual_assets: dict[str, VisualAsset]
    export_manifest: ExportManifest | None = None
    created_at: datetime
