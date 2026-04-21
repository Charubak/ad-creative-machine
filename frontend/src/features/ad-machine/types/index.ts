export type Platform = "x" | "linkedin" | "meta" | "google_rsa";
export type ExtraPlatform = "coinzilla" | "bitmedia" | "reddit";
export type JobStatus = "queued" | "running" | "succeeded" | "failed";
export type PipelineStage =
  | "opus_planning"
  | "copy_generation"
  | "image_generation"
  | "assembly";
export type UserLabel = "winner" | "loser" | "neutral";

export interface ComplianceFlag {
  severity: "block" | "warn" | "info";
  rule: string;
  matched_text: string;
  suggestion?: string;
}

export interface CopyVariation {
  variation_id: string;
  platform: string;
  angle_used: string;
  payload: Record<string, unknown>;
  char_count?: number;
  voice_score?: number;
  slop_score?: number;
  compliance_flags: ComplianceFlag[];
}

export interface CopyPack {
  pack_id: string;
  brief_id: string;
  variations: Record<string, CopyVariation[]>;
  overall_voice_score: number;
  overall_slop_score: number;
  overall_compliance_flags: ComplianceFlag[];
}

export interface VisualAsset {
  asset_id: string;
  url: string;
  platform: string;
  spec_name: string;
  width: number;
  height: number;
  prompt_used: string;
  model: string;
  created_at: string;
}

export interface CreativePairing {
  pairing_id: string;
  platform: string;
  copy_variation_id: string;
  visual_asset_ids: string[];
  pairing_rationale?: string;
  user_label?: UserLabel;
  user_notes?: string;
}

export interface CreativePack {
  pack_id: string;
  project_id: string;
  brief_id: string;
  copy_pack_id: string;
  pairings: CreativePairing[];
  visual_assets: Record<string, VisualAsset>;
  export_manifest?: {
    zip_url?: string;
    google_rsa_csv_url?: string;
    buffer_push_status?: Record<string, unknown>;
  };
  created_at: string;
}

export interface SSEEvent {
  type: string;
  stage?: string;
  started_at?: string;
  duration_ms?: number;
  output_summary?: string;
  brief_id?: string;
  copy_pack_id?: string;
  creative_pack_id?: string;
  platform?: string;
  variations?: number;
  asset_count?: number;
  pairing_count?: number;
  voice_score?: number;
  slop_score?: number;
  compliance_flag_count?: number;
  error?: string;
}

export interface ProjectInput {
  protocol_name: string;
  protocol_type: string;
  chains: string[];
  token_symbol?: string;
  token_live: boolean;
  stage: string;
  tvl?: string;
  volume_24h?: string;
  apr?: string;
  active_users?: string;
  other_metrics?: string;
  target_audience_raw: string;
  competitive_positioning: string;
  differentiators: string[];
  campaign_goal: string;
  budget_tier: string;
  geo: string;
  excluded_geos: string[];
  voice_profile_id: string;
  brand_refs: string[];
  brand_voice_notes?: string;
  visuals_per_variation: number;
  auto_publish: boolean;
  extra_platforms_enabled: boolean;
}
