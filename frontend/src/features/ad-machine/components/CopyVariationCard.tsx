import { useState } from "react";
import type { CopyVariation } from "../types";
import { useCopyEdit } from "../hooks/useCopyEdit";
import { ComplianceFlagBanner } from "./ComplianceFlagBanner";

interface Props {
  variation: CopyVariation;
  index: number;
}

function scoreClass(score: number | undefined): string {
  if (score === undefined) return "";
  if (score >= 7.5) return "am-score-good";
  if (score >= 5) return "am-score-mid";
  return "am-score-bad";
}

export function CopyVariationCard({ variation, index }: Props) {
  const { debouncedEdit } = useCopyEdit();
  const [payload, setPayload] = useState<Record<string, unknown>>(variation.payload);
  const [expanded, setExpanded] = useState(false);

  const handleChange = (key: string, value: string) => {
    const next = { ...payload, [key]: value };
    setPayload(next);
    debouncedEdit(variation.variation_id, next);
  };

  const editableText = Object.entries(payload).filter(
    ([, v]) => typeof v === "string"
  ) as [string, string][];

  return (
    <div className="am-copy-card">
      <div className="am-copy-card-header">
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <span style={{ color: "var(--amber)", fontSize: "0.75rem" }}>#{index + 1}</span>
          <span className="am-tag">{variation.angle_used}</span>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          {variation.voice_score !== undefined && (
            <span className={`am-score-badge ${scoreClass(variation.voice_score)}`}>
              voice {variation.voice_score.toFixed(1)}
            </span>
          )}
          {variation.slop_score !== undefined && (
            <span className={`am-score-badge ${scoreClass(variation.slop_score)}`}>
              slop {variation.slop_score.toFixed(1)}
            </span>
          )}
          <button
            className="am-btn am-btn-ghost"
            style={{ padding: "0.2rem 0.5rem", fontSize: "0.7rem" }}
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? "collapse" : "edit"}
          </button>
        </div>
      </div>

      <div className="am-copy-card-body">
        <ComplianceFlagBanner flags={variation.compliance_flags} />

        {expanded ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            {editableText.map(([key, val]) => (
              <div key={key} className="am-field">
                <label className="am-label">{key.replace(/_/g, " ")}</label>
                {val.length > 80 ? (
                  <textarea
                    className="am-textarea"
                    value={val}
                    onChange={(e) => handleChange(key, e.target.value)}
                    style={{ minHeight: "80px" }}
                  />
                ) : (
                  <input
                    className="am-input"
                    value={val}
                    onChange={(e) => handleChange(key, e.target.value)}
                  />
                )}
              </div>
            ))}
          </div>
        ) : (
          <div>
            {editableText.slice(0, 3).map(([key, val]) => (
              <div key={key} style={{ marginBottom: "0.5rem" }}>
                <span style={{ color: "var(--text-dim)", fontSize: "0.7rem" }}>{key}: </span>
                <span style={{ color: "var(--text-bright)", fontSize: "0.82rem" }}>{val}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
