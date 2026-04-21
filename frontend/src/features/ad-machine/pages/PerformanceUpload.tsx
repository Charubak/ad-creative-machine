import { useState, useRef } from "react";
import { adMachineApi } from "../api/adMachineClient";

interface Props {
  packId: string;
  projectId: string;
  onIterateStarted: (jobId: string) => void;
}

type ParsedRow = Record<string, unknown> & { performance_id?: string; platform?: string };

export function PerformanceUpload({ packId, projectId, onIterateStarted }: Props) {
  const [platform, setPlatform] = useState("x");
  const [rows, setRows] = useState<ParsedRow[]>([]);
  const [uploading, setUploading] = useState(false);
  const [iterating, setIterating] = useState(false);
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleUpload = async () => {
    if (!fileRef.current?.files?.[0]) return;
    setUploading(true);
    setError(null);
    try {
      const result = await adMachineApi.uploadPerformance(packId, platform, fileRef.current.files[0]) as { rows: ParsedRow[] };
      setRows(result.rows ?? []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleLabel = async (performanceId: string, label: string) => {
    await adMachineApi.labelPerformance(performanceId, label, null);
    setRows((prev) =>
      prev.map((r) =>
        r.performance_id === performanceId ? { ...r, user_label: label } : r
      )
    );
  };

  const handleIterate = async () => {
    setIterating(true);
    try {
      const { job_id } = await adMachineApi.iterate(projectId, notes);
      onIterateStarted(job_id);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Iteration failed");
    } finally {
      setIterating(false);
    }
  };

  return (
    <div className="am-page">
      <h1 className="am-heading" style={{ fontSize: "1.3rem", marginBottom: "0.5rem" }}>Performance Feedback</h1>
      <p style={{ color: "var(--text-dim)", fontSize: "0.82rem", marginBottom: "2rem" }}>
        Upload CSV exports from your ad platforms, label winners and losers, then generate Round 2.
      </p>

      <div className="am-card" style={{ marginBottom: "2rem" }}>
        <h3 style={{ color: "var(--amber)", marginBottom: "1rem", fontSize: "0.9rem" }}>Upload Performance CSV</h3>
        <div className="am-grid-2">
          <div className="am-field">
            <label className="am-label">Platform</label>
            <select className="am-select" value={platform} onChange={(e) => setPlatform(e.target.value)}>
              <option value="x">X (Twitter)</option>
              <option value="linkedin">LinkedIn</option>
              <option value="meta">Meta</option>
              <option value="google">Google Ads</option>
            </select>
          </div>
          <div className="am-field">
            <label className="am-label">CSV File</label>
            <input
              type="file"
              accept=".csv"
              ref={fileRef}
              style={{ color: "var(--text)", fontSize: "0.82rem" }}
            />
          </div>
        </div>
        <button
          className="am-btn am-btn-ghost"
          onClick={handleUpload}
          disabled={uploading}
        >
          {uploading ? <span className="am-spinner" /> : "Upload & Parse"}
        </button>
      </div>

      {rows.length > 0 && (
        <div style={{ marginBottom: "2rem" }}>
          <div className="am-subheading" style={{ marginBottom: "0.75rem" }}>
            {rows.length} rows parsed — label each pairing
          </div>
          <table className="am-table">
            <thead>
              <tr>
                <th>Pairing</th>
                <th>Platform</th>
                <th>Impressions</th>
                <th>Clicks</th>
                <th>CTR</th>
                <th>Spend</th>
                <th>Label</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i}>
                  <td style={{ color: "var(--text-dim)", fontSize: "0.75rem" }}>
                    {(row.pairing_id as string)?.slice(0, 8) || "—"}
                  </td>
                  <td><span className="am-tag">{row.platform as string}</span></td>
                  <td>{(row.impressions as number)?.toLocaleString()}</td>
                  <td>{(row.clicks as number)?.toLocaleString()}</td>
                  <td>{((row.ctr as number) * 100)?.toFixed(2)}%</td>
                  <td>${(row.spend as number)?.toFixed(2)}</td>
                  <td>
                    <select
                      className="am-select"
                      style={{ padding: "0.25rem 0.5rem", fontSize: "0.75rem" }}
                      value={(row.user_label as string) ?? ""}
                      onChange={(e) => row.performance_id && handleLabel(row.performance_id, e.target.value)}
                    >
                      <option value="">—</option>
                      <option value="winner">Winner</option>
                      <option value="neutral">Neutral</option>
                      <option value="loser">Loser</option>
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="am-card">
        <h3 style={{ color: "var(--amber)", marginBottom: "1rem", fontSize: "0.9rem" }}>Generate Round 2</h3>
        <div className="am-field">
          <label className="am-label">Notes for strategist (optional)</label>
          <textarea
            className="am-textarea"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="The yield angle performed best on X. LinkedIn copy was too institutional. Try a more founder-led tone for round 2."
          />
        </div>
        {error && <div className="am-error" style={{ marginBottom: "0.75rem" }}>{error}</div>}
        <button
          className="am-btn am-btn-primary"
          onClick={handleIterate}
          disabled={iterating}
        >
          {iterating ? <><span className="am-spinner" /> Generating Round 2...</> : "Generate Round 2 →"}
        </button>
      </div>
    </div>
  );
}
