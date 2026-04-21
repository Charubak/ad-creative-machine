-- Ad Machine tables migration
-- Run once against the target Postgres database.

CREATE TABLE IF NOT EXISTS ad_projects (
    project_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    protocol_name TEXT NOT NULL,
    inputs JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ad_projects_user ON ad_projects(user_id);

CREATE TABLE IF NOT EXISTS ad_briefs (
    brief_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES ad_projects(project_id) ON DELETE CASCADE,
    round_number INT NOT NULL DEFAULT 1,
    parent_brief_id UUID REFERENCES ad_briefs(brief_id),
    brief_json JSONB NOT NULL,
    opus_model TEXT NOT NULL,
    opus_input_tokens INT,
    opus_output_tokens INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ad_briefs_project ON ad_briefs(project_id);

CREATE TABLE IF NOT EXISTS ad_copy_packs (
    pack_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brief_id UUID NOT NULL REFERENCES ad_briefs(brief_id) ON DELETE CASCADE,
    pack_json JSONB NOT NULL,
    sonnet_model TEXT NOT NULL,
    voice_score FLOAT,
    slop_score FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ad_copy_packs_brief ON ad_copy_packs(brief_id);

CREATE TABLE IF NOT EXISTS ad_visual_assets (
    asset_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES ad_projects(project_id) ON DELETE CASCADE,
    brief_id UUID REFERENCES ad_briefs(brief_id),
    storage_url TEXT NOT NULL,
    platform TEXT NOT NULL,
    spec_name TEXT NOT NULL,
    width INT NOT NULL,
    height INT NOT NULL,
    prompt_used TEXT NOT NULL,
    model TEXT NOT NULL,
    bytes_size INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ad_assets_project ON ad_visual_assets(project_id);

CREATE TABLE IF NOT EXISTS ad_creative_packs (
    pack_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES ad_projects(project_id) ON DELETE CASCADE,
    brief_id UUID NOT NULL REFERENCES ad_briefs(brief_id),
    copy_pack_id UUID NOT NULL REFERENCES ad_copy_packs(pack_id),
    pack_json JSONB NOT NULL,
    export_manifest JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ad_creative_packs_project ON ad_creative_packs(project_id);

CREATE TABLE IF NOT EXISTS ad_pairing_performance (
    performance_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pairing_id UUID NOT NULL,
    creative_pack_id UUID NOT NULL REFERENCES ad_creative_packs(pack_id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    impressions INT NOT NULL DEFAULT 0,
    clicks INT NOT NULL DEFAULT 0,
    ctr FLOAT,
    conversions INT,
    cpa FLOAT,
    spend FLOAT NOT NULL DEFAULT 0,
    days_running INT NOT NULL DEFAULT 0,
    user_label TEXT CHECK (user_label IN ('winner', 'loser', 'neutral')),
    user_notes TEXT,
    uploaded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ad_perf_pack ON ad_pairing_performance(creative_pack_id);
CREATE INDEX IF NOT EXISTS idx_ad_perf_pairing ON ad_pairing_performance(pairing_id);

CREATE TABLE IF NOT EXISTS ad_jobs (
    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES ad_projects(project_id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'succeeded', 'failed')),
    current_stage TEXT,
    progress_events JSONB DEFAULT '[]'::jsonb,
    error TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_ad_jobs_project ON ad_jobs(project_id);
CREATE INDEX IF NOT EXISTS idx_ad_jobs_status ON ad_jobs(status);
