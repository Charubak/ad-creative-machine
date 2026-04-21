import { useState } from "react";
import { adMachineApi } from "../api/adMachineClient";

interface Props {
  packId: string;
  selectedPairingIds: string[];
}

export function ExportPanel({ packId, selectedPairingIds }: Props) {
  const [loading, setLoading] = useState<string | null>(null);
  const [bufferProfiles, setBufferProfiles] = useState({ x: "", linkedin: "", meta: "" });
  const [showBuffer, setShowBuffer] = useState(false);

  const doExport = async (type: "zip" | "csv" | "buffer") => {
    setLoading(type);
    try {
      if (type === "zip") {
        const res = await adMachineApi.exportZip(packId);
        if (res.zip_url) window.open(res.zip_url, "_blank");
      } else if (type === "csv") {
        const res = await adMachineApi.exportRsaCsv(packId, {});
        if (res.csv_url) window.open(res.csv_url, "_blank");
      } else {
        const profileMap: Record<string, string> = {};
        if (bufferProfiles.x) profileMap.x = bufferProfiles.x;
        if (bufferProfiles.linkedin) profileMap.linkedin = bufferProfiles.linkedin;
        if (bufferProfiles.meta) profileMap.meta = bufferProfiles.meta;
        await adMachineApi.pushBuffer(packId, selectedPairingIds, profileMap);
        alert("Pushed to Buffer drafts.");
      }
    } catch (e: unknown) {
      alert(`Export failed: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="am-export-panel">
      <span style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>
        {selectedPairingIds.length} pairing{selectedPairingIds.length !== 1 ? "s" : ""} selected
      </span>
      <button
        className="am-btn am-btn-ghost"
        onClick={() => doExport("zip")}
        disabled={loading !== null}
      >
        {loading === "zip" ? <span className="am-spinner" /> : "↓ ZIP Bundle"}
      </button>
      <button
        className="am-btn am-btn-ghost"
        onClick={() => doExport("csv")}
        disabled={loading !== null}
      >
        {loading === "csv" ? <span className="am-spinner" /> : "↓ Google RSA CSV"}
      </button>
      <button
        className="am-btn am-btn-ghost"
        onClick={() => setShowBuffer(!showBuffer)}
        disabled={loading !== null}
      >
        Buffer →
      </button>

      {showBuffer && (
        <div
          style={{
            position: "absolute",
            bottom: "60px",
            right: "1.5rem",
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "6px",
            padding: "1rem",
            width: "280px",
            zIndex: 50,
          }}
        >
          <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginBottom: "0.75rem" }}>
            Enter Buffer profile IDs for each platform
          </div>
          {(["x", "linkedin", "meta"] as const).map((p) => (
            <div key={p} className="am-field">
              <label className="am-label">{p}</label>
              <input
                className="am-input"
                placeholder="buffer-profile-id"
                value={bufferProfiles[p]}
                onChange={(e) => setBufferProfiles((prev) => ({ ...prev, [p]: e.target.value }))}
              />
            </div>
          ))}
          <button
            className="am-btn am-btn-primary"
            style={{ width: "100%", justifyContent: "center", marginTop: "0.5rem" }}
            onClick={() => doExport("buffer")}
            disabled={loading !== null || selectedPairingIds.length === 0}
          >
            {loading === "buffer" ? <span className="am-spinner" /> : "Push to Buffer"}
          </button>
        </div>
      )}
    </div>
  );
}
