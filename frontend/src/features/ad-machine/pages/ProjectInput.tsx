import { useState } from "react";
import { adMachineApi } from "../api/adMachineClient";

interface Props {
  onJobStarted: (projectId: string, jobId: string) => void;
}

const INDUSTRIES = [
  { value: "saas", label: "SaaS" },
  { value: "ecommerce", label: "E-commerce" },
  { value: "fintech", label: "Fintech" },
  { value: "health", label: "Health" },
  { value: "crypto", label: "Crypto / DeFi" },
  { value: "other", label: "Other" },
];

const GOALS = [
  { value: "user signups", label: "Sign-ups" },
  { value: "brand awareness", label: "Awareness" },
  { value: "app installs", label: "App Installs" },
  { value: "revenue growth", label: "Revenue" },
  { value: "lead generation", label: "Lead Gen" },
  { value: "TVL growth", label: "TVL Growth" },
];

const PLATFORMS = [
  { value: "meta", label: "Meta" },
  { value: "google", label: "Google" },
  { value: "linkedin", label: "LinkedIn" },
  { value: "twitter", label: "X / Twitter" },
  { value: "tiktok", label: "TikTok" },
];

const PLACEHOLDERS: Record<string, { name: string; desc: string; audience: string }> = {
  saas: {
    name: "e.g. Notion, Linear, Figma",
    desc: "e.g. AI project management that auto-prioritises your backlog. 10x faster sprint planning than Jira. Works in minutes, no setup.",
    audience: "e.g. Engineering managers at Series A–C startups. Frustrated with Jira. Active on LinkedIn and Twitter.",
  },
  ecommerce: {
    name: "e.g. Gymshark, MNML, Allbirds",
    desc: "e.g. Premium gym wear at mid-market prices. 4-way stretch, 500+ 5-star reviews. Ships same day. Half the price of Lululemon.",
    audience: "e.g. Gym-goers 22–35, active on Instagram and TikTok. Aspirational, price-conscious but quality-focused.",
  },
  fintech: {
    name: "e.g. Wise, Plaid, Brex",
    desc: "e.g. International transfers with zero fx markup. 4x cheaper than your bank. 200+ countries, instant to 40+ markets.",
    audience: "e.g. Expats and freelancers sending money internationally. 25–40, mobile-first, fed up with bank fees.",
  },
  health: {
    name: "e.g. Whoop, Calm, Hims",
    desc: "e.g. Sleep + HRV tracking wearable with daily recovery scores. More accurate than Fitbit, used by 50+ NFL athletes.",
    audience: "e.g. Performance athletes and health-obsessed professionals, 28–45. Track everything. Pay for accuracy.",
  },
  crypto: {
    name: "e.g. EigenLayer, Aave, Uniswap",
    desc: "e.g. Delta-neutral yield averaging 14% APY. Audited by Certik. No lockups, withdraw any time. $48M TVL, zero exploits.",
    audience: "e.g. DeFi-native yield farmers, 25–40, technically fluent, active on CT. Also want TradFi crossover via LinkedIn.",
  },
  other: {
    name: "e.g. your brand or product name",
    desc: "e.g. what your product does, key metrics, and why it beats the alternatives",
    audience: "e.g. who your ideal customer is, age range, platforms they use, what they care about",
  },
};

