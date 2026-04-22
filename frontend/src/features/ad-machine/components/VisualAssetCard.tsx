import type { VisualAsset } from "../types";
import { adMachineApi } from "../api/adMachineClient";

const API_BASE = import.meta.env.VITE_API_BASE ?? "https://ad-creative-machine-api.fly.dev";

function getImageSrc(asset: VisualAsset): string {
  // Always proxy through the backend — works for local file:// and S3 URLs alike
  return `${API_BASE}/api/ad-machine/visual-assets/${asset.asset_id}/image`;
}

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
    a.href = getImageSrc(asset);
    a.download = `${asset.platform}_${asset.spec_name}_${asset.asset_id.slice(0, 8)}.png`;
    a.click();
  };

  return (
    <div
      className={`am-visual-card ${selected ? "selected" : ""}`}
      onClick={onSelect}
      title={`${asset.width}×${asset.height} · ${asset.spec_name}`}
    >
      <img
        src={getImageSrc(asset)}
        alt={`${asset.platform} ${asset.spec_name}`}
        style={{ width: "100%", aspectRatio: `${asset.width}/${asset.height}`, objectFit: "cover", display: "block", background: "var(--surface2)" }}
        onError={(e) => {
          const el = e.target as HTMLImageElement;
          el.style.display = "none";
          el.insertAdjacentHTML("afterend", `<div style="aspect-ratio:${asset.width}/${asset.height};display:flex;align-items:center;justify-content:center;color:var(--text-dim);font-size:0.75rem;background:var(--surface2)">${asset.width}×${asset.height}</div>`);
        }}
      />
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
