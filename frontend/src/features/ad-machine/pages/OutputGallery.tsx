import { useState, useEffect } from "react";
import { adMachineApi } from "../api/adMachineClient";
import type { CreativePack, CopyPack } from "../types";
import { BriefCard } from "../components/BriefCard";
import { CopyVariationCard } from "../components/CopyVariationCard";
import { VisualAssetCard } from "../components/VisualAssetCard";
import { ComplianceFlagBanner } from "../components/ComplianceFlagBanner";
import { ExportPanel } from "../components/ExportPanel";

const PLATFORM_LABELS: Record<string, string> = {
  x: "X (Twitter)",
  linkedin: "LinkedIn",
  meta: "Meta",
  google_rsa: "Google RSA",
};

interface Props {
  packId: string;
  onIterateReady?: (projectId: string) => void;
}

export function OutputGallery({ packId, onIterateReady }: Props) {
  const [pack, setPack] = useState<CreativePack | null>(null);
  const [copyPack, setCopyPack] = useState<CopyPack | null>(null);
  const [brief, setBrief] = useState<Record<string, unknown> | null>(null);
  const [activeTab, setActiveTab] = useState("brief");
  const [selectedPairings, setSelectedPairings] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const cp = await adMachineApi.getCreativePack(packId) as unknown as CreativePack;
        setPack(cp);
        const copyRaw = await adMachineApi.getCopyPack(cp.copy_pack_id) as unknown as CopyPack;
        setCopyPack(copyRaw);
        const briefRaw = await adMachineApi.getBrief(cp.brief_id);
        setBrief(briefRaw);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [packId]);

  if (loading) return <div className="am-page"><span className="am-spinner" /></div>;
  if (error) return <div className="am-page" style={{ color: "var(--red)" }}>{error}</div>;
  if (!pack || !copyPack) return null;

  const platforms = Object.keys(copyPack.variations);
  const tabs = ["brief", ...platforms];

  const togglePairing = (id: string) => {
    setSelectedPairings((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const pairingsByPlatform = (platform: string) =>
    pack.pairings.filter((p) => p.platform === platform);

  return (
    <div className="am-page" style={{ paddingBottom: "80px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <h1 className="am-heading" style={{ fontSize: "1.3rem" }}>Creative Pack</h1>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <span style={{ fontSize: "0.7rem", color: "var(--text-dim)" }}>
            {copyPack.overall_compliance_flags.length > 0 && (
              <span style={{ color: "var(--yellow)" }}>
                {copyPack.overall_compliance_flags.length} flag(s)
              </span>
            )}
          </span>
          <span className="am-score-badge am-score-good">
            voice {copyPack.overall_voice_score.toFixed(1)}
          </span>
          <span className="am-score-badge am-score-good">
            slop {copyPack.overall_slop_score.toFixed(1)}
          </span>
        </div>
      </div>

      <div className="am-tabs">
        {tabs.map((tab) => (
          <button
            key={tab}
            className={`am-tab ${activeTab === tab ? "active" : ""}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab === "brief" ? "Brief" : PLATFORM_LABELS[tab] ?? tab}
          </button>
        ))}
      </div>

      {activeTab === "brief" && brief && (
        <BriefCard brief={brief} />
      )}

      {platforms.includes(activeTab) && (
        <div>
          <ComplianceFlagBanner
            flags={copyPack.overall_compliance_flags.filter((f) =>
              copyPack.variations[activeTab]?.some((v) =>
                v.compliance_flags.some((cf) => cf.matched_text === f.matched_text)
              )
            )}
          />

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            {/* Copy variations column */}
            <div>
              <div className="am-subheading" style={{ marginBottom: "0.75rem" }}>Copy Variations</div>
              {(copyPack.variations[activeTab] ?? []).map((v, i) => (
                <CopyVariationCard key={v.variation_id} variation={v} index={i} />
              ))}
            </div>

            {/* Pairings column */}
            <div>
              <div className="am-subheading" style={{ marginBottom: "0.75rem" }}>Paired Visuals</div>
              {pairingsByPlatform(activeTab).map((pairing) => {
                const assets = pairing.visual_asset_ids
                  .map((id) => pack.visual_assets[id])
                  .filter(Boolean);
                const isSelected = selectedPairings.has(pairing.pairing_id);

                return (
                  <div
                    key={pairing.pairing_id}
                    className="am-card"
                    style={{ borderColor: isSelected ? "var(--amber)" : undefined, cursor: "pointer" }}
                    onClick={() => togglePairing(pairing.pairing_id)}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                      <span style={{ fontSize: "0.7rem", color: "var(--text-dim)" }}>
                        pairing {pairing.pairing_id.slice(0, 8)}
                      </span>
                      <span style={{ fontSize: "0.7rem", color: isSelected ? "var(--amber)" : "var(--text-dim)" }}>
                        {isSelected ? "✓ selected for export" : "click to select"}
                      </span>
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(120px, 1fr))", gap: "0.5rem" }}>
                      {assets.map((asset) => (
                        <VisualAssetCard
                          key={asset.asset_id}
                          asset={asset}
                          selected={isSelected}
                        />
                      ))}
                      {assets.length === 0 && (
                        <div style={{ color: "var(--text-dim)", fontSize: "0.75rem", padding: "1rem", textAlign: "center" }}>
                          No visuals generated yet
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      <ExportPanel packId={packId} selectedPairingIds={Array.from(selectedPairings)} />
    </div>
  );
}
