import type { VisualAsset } from "../types";
import { adMachineApi } from "../api/adMachineClient";

interface Props {
  asset: VisualAsset;
  selected?: boolean;
  onSelect?: () => void;
}

export function VisualAssetCard({ asset, selected, onSelect }: Props) {
  const handleRegen = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await adMachineApi.regenerateVisual(asset.asset_id);
    } catch {
      alert("Regeneration not yet available in v1 (coming in v1.1)");
    }
  };

  const handleDownload = (e: React.MouseEvent) => {
    e.stopPropagation();
    const a = document.createElement("a");
    a.href = asset.url;
    a.download = `${asset.platform}_${asset.spec_name}_${asset.asset_id.slice(0, 8)}.png`;
    a.click();
  };

  return (
    <div
      className={`am-visual-card ${selected ? "selected" : ""}`}
      onClick={onSelect}
      title={`${asset.width}×${asset.height} · ${asset.spec_name}`}
    >
      {asset.url.startsWith("file://") || asset.url.startsWith("http") ? (
        <img
          src={asset.url}
          alt={`${asset.platform} ${asset.spec_name}`}
          style={{ aspectRatio: `${asset.width}/${asset.height}`, maxHeight: "200px" }}
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = "none";
          }}
        />
      ) : (
        <div style={{ aspectRatio: `${asset.width}/${asset.height}`, background: "var(--surface2)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-dim)", fontSize: "0.75rem" }}>
          {asset.width}×{asset.height}
        </div>
      )}
      <div className="am-visual-card-footer">
        <span>{asset.spec_name} · {asset.width}×{asset.height}</span>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button
            className="am-btn am-btn-ghost"
            style={{ padding: "0.15rem 0.4rem", fontSize: "0.65rem" }}
            onClick={handleDownload}
          >
            ↓
          </button>
          <button
            className="am-btn am-btn-ghost"
            style={{ padding: "0.15rem 0.4rem", fontSize: "0.65rem" }}
            onClick={handleRegen}
          >
            ↺
          </button>
        </div>
      </div>
    </div>
  );
}
