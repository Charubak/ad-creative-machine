import type { SSEEvent, PipelineStage as Stage } from "../types";

const STAGE_LABELS: Record<string, string> = {
  opus_planning: "Strategic Brief (Opus)",
  copy_generation: "Copy Generation (Sonnet)",
  image_generation: "Visual Generation (Gemini)",
  assembly: "Assembly",
};

type StageStatus = "pending" | "active" | "done" | "failed";

interface Props {
  stage: string;
  status: StageStatus;
  summary?: string;
  substages?: SSEEvent[];
}

const ICONS: Record<StageStatus, string> = {
  pending: "○",
  active: "●",
  done: "✓",
  failed: "✗",
};

export function PipelineStage({ stage, status, summary, substages }: Props) {
  return (
    <div className={`am-stage ${status}`}>
      <div className={`am-stage-icon ${status}`}>
        {status === "active" ? <span className="am-spinner" /> : ICONS[status]}
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ color: status === "active" ? "var(--amber)" : status === "done" ? "var(--green)" : status === "failed" ? "var(--red)" : "var(--text-dim)" }}>
          {STAGE_LABELS[stage] ?? stage}
        </div>
        {summary && (
          <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginTop: "0.25rem" }}>
            {summary}
          </div>
        )}
        {substages && substages.length > 0 && (
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginTop: "0.5rem" }}>
            {substages.map((s, i) => (
              <span key={i} className="am-tag">
                {s.platform} — {s.variations} vars
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
