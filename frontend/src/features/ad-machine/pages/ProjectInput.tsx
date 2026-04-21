import { useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { adMachineApi } from "../api/adMachineClient";
import type { ProjectInput as ProjectInputType } from "../types";

interface Props {
  onJobStarted: (projectId: string, jobId: string) => void;
}

const PROTOCOL_TYPES = [
  "dex", "lending", "yield_aggregator", "bridge", "restaking", "liquid_staking",
  "perps", "options", "rwa", "launchpad", "dao", "nft_infra", "l1", "l2", "wallet", "other",
];

const STAGES = ["pre_launch", "testnet", "mainnet_early", "mainnet_growth", "mature"];
const BUDGETS = ["under_5k", "5k_25k", "25k_100k", "over_100k"];

export function ProjectInput({ onJobStarted }: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [diffInput, setDiffInput] = useState("");

  const { register, control, handleSubmit, formState: { errors } } = useForm<ProjectInputType>({
    defaultValues: {
      chains: [],
      differentiators: [],
      excluded_geos: [],
      brand_refs: [],
      geo: "global",
      voice_profile_id: "demo",
      visuals_per_variation: 1,
      auto_publish: false,
      extra_platforms_enabled: true,
      token_live: false,
    },
  });

  const onSubmit = async (data: ProjectInputType) => {
    setLoading(true);
    setError(null);
    try {
      // Parse comma-separated fields
      const input: ProjectInputType = {
        ...data,
        chains: typeof data.chains === "string"
          ? (data.chains as unknown as string).split(",").map((s) => s.trim()).filter(Boolean)
          : data.chains,
        differentiators: diffInput.split("\n").map((s) => s.trim()).filter(Boolean),
        excluded_geos: typeof data.excluded_geos === "string"
          ? (data.excluded_geos as unknown as string).split(",").map((s) => s.trim()).filter(Boolean)
          : data.excluded_geos,
      };

      const { project_id } = await adMachineApi.createProject(input);
      const { job_id } = await adMachineApi.runProject(project_id, data.voice_profile_id || "demo");
      onJobStarted(project_id, job_id);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="am-page">
      <h1 className="am-heading" style={{ fontSize: "1.6rem", marginBottom: "0.35rem" }}>
        Ad Creative Machine
      </h1>
      <p style={{ color: "var(--text-dim)", fontSize: "0.82rem", marginBottom: "2rem" }}>
        Fill in your project details. Opus plans the strategy, Sonnet writes the copy, Gemini generates the visuals.
      </p>

      <form onSubmit={handleSubmit(onSubmit)}>
        {/* Project Basics */}
        <div className="am-form-section">
          <h3>Project Basics</h3>
          <div className="am-grid-2">
            <div className="am-field">
              <label className="am-label required">Protocol Name</label>
              <input className="am-input" {...register("protocol_name", { required: "Required" })} placeholder="Aave, Uniswap, EigenLayer..." />
              {errors.protocol_name && <div className="am-error">{errors.protocol_name.message}</div>}
            </div>
            <div className="am-field">
              <label className="am-label required">Protocol Type</label>
              <select className="am-select" {...register("protocol_type", { required: "Required" })}>
                <option value="">Select type...</option>
                {PROTOCOL_TYPES.map((t) => (
                  <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
                ))}
              </select>
              {errors.protocol_type && <div className="am-error">{errors.protocol_type.message}</div>}
            </div>
          </div>
          <div className="am-grid-2">
            <div className="am-field">
              <label className="am-label required">Chain(s) (comma-separated)</label>
              <input className="am-input" {...register("chains")} placeholder="Ethereum, Arbitrum, Base" />
            </div>
            <div className="am-field">
              <label className="am-label">Token Symbol</label>
              <input className="am-input" {...register("token_symbol")} placeholder="$AAVE" />
            </div>
          </div>
          <div className="am-grid-2">
            <div className="am-field">
              <label className="am-label required">Stage</label>
              <select className="am-select" {...register("stage", { required: "Required" })}>
                <option value="">Select stage...</option>
                {STAGES.map((s) => (<option key={s} value={s}>{s.replace(/_/g, " ")}</option>))}
              </select>
              {errors.stage && <div className="am-error">{errors.stage.message}</div>}
            </div>
            <div className="am-field" style={{ display: "flex", alignItems: "center", gap: "0.5rem", paddingTop: "1.5rem" }}>
              <input type="checkbox" id="token_live" {...register("token_live")} />
              <label htmlFor="token_live" style={{ color: "var(--text)", fontSize: "0.82rem" }}>Token is live</label>
            </div>
          </div>
        </div>

        {/* Live Metrics */}
        <div className="am-form-section">
          <h3>Live Metrics <span style={{ color: "var(--text-dim)", fontSize: "0.75rem", fontWeight: 400 }}>(optional but makes the brief sharper)</span></h3>
          <div className="am-grid-2">
            <div className="am-field">
              <label className="am-label">TVL</label>
              <input className="am-input" {...register("tvl")} placeholder="$1.2B" />
            </div>
            <div className="am-field">
              <label className="am-label">24h Volume</label>
              <input className="am-input" {...register("volume_24h")} placeholder="$450M" />
            </div>
            <div className="am-field">
              <label className="am-label">APR / APY</label>
              <input className="am-input" {...register("apr")} placeholder="8.5% APR" />
            </div>
            <div className="am-field">
              <label className="am-label">Active Users (30d)</label>
              <input className="am-input" {...register("active_users")} placeholder="48,000" />
            </div>
          </div>
        </div>

        {/* Strategy */}
        <div className="am-form-section">
          <h3>Strategy Inputs</h3>
          <div className="am-field">
            <label className="am-label required">Target Audience</label>
            <textarea className="am-textarea" {...register("target_audience_raw", { required: "Required" })}
              placeholder="DeFi-native yield farmers, 25-40, active on CT. Also targeting TradFi crossover via LinkedIn." />
            {errors.target_audience_raw && <div className="am-error">{errors.target_audience_raw.message}</div>}
          </div>
          <div className="am-field">
            <label className="am-label required">Competitive Positioning</label>
            <textarea className="am-textarea" {...register("competitive_positioning", { required: "Required" })}
              placeholder="vs Aave: higher yields through concentrated liquidity. vs Compound: better UX and gas." />
            {errors.competitive_positioning && <div className="am-error">{errors.competitive_positioning.message}</div>}
          </div>
          <div className="am-field">
            <label className="am-label required">Key Differentiators (one per line)</label>
            <textarea className="am-textarea"
              value={diffInput}
              onChange={(e) => setDiffInput(e.target.value)}
              placeholder={"No withdrawal fees\nAudit by Trail of Bits\nHighest ETH staking yield on L2"}
            />
          </div>
          <div className="am-grid-2">
            <div className="am-field">
              <label className="am-label required">Campaign Goal</label>
              <input className="am-input" {...register("campaign_goal", { required: "Required" })}
                placeholder="TVL growth, app downloads, wallet connections..." />
              {errors.campaign_goal && <div className="am-error">{errors.campaign_goal.message}</div>}
            </div>
            <div className="am-field">
              <label className="am-label required">Budget Tier</label>
              <select className="am-select" {...register("budget_tier", { required: "Required" })}>
                <option value="">Select...</option>
                {BUDGETS.map((b) => (<option key={b} value={b}>{b.replace(/_/g, " ")}</option>))}
              </select>
              {errors.budget_tier && <div className="am-error">{errors.budget_tier.message}</div>}
            </div>
            <div className="am-field">
              <label className="am-label">Geographic Focus</label>
              <input className="am-input" {...register("geo")} placeholder="global" />
            </div>
            <div className="am-field">
              <label className="am-label">Excluded Geos (comma-separated)</label>
              <input className="am-input" {...register("excluded_geos")} placeholder="US, UK (if restricted)" />
            </div>
          </div>
        </div>

        {/* Brand & Voice */}
        <div className="am-form-section">
          <h3>Brand & Voice</h3>
          <div className="am-grid-2">
            <div className="am-field">
              <label className="am-label">Voice Profile ID</label>
              <input className="am-input" {...register("voice_profile_id")} placeholder="demo" />
            </div>
          </div>
          <div className="am-field">
            <label className="am-label">Brand Voice Notes</label>
            <textarea className="am-textarea" {...register("brand_voice_notes")}
              placeholder="Institutional tone. No meme language. Always cite on-chain data." />
          </div>
        </div>

        {error && (
          <div style={{ color: "var(--red)", padding: "0.75rem", background: "rgba(224,82,82,0.1)", borderRadius: "4px", marginBottom: "1rem" }}>
            {error}
          </div>
        )}

        <button
          type="submit"
          className="am-btn am-btn-primary"
          disabled={loading}
          style={{ fontSize: "0.9rem", padding: "0.8rem 2rem" }}
        >
          {loading ? <><span className="am-spinner" /> Submitting...</> : "Generate Creative Package →"}
        </button>
      </form>
    </div>
  );
}
