from pydantic import BaseModel, Field
from typing import Literal

ProtocolType = Literal[
    "dex", "lending", "yield_aggregator", "bridge", "restaking", "liquid_staking",
    "perps", "options", "rwa", "launchpad", "dao", "nft_infra", "l1", "l2", "wallet", "other"
]

Stage = Literal["pre_launch", "testnet", "mainnet_early", "mainnet_growth", "mature"]

BudgetTier = Literal["under_5k", "5k_25k", "25k_100k", "over_100k"]


class ProjectInput(BaseModel):
    # Project Basics
    protocol_name: str = Field(..., min_length=1, max_length=100)
    protocol_type: ProtocolType
    chains: list[str] = Field(..., min_length=1)
    token_symbol: str | None = None
    token_live: bool = False
    stage: Stage

    # Live Metrics (all optional but recommended)
    tvl: str | None = None
    volume_24h: str | None = None
    apr: str | None = None
    active_users: str | None = None
    other_metrics: str | None = None

    # Strategy
    target_audience_raw: str = Field(..., min_length=10)
    competitive_positioning: str = Field(..., min_length=10)
    differentiators: list[str] = Field(..., min_length=1)
    campaign_goal: str
    budget_tier: BudgetTier
    geo: str = "global"
    excluded_geos: list[str] = []

    # Brand & Voice
    voice_profile_id: str = "demo"
    brand_refs: list[str] = []
    brand_voice_notes: str | None = None

    # Output Preferences
    visuals_per_variation: int = Field(default=1, ge=1, le=3)
    auto_publish: bool = False
    extra_platforms_enabled: bool = True