export function ProjectInput({ onJobStarted }: Props) {
  const [industry, setIndustry] = useState("saas");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [audience, setAudience] = useState("");
  const [goal, setGoal] = useState("user signups");
  const [platforms, setPlatforms] = useState<string[]>(["meta", "google"]);
  const [brandFiles, setBrandFiles] = useState<File[]>([]);
  const [brandNotes, setBrandNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleBrandFiles = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []).slice(0, 5);
    setBrandFiles(files);
  };

  const removeBrandFile = (i: number) => {
    setBrandFiles(prev => prev.filter((_, idx) => idx !== i));
  };

  const togglePlatform = (p: string) => {
    setPlatforms(prev =>
      prev.includes(p) ? prev.filter(x => x !== p) : [...prev, p]
    );
  };

  const ph = PLACEHOLDERS[industry] ?? PLACEHOLDERS.other;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !description.trim() || !audience.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const { project_id } = await adMachineApi.createProject({
        protocol_name: name.trim(),
        industry: industry as any,
        protocol_type: "other",
        chains: industry === "crypto" ? ["ethereum"] : [],
        stage: "growth",
        target_audience_raw: audience.trim(),
        competitive_positioning: description.trim(),
        differentiators: [description.trim()],
        campaign_goal: goal,
        budget_tier: "5k_25k",
        geo: "global",
        excluded_geos: [],
        voice_profile_id: "demo",
        brand_refs: brandFiles.map(f => f.name),
        brand_voice_notes: brandNotes.trim() || undefined,
        visuals_per_variation: 1,
        auto_publish: false,
        extra_platforms_enabled: true,
        token_live: false,
      });

      // Upload brand files if any
      if (brandFiles.length > 0) {
        const form = new FormData();
        brandFiles.forEach(f => form.append("files", f));
        await fetch(
          `${import.meta.env.VITE_API_BASE ?? "https://ad-creative-machine-api.fly.dev"}/api/ad-machine/projects/${project_id}/brand-assets`,
          { method: "POST", body: form }
        );
      }

      const { job_id } = await adMachineApi.runProject(project_id, "demo");
      onJobStarted(project_id, job_id);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  const isValid = name.trim() && description.trim() && audience.trim() && platforms.length > 0;

  return (
    <div className="am-generate-page">
      <div className="am-generate-header">
        <h1>Generate Ad Creatives</h1>
        <p>Describe your product. We'll build the strategy, copy, and visuals — with Claude + Gemini.</p>
      </div>

      <form onSubmit={handleSubmit} className="am-generate-form">

        {/* Industry selector */}
        <div className="am-field-group">
          <label className="am-field-label">Industry</label>
          <div className="am-industry-grid">
            {INDUSTRIES.map(ind => (
              <button
                key={ind.value}
                type="button"
                className={`am-industry-btn ${industry === ind.value ? "active" : ""}`}
                onClick={() => setIndustry(ind.value)}
              >
                {ind.label}
              </button>
            ))}
          </div>
        </div>

        {/* Product name */}
        <div className="am-field-group">
          <label className="am-field-label am-required">Product / Brand name</label>
          <input
            className="am-input"
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder={ph.name}
            required
          />
        </div>

        {/* Description */}
        <div className="am-field-group">
          <label className="am-field-label am-required">What does it do and what makes it different?</label>
          <textarea
            className="am-textarea"
            value={description}
            onChange={e => setDescription(e.target.value)}
            rows={3}
            placeholder={ph.desc}
            required
          />
        </div>

        {/* Audience */}
        <div className="am-field-group">
          <label className="am-field-label am-required">Who are you targeting?</label>
          <textarea
            className="am-textarea"
            value={audience}
            onChange={e => setAudience(e.target.value)}
            rows={2}
            placeholder={ph.audience}
            required
          />
        </div>

        {/* Goal */}
        <div className="am-field-group">
          <label className="am-field-label">Campaign goal</label>
          <div className="am-pill-row">
            {GOALS.map(g => (
              <button
                key={g.value}
                type="button"
                className={`am-pill ${goal === g.value ? "active" : ""}`}
                onClick={() => setGoal(g.value)}
              >
                {g.label}
              </button>
            ))}
          </div>
        </div>

        {/* Platforms */}
        <div className="am-field-group">
          <label className="am-field-label">Platforms <span className="am-field-sub">(select all that apply)</span></label>
          <div className="am-pill-row">
            {PLATFORMS.map(p => (
              <button
                key={p.value}
                type="button"
                className={`am-pill ${platforms.includes(p.value) ? "active" : ""}`}
                onClick={() => togglePlatform(p.value)}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* Brand assets — optional */}
        <div className="am-field-group">
          <label className="am-field-label">
            Brand reference files <span className="am-field-sub">optional · logos, style guides, existing ads</span>
          </label>
          <label className="am-file-drop">
            <input
              type="file"
              multiple
              accept="image/*,.pdf,.png,.jpg,.jpeg,.svg,.gif,.webp"
              onChange={handleBrandFiles}
              style={{ display: "none" }}
            />
            <span className="am-file-drop-icon">↑</span>
            <span>Drop files or click to upload <span className="am-field-sub">(up to 5 files)</span></span>
          </label>
          {brandFiles.length > 0 && (
            <div className="am-brand-file-list">
              {brandFiles.map((f, i) => (
                <div key={i} className="am-brand-file-chip">
                  <span>{f.name}</span>
                  <button type="button" onClick={() => removeBrandFile(i)} className="am-brand-file-remove">×</button>
                </div>
              ))}
            </div>
          )}
          <textarea
            className="am-textarea"
            value={brandNotes}
            onChange={e => setBrandNotes(e.target.value)}
            rows={2}
            placeholder="e.g. primary colour is #6366F1, always use Inter font, avoid red, our tone is direct and confident"
          />
        </div>

        {error && (
          <div className="am-error-banner">
            <span>!</span>
            <span>{error}</span>
          </div>
        )}

        <div className="am-submit-row">
          <button
            type="submit"
            className="am-generate-btn"
            disabled={loading || !isValid}
          >
            {loading ? (
              <><span className="am-spinner" /> Generating…</>
            ) : (
              <>Generate Ads <span className="am-arrow">→</span></>
            )}
          </button>
          <span className="am-generate-note">~60–90 seconds · Claude Opus + Gemini 2.5</span>
        </div>
      </form>
    </div>
  );
}
